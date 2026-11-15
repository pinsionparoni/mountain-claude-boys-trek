"""Fast automated invariants for training/train.jsonl and training/val.jsonl."""

from __future__ import annotations

import json
import re
from pathlib import Path

from evals.coach.score import DECLINE, FI_LEAK, HELP, LEAKS
from evals.finnish.checks import check_answer
from training.generate import load_exclusions

ROOT = Path(__file__).resolve().parent.parent
TRAIN_PATH = ROOT / "training" / "train.jsonl"
VAL_PATH = ROOT / "training" / "val.jsonl"

_FI_ALLOWED_PAREN = re.compile(r"^\(\d{1,2}\.\d{1,2}\.(?:\d{4})?–\d{1,2}\.\d{1,2}\.\d{4}\)$")
_EN_ALLOWED_PAREN = re.compile(r"^\(\d{1,2} [A-Z][a-z]+(?: \d{4})? to \d{1,2} [A-Z][a-z]+ \d{4}\)$")


def _load_jsonl(path: Path) -> list[dict]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def test_training_and_val_files_exist_and_counts():
    assert TRAIN_PATH.exists(), "training/train.jsonl missing"
    assert VAL_PATH.exists(), "training/val.jsonl missing"
    train = _load_jsonl(TRAIN_PATH)
    val = _load_jsonl(VAL_PATH)
    assert len(train) == 304
    assert len(val) == 30

    all_recs = train + val
    fi_count = sum(1 for r in all_recs if r["lang"] == "fi")
    en_count = sum(1 for r in all_recs if r["lang"] == "en")
    assert fi_count == 272
    assert en_count == 62


def test_zero_overlap_with_evals_and_between_splits():
    excluded_cids, excluded_qs = load_exclusions()
    train = _load_jsonl(TRAIN_PATH)
    val = _load_jsonl(VAL_PATH)

    train_cids = {r["customer_id"] for r in train}
    val_cids = {r["customer_id"] for r in val}

    assert len(train_cids) == len(train), "Duplicate customer_id inside train.jsonl"
    assert len(val_cids) == len(val), "Duplicate customer_id inside val.jsonl"
    assert not (train_cids & val_cids), "Customer overlap between train.jsonl and val.jsonl"
    assert not (train_cids & excluded_cids), f"Eval customer leaked into train: {train_cids & excluded_cids}"
    assert not (val_cids & excluded_cids), f"Eval customer leaked into val: {val_cids & excluded_cids}"

    for r in train + val:
        for m in r["messages"]:
            if m["role"] == "user":
                assert m["content"].strip().lower() not in excluded_qs, (
                    f"{r['id']} reuses eval question: {m['content']!r}"
                )


def test_finnish_checks_no_leaks_and_openai_tool_schema():
    train = _load_jsonl(TRAIN_PATH)
    val = _load_jsonl(VAL_PATH)

    from coach.tools import spending

    tool_names = {t.name for t in spending.load_tools("CUST00001")}
    for r in train + val:
        msgs = r["messages"]
        assert msgs[0]["role"] == "system"
        assert "You are talking with customer " in msgs[0]["content"]
        assert {t["function"]["name"] for t in r["tools"]} == tool_names  # the coach's current tools

        has_tool_call = False
        assistant_texts = []
        for idx, m in enumerate(msgs):
            if m["role"] == "assistant":
                if m.get("tool_calls"):
                    has_tool_call = True
                    for tc in m["tool_calls"]:
                        assert tc["type"] == "function"
                        json.loads(tc["function"]["arguments"])
                    assert idx + 1 < len(msgs) and msgs[idx + 1]["role"] == "tool"
                txt = m.get("content") or ""
                if txt:
                    assistant_texts.append(txt)
                    assert ".." not in txt, f"{r['id']} contains double period '..'"
                    for paren in re.findall(r"\([^)]*\)", txt):
                        pat = _FI_ALLOWED_PAREN if r["lang"] == "fi" else _EN_ALLOWED_PAREN
                        assert pat.match(paren), f"{r['id']} has disallowed parenthetical {paren!r}"
                        if r["lang"] == "fi":
                            m_same = re.match(r"^\((\d{1,2})\.(\d{1,2})\.–(\d{1,2})\.(\d{1,2})\.\d{4}\)$", paren)
                            if m_same:
                                assert m_same.group(2) != m_same.group(4), (
                                    f"{r['id']} has single-month date range {paren!r}"
                                )
                    for leak in LEAKS:
                        assert leak not in txt, f"{r['id']} leaked {leak!r}"
                    if r["lang"] == "fi":
                        assert not FI_LEAK.search(txt), f"{r['id']} leaked FI_LEAK"
                        issues = check_answer(txt)
                        assert issues == [], f"{r['id']} Finnish issues: {issues}"
            elif m["role"] == "tool":
                assert "tool_call_id" in m
                json.loads(m["content"])

        assert assistant_texts, f"{r['id']} has no assistant text"
        last_txt = assistant_texts[-1]
        if r["group"] == "refusal":
            assert DECLINE.search(last_txt) and len(last_txt) < 600, f"{r['id']} refusal check failed"
        elif r["group"] == "care":
            assert HELP.search(last_txt), f"{r['id']} care check failed"
        else:
            assert not (not has_tool_call and DECLINE.search(last_txt) and len(last_txt) < 600), (
                f"{r['id']} accidentally triggers score.DECLINE"
            )


def test_training_category_names_match_the_tools():
    """Answers must use the same Finnish names the tools return as category_fi."""
    from coach.spending_baskets import CATEGORY_LABELS_FI
    from training.formatting import CAT_FI

    for category, forms in CAT_FI.items():
        assert forms[0] == CATEGORY_LABELS_FI[category], category
