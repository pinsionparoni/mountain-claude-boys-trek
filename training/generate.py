"""Offline training & validation set generator for Gemma 4 31B LoRA fine-tuning.

Runs the real coach spending/budget/peer/calculation tools against local CSV data
(via training.csv_queries), builds 280 multi-scenario FI/EN conversations (250 train +
30 stratified val), and enforces:
  1. Zero customer or question overlap with evals/coach/cases.json,
     evals/coach/cases_generated.json, evals/finnish/questions.json, and demo IDs.
  2. 100% distinct customers across all 280 examples (train and val are customer-disjoint).
  3. Zero Finnish errors AND zero warnings in evals.finnish.checks.check_answer.
  4. Zero leaked internal tool/field names (evals.coach.score.LEAKS / FI_LEAK).
  5. Exact runtime system prompt and OpenAI tool definitions from coach.agent._prepare.
"""

from __future__ import annotations

import json
import os
import random
from collections import Counter
from datetime import date, timedelta
from pathlib import Path

from training import csv_queries
from training.scenarios_coaching import (
    S08_SPECS,
    S11_CUTS,
    build_s01,
    build_s02,
    build_s03,
    build_s04,
    build_s05,
    build_s06,
    build_s07,
    build_s08,
    build_s09,
    build_s10,
    build_s11,
    build_s12,
    build_s13,
)
from training.scenarios_policy import (
    build_s14,
    build_s15,
    build_s16,
    build_s17,
    build_s18,
    build_s19,
    build_s20,
    build_s21,
    build_s22,
)

ROOT = Path(__file__).resolve().parent.parent
OUT_DIR = Path(__file__).resolve().parent

DEMO_CUSTOMERS = {"CUST00226", "CUST00050", "CUST00127", "CUST00001"}

# Vary `today` on ~30% of examples so LoRA learns to read `today` from CUSTOMER_PROMPT
# rather than memorizing "elokuussa 2026" or "15.9.".
TODAY_POOL = [
    date(2026, 9, 10),
    date(2026, 9, 10),
    date(2026, 9, 10),
    date(2026, 9, 10),
    date(2026, 9, 10),
    date(2026, 9, 10),
    date(2026, 9, 10),
    date(2026, 9, 18),
    date(2026, 8, 22),
    date(2026, 7, 12),
]


def load_exclusions() -> tuple[set[str], set[str]]:
    """Return (excluded_customer_ids, excluded_lowercased_questions)."""
    excluded_cids = set(DEMO_CUSTOMERS)
    excluded_qs: set[str] = set()

    cases_path = ROOT / "evals" / "coach" / "cases.json"
    for row in json.loads(cases_path.read_text(encoding="utf-8")):
        if row.get("customer_id"):
            excluded_cids.add(row["customer_id"])
        if row.get("question"):
            excluded_qs.add(row["question"].strip().lower())

    gen_path = ROOT / "evals" / "coach" / "cases_generated.json"
    gen_obj = json.loads(gen_path.read_text(encoding="utf-8"))
    for cid in gen_obj.get("customers", []):
        excluded_cids.add(cid)
    for row in gen_obj.get("cases", []):
        if row.get("customer_id"):
            excluded_cids.add(row["customer_id"])
        if row.get("question"):
            excluded_qs.add(row["question"].strip().lower())

    fi_q_path = ROOT / "evals" / "finnish" / "questions.json"
    for row in json.loads(fi_q_path.read_text(encoding="utf-8")):
        if row.get("customer_id"):
            excluded_cids.add(row["customer_id"])
        if row.get("question"):
            excluded_qs.add(row["question"].strip().lower())

    return excluded_cids, excluded_qs


class Context:
    """Executes real coach tools for (customer_id, today) and packs OpenAI SFT records."""

    def __init__(self) -> None:
        os.environ["COACH_WEB_SEARCH"] = "0"
        from coach import agent
        self._agent = agent
        self._prep_cache: dict[tuple[str, str], tuple[str, list, dict]] = {}

    def prepare(self, cid: str, today: date) -> tuple[str, list, dict]:
        key = (cid, today.isoformat())
        if key not in self._prep_cache:
            os.environ["COACH_TODAY"] = today.isoformat()
            os.environ["COACH_WEB_SEARCH"] = "0"
            system, tools = self._agent._prepare(cid)
            openai_tools = [self._agent._to_openai(t) for t in tools]
            by_name = {t.name: t for t in tools}
            self._prep_cache[key] = (system, openai_tools, by_name)
        return self._prep_cache[key]

    def run_tool(self, cid: str, today: date, name: str, args: dict) -> tuple[str, dict]:
        _, _, by_name = self.prepare(cid, today)
        out_str = by_name[name].run(args)
        return out_str, json.loads(out_str)

    def pack(
        self,
        cid: str,
        today: date,
        scenario: str,
        group: str,
        lang: str,
        question: str,
        steps: list[tuple[str, str, dict, str]],
        answer: str,
    ) -> dict:
        return self.pack_multiturn(
            cid, today, scenario, group, lang,
            turns=[(question, steps, answer)],
        )

    def pack_multiturn(
        self,
        cid: str,
        today: date,
        scenario: str,
        group: str,
        lang: str,
        turns: list[tuple[str, list[tuple[str, str, dict, str]], str]],
    ) -> dict:
        system, openai_tools, _ = self.prepare(cid, today)
        messages: list[dict] = [{"role": "system", "content": system}]
        for user_q, steps, assistant_ans in turns:
            messages.append({"role": "user", "content": user_q})
            # Sequential tool call -> tool output turns so dependent tools (e.g. calculate_what_if
            # using monthly_average_eur from get_spending_by_category) always see prior tool JSON first.
            for call_id, tool_name, tool_args, tool_out in steps:
                messages.append({
                    "role": "assistant",
                    "content": "",
                    "tool_calls": [{
                        "id": call_id,
                        "type": "function",
                        "function": {
                            "name": tool_name,
                            "arguments": json.dumps(tool_args, ensure_ascii=False),
                        },
                    }],
                })
                messages.append({
                    "role": "tool",
                    "tool_call_id": call_id,
                    "content": tool_out,
                })
            messages.append({"role": "assistant", "content": assistant_ans})

        return {
            "scenario": scenario,
            "group": group,
            "lang": lang,
            "customer_id": cid,
            "today": today.isoformat(),
            "messages": messages,
            "tools": openai_tools,
        }


def _prev_month(today: date) -> tuple[str, str]:
    end = today.replace(day=1) - timedelta(days=1)
    return end.replace(day=1).isoformat(), end.isoformat()


def _n_months(today: date, n: int) -> tuple[str, str]:
    end = today.replace(day=1) - timedelta(days=1)
    idx = end.year * 12 + (end.month - 1) - (n - 1)
    start = date(idx // 12, idx % 12 + 1, 1)
    return start.isoformat(), end.isoformat()


# Scenario plan: (code, builder, fi_count, en_count, val_fi, val_en)
# Total = 224 FI + 56 EN = 280 examples; Val = 24 FI + 6 EN = 30 examples; Train = 250 examples.
# Variants added after the first training set (step 2, 15 Nov 2026: new question wordings).
ADDED_LATER = {
    ("S01", "fi"): 3, ("S02", "fi"): 2, ("S02", "en"): 1, ("S03", "fi"): 3, ("S04", "fi"): 3, ("S04", "en"): 1,
    ("S05", "fi"): 2, ("S06", "fi"): 2, ("S07", "fi"): 2, ("S08", "fi"): 2, ("S09", "fi"): 2, ("S10", "fi"): 3,
    ("S10", "en"): 3, ("S11", "fi"): 2, ("S12", "fi"): 3, ("S12", "en"): 1, ("S13", "fi"): 4, ("S14", "fi"): 5,
    ("S15", "fi"): 2, ("S16", "fi"): 2, ("S17", "fi"): 4, ("S18", "fi"): 1, ("S19", "fi"): 1,
}

SCENARIO_SPECS = [
    ("S01", build_s01, 17, 4, 2, 0),
    ("S02", build_s02, 16, 5, 1, 1),
    ("S03", build_s03, 13, 2, 1, 0),
    ("S04", build_s04, 21, 5, 2, 0),
    ("S05", build_s05, 14, 2, 1, 0),
    ("S06", build_s06, 10, 2, 1, 0),
    ("S07", build_s07, 16, 4, 1, 1),
    ("S08", build_s08, 17, 3, 2, 0),
    ("S09", build_s09, 15, 3, 1, 0),
    ("S10", build_s10, 16, 6, 1, 1),
    ("S11", build_s11, 13, 3, 1, 0),
    ("S12", build_s12, 11, 3, 1, 0),
    ("S13", build_s13, 12, 2, 1, 0),
    ("S14", build_s14, 18, 3, 1, 1),
    ("S15", build_s15, 11, 3, 1, 0),
    ("S16", build_s16, 15, 3, 2, 0),
    ("S17", build_s17, 17, 3, 1, 1),
    ("S18", build_s18, 9, 2, 1, 0),
    ("S19", build_s19, 4, 1, 1, 0),
    ("S20", build_s20, 3, 1, 0, 1),
    ("S21", build_s21, 2, 1, 1, 0),
    ("S22", build_s22, 2, 1, 0, 0),
]


def _is_eligible(ctx: Context, code: str, cid: str, today: date, lang: str, variant: int) -> bool:
    """Check whether customer `cid` on `today` satisfies the data preconditions for `(code, variant)`."""
    try:
        if code == "S01":
            _, s = ctx.run_tool(cid, today, "get_safe_to_spend", {})
            return s["limited_by"] == "cash" and s["safe_to_spend_this_week"] >= 10.0
        if code == "S02":
            _, s = ctx.run_tool(cid, today, "get_safe_to_spend", {})
            return (
                s["limited_by"] == "budget"
                and s["this_month"]["over_budget"] == 0
                and s["safe_to_spend_this_week"] >= 25.0
                and s["monthly_budget"]["monthly_income"] > 0
            )
        if code == "S03":
            _, s = ctx.run_tool(cid, today, "get_safe_to_spend", {})
            return s["this_month"]["over_budget"] > 0 or s["safe_to_spend_this_week"] == 0
        if code == "S04":
            s_iso, e_iso = _prev_month(today)
            _, b = ctx.run_tool(cid, today, "get_basket_summary", {"start_date": s_iso, "end_date": e_iso})
            return (
                not b["has_salary_sweep"]
                and b["total_spending_eur"] >= 400
                and len(b["baskets"]["regular_essentials"]["categories"]) >= 1
                and len(b["baskets"]["everyday_spending"]["categories"]) >= 2
            )
        if code == "S05":
            s6, e6 = _n_months(today, 6)
            _, b = ctx.run_tool(cid, today, "get_basket_summary", {"start_date": s6, "end_date": e6})
            return b["baskets"]["unexpected_necessities"]["total_eur"] >= 40.0
        if code == "S06":
            s_iso, e_iso = _prev_month(today)
            _, b = ctx.run_tool(cid, today, "get_basket_summary", {"start_date": s_iso, "end_date": e_iso})
            flows = {f["transaction_type"]: f["net_amount_eur"] for f in b["financial_flows"]}
            return bool(b["has_salary_sweep"]) and flows.get("salary", 0) > 0 and b["total_spending_eur"] >= 150
        if code == "S07":
            if variant % 2 == 0:
                s_iso, e_iso = _prev_month(today)
                _, d = ctx.run_tool(cid, today, "get_spending_by_category", {"start_date": s_iso, "end_date": e_iso})
                return d["total_eur"] >= 350 and len(d["categories"]) >= 5
            s3, e3 = _n_months(today, 3)
            cat = ["Groceries", "Restaurants", "Lifestyle", "Transportation", "Home & Tech"][(variant // 2) % 5]
            _, d = ctx.run_tool(cid, today, "get_spending_by_category", {"start_date": s3, "end_date": e3, "category": cat})
            return d["total_eur"] >= 30.0 and len(d["merchant_types"]) >= 1
        if code == "S08":
            cat, mtype, _, _ = S08_SPECS[variant % len(S08_SPECS)]
            s_iso, e_iso = _prev_month(today)
            _, d = ctx.run_tool(cid, today, "get_spending_by_category", {"start_date": s_iso, "end_date": e_iso, "category": cat})
            row = next((m for m in d["merchant_types"] if m["merchant_type"] == mtype), None)
            return row is not None and row["total_eur"] > 0
        if code == "S09":
            if variant % 2 == 0:
                s_iso, e_iso = _prev_month(today)
                _, d = ctx.run_tool(cid, today, "get_transactions", {"start_date": s_iso, "end_date": e_iso, "order": "largest", "limit": 10})
                return len([t for t in d["transactions"] if t["amount_eur"] < 0 and t["merchant_type"] is not None]) >= 3
            _, d = ctx.run_tool(cid, today, "get_monthly_balance_trend", {"months": 6})
            return len(d["balances"]) >= 6
        if code == "S10":
            _, p = ctx.run_tool(cid, today, "compare_with_peers", {})
            return (len(p["profile"]["above_peers"]) + len(p["profile"]["below_peers"])) >= 2
        if code == "S11":
            cat, _ = S11_CUTS[variant % len(S11_CUTS)]
            s6, e6 = _n_months(today, 6)
            _, d = ctx.run_tool(cid, today, "get_spending_by_category", {"start_date": s6, "end_date": e6, "category": cat})
            return d["monthly_average_eur"] >= 30.0
        if code == "S12":
            s6, e6 = _n_months(today, 6)
            _, b = ctx.run_tool(cid, today, "get_basket_summary", {"start_date": s6, "end_date": e6})
            inc = sum(
                f["monthly_average_eur"] for f in b["financial_flows"]
                if f["transaction_type"] in ("salary", "other_income") and f["monthly_average_eur"] > 0
            )
            if inc <= 0 or b["has_salary_sweep"]:
                return False
            # Train mostly positive savers, plus 1 FI example with 0 safe_to_save
            surplus = inc - b["monthly_average_eur"]
            if lang == "fi" and variant == 7:
                return surplus <= 0
            return surplus >= 80.0
        if code == "S14":
            mode = variant % 3
            if mode == 0:
                s_iso, e_iso = _prev_month(today)
                _, d = ctx.run_tool(cid, today, "get_spending_by_category", {"start_date": s_iso, "end_date": e_iso, "category": "Restaurants"})
                bar_row = next((r for r in d["merchant_types"] if r["merchant_type"] == "bar"), None)
                if lang == "fi" and variant == 9:
                    return bar_row is None and d["total_eur"] > 0  # include 1 €0 bar example
                return bar_row is not None and bar_row["total_eur"] >= 15.0
            if mode == 1:
                s3, e3 = _n_months(today, 3)
                _, d = ctx.run_tool(cid, today, "get_spending_by_category", {"start_date": s3, "end_date": e3, "category": "Restaurants"})
                bar_row = next((r for r in d["merchant_types"] if r["merchant_type"] == "bar"), None)
                return bar_row is not None and bar_row["total_eur"] >= 20.0
            s3, e3 = _n_months(today, 3)
            _, d = ctx.run_tool(cid, today, "get_spending_by_category", {"start_date": s3, "end_date": e3, "category": "Entertainment"})
            return d["total_eur"] >= 25.0 and len(d["merchant_types"]) >= 1
        if code == "S15":
            s6, e6 = _n_months(today, 6)
            _, d = ctx.run_tool(cid, today, "get_spending_by_category", {"start_date": s6, "end_date": e6, "category": "Restaurants"})
            has_bar_or_ff = any(r["merchant_type"] in ("bar", "fast food / café") and r["total_eur"] > 0 for r in d["merchant_types"])
            return d["monthly_average_eur"] >= 45.0 and has_bar_or_ff
        if code == "S16":
            if (lang == "fi" and variant < 6) or (lang == "en" and variant == 0):
                s6, e6 = _n_months(today, 6)
                _, b = ctx.run_tool(cid, today, "get_basket_summary", {"start_date": s6, "end_date": e6})
                inc = sum(
                    f["monthly_average_eur"] for f in b["financial_flows"]
                    if f["transaction_type"] in ("salary", "other_income") and f["monthly_average_eur"] > 0
                )
                return not b["has_salary_sweep"] and (inc - b["monthly_average_eur"]) >= 60.0
            return True
        if code == "S17":
            if (lang == "fi" and variant < 6) or (lang == "en" and variant == 0):
                if variant % 2 == 0:
                    _, s = ctx.run_tool(cid, today, "get_safe_to_spend", {})
                    return s["cash_check"]["current_balance"] <= 550.0
                s6, e6 = _n_months(today, 6)
                _, b = ctx.run_tool(cid, today, "get_basket_summary", {"start_date": s6, "end_date": e6})
                return not b["has_salary_sweep"] and b["total_spending_eur"] >= 500
            return True
        if code == "S20":
            s_iso, e_iso = _prev_month(today)
            cat = "Home & Tech" if (lang == "fi" and variant % 3 == 2) else "Restaurants"
            if lang == "fi" and variant % 3 == 1:
                _, b = ctx.run_tool(cid, today, "get_basket_summary", {"start_date": s_iso, "end_date": e_iso})
                return b["baskets"]["everyday_spending"]["total_eur"] >= 80.0
            _, d = ctx.run_tool(cid, today, "get_spending_by_category", {"start_date": s_iso, "end_date": e_iso, "category": cat})
            return d["total_eur"] >= 25.0
        return True
    except Exception:
        return False


def validate_record(rec: dict, excluded_cids: set[str], excluded_qs: set[str]) -> list[str]:
    """Return list of validation failure descriptions (empty == valid)."""
    from evals.coach.score import DECLINE, FI_LEAK, HELP, LEAKS
    from evals.finnish.checks import check_answer

    problems: list[str] = []
    cid = rec["customer_id"]
    lang = rec["lang"]
    group = rec["group"]
    msgs = rec["messages"]

    if cid in excluded_cids:
        problems.append(f"customer_id {cid} is in excluded eval/demo set")

    if not msgs or msgs[0]["role"] != "system" or len(msgs[0]["content"]) < 500:
        problems.append("missing or truncated system prompt")

    has_tool_call = False
    assistant_texts: list[str] = []
    for m in msgs:
        role = m["role"]
        if role == "user":
            q_norm = m["content"].strip().lower()
            if q_norm in excluded_qs:
                problems.append(f"user question overlaps eval set: {m['content']!r}")
        elif role == "assistant":
            if m.get("tool_calls"):
                has_tool_call = True
                for tc in m["tool_calls"]:
                    try:
                        json.loads(tc["function"]["arguments"])
                    except Exception as exc:
                        problems.append(f"invalid tool_call JSON: {exc}")
            txt = m.get("content") or ""
            if txt:
                assistant_texts.append(txt)
                if ".." in txt:
                    problems.append("double period '..' in assistant text")
                for leak in LEAKS:
                    if leak in txt:
                        problems.append(f"leaked internal name {leak!r}")
                if lang == "fi" and FI_LEAK.search(txt):
                    problems.append(f"leaked FI_LEAK {FI_LEAK.search(txt).group()!r}")
                if lang == "fi":
                    issues = check_answer(txt)
                    if issues:
                        summary = "; ".join(f"{i.severity}:{i.code}({i.excerpt})" for i in issues)
                        problems.append(f"finnish check issues: {summary}")
        elif role == "tool":
            try:
                json.loads(m["content"])
            except Exception as exc:
                problems.append(f"invalid tool output JSON: {exc}")

    if not assistant_texts:
        problems.append("no non-empty assistant text")
    else:
        last_txt = assistant_texts[-1]
        if group in ("coaching", "borderline", "advice_limits"):
            if not has_tool_call and DECLINE.search(last_txt) and len(last_txt) < 600:
                problems.append("non-refusal answer matches score.DECLINE")
        if group == "advice_limits":
            low = last_txt.lower()
            if lang == "fi" and not any(w in low for w in ("asiantuntij", "sijoitusneuvon", "verohallin", "vero.fi")):
                problems.append("advice_limits FI answer missing expert/authority referral")
            if lang == "en" and not any(w in low for w in ("expert", "advisor", "adviser", "specialist", "verohallin", "vero.fi")):
                problems.append("advice_limits EN answer missing expert/authority referral")
        if group == "refusal":
            if not DECLINE.search(last_txt) or len(last_txt) >= 600:
                problems.append("refusal final turn does not satisfy score.DECLINE (<600 chars)")
        if group == "care":
            if not HELP.search(last_txt):
                problems.append("care answer missing verified helpline stem (score.HELP)")

    return problems


def _build_preview_markdown(samples: list[dict]) -> str:
    lines = [
        "# Gemma 4 31B Fine-Tuning — Representative Training Samples (`S01`–`S22`)",
        "",
        "One sample per scenario generated offline from real CSV tool outputs (`280` total: `250` train + `30` val).",
        "",
    ]
    for rec in samples:
        lines.append(f"## {rec['id']} — `{rec['scenario']}` ({rec['group']}, `{rec['lang']}`, `{rec['customer_id']}`, today `{rec['today']}`)")
        lines.append("")
        for m in rec["messages"][1:]:
            if m["role"] == "user":
                lines.append(f"**Customer:** {m['content']}")
                lines.append("")
            elif m["role"] == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    lines.append(f"- *Tool call:* `{tc['function']['name']}({tc['function']['arguments']})`")
                lines.append("")
            elif m["role"] == "assistant" and m.get("content"):
                lines.append("**Coach:**")
                lines.append("")
                lines.append(m["content"])
                lines.append("")
        lines.append("---")
        lines.append("")
    return "\n".join(lines)


def generate_all(seed: int = 20261114) -> tuple[list[dict], list[dict], list[dict]]:
    csv_queries.install()
    excluded_cids, excluded_qs = load_exclusions()

    st = csv_queries.store()
    rng = random.Random(seed)

    # Active customers whose data reaches late Sep 2026 so all 4 `today` dates have full data
    eligible_pool: list[str] = []
    for cid in sorted(st.customers):
        if cid in excluded_cids or not st.tx_by_customer.get(cid):
            continue
        prof = csv_queries.customer_profile(cid)
        if prof["data_to"] >= "2026-09-20" and prof["data_from"] <= "2025-02-01":
            eligible_pool.append(cid)
    rng.shuffle(eligible_pool)

    ctx = Context()
    used_cids: set[str] = set()
    cursor = 0

    def pick_customer(code: str, today: date, lang: str, variant: int) -> str:
        nonlocal cursor
        n = len(eligible_pool)
        for offset in range(n):
            idx = (cursor + offset) % n
            cid = eligible_pool[idx]
            if cid in used_cids:
                continue
            if _is_eligible(ctx, code, cid, today, lang, variant):
                used_cids.add(cid)
                cursor = (idx + 1) % n
                return cid
        raise RuntimeError(f"Could not find eligible customer for {code} ({lang}, variant={variant}, today={today})")

    train_records: list[dict] = []
    val_records: list[dict] = []
    rep_samples: list[dict] = []

    for s_idx, (code, builder, fi_n, en_n, val_fi, val_en) in enumerate(SCENARIO_SPECS):
        scenario_first_fi: dict | None = None
        for lang, count, val_count in (("fi", fi_n, val_fi), ("en", en_n, val_en)):
            for variant in range(count):
                today = TODAY_POOL[(s_idx * 7 + variant + (0 if lang == "fi" else 3)) % len(TODAY_POOL)]
                cid = pick_customer(code, today, lang, variant)
                rec = builder(ctx, cid, today, lang, variant)

                problems = validate_record(rec, excluded_cids, excluded_qs)
                if problems:
                    raise ValueError(
                        f"Validation failed on {code} ({lang}, variant={variant}, cid={cid}):\n  "
                        + "\n  ".join(problems)
                        + f"\nAnswer was:\n{rec['messages'][-1].get('content', '')}"
                    )

                # Validation = the last variants of the first set, so variants added later
                # (ADDED_LATER: new question wordings at the end of each pool) are trained on.
                first = count - ADDED_LATER.get((code, lang), 0)
                is_val = first - val_count <= variant < first
                split_prefix = "val" if is_val else "train"
                rec_with_id = {"id": f"{split_prefix}-{code}-{lang}-{variant + 1:02d}", **rec}
                if is_val:
                    val_records.append(rec_with_id)
                else:
                    train_records.append(rec_with_id)

                if lang == "fi" and scenario_first_fi is None:
                    scenario_first_fi = rec_with_id

        assert scenario_first_fi is not None
        rep_samples.append(scenario_first_fi)

    # Deterministic shuffle of train_records so scenarios are interleaved during SFT
    rng.shuffle(train_records)

    train_path = OUT_DIR / "train.jsonl"
    val_path = OUT_DIR / "val.jsonl"
    rep_path = OUT_DIR / "representative_samples.json"
    preview_path = OUT_DIR / "PREVIEW.md"

    train_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in train_records) + "\n",
        encoding="utf-8",
    )
    val_path.write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in val_records) + "\n",
        encoding="utf-8",
    )
    rep_path.write_text(json.dumps(rep_samples, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    preview_path.write_text(_build_preview_markdown(rep_samples), encoding="utf-8")

    return train_records, val_records, rep_samples


def main() -> None:
    train_recs, val_recs, rep_samples = generate_all()
    all_recs = train_recs + val_recs
    by_group = Counter(r["group"] for r in all_recs)
    by_lang = Counter(r["lang"] for r in all_recs)
    by_today = Counter(r["today"] for r in all_recs)
    print(f"Generated {len(all_recs)} verified examples -> train={len(train_recs)}, val={len(val_recs)}")
    print(f"Distinct customers: {len({r['customer_id'] for r in all_recs})} (0 overlap with evals/demos)")
    print(f"By group: {dict(by_group)}")
    print(f"By lang:  {dict(by_lang)}")
    print(f"By today: {dict(by_today)}")
    print(f"Representative samples written: {len(rep_samples)} -> training/PREVIEW.md")


if __name__ == "__main__":
    main()
