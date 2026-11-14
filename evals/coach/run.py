"""
Run the coach test set (cases.json) on one model and score every answer.

    # Gemma on Verda, with the guardrail (uses COACH_MODEL and the keys in .env):
    COACH_TODAY=2026-09-10 COACH_MODEL=gemma .venv/bin/python -m evals.coach.run

    # Without the guardrail, to measure its effect:
    COACH_TODAY=2026-09-10 COACH_GUARDRAIL=0 .venv/bin/python -m evals.coach.run

    # Claude Opus 5.5 (needs ANTHROPIC_API_KEY):
    COACH_TODAY=2026-09-10 COACH_MODEL=claude .venv/bin/python -m evals.coach.run

    # Only some cases, or a name for the run:
    .venv/bin/python -m evals.coach.run --only budget-fi-1 drugs-fi-1 --name gemma-finetuned

Each run also writes review.csv: one row per answer, for checking by hand in Excel or
Google Sheets (fill in the "agree" and "comment" columns).

Always use COACH_TODAY=2026-09-10: the expected numbers in cases.json are for that date.
Compare runs with evals.coach.compare. Results go to evals/coach/results/ (not in git).

These cases are the TEST set: never use them, or answers to them, as training data
(see FINE_TUNING.md).
"""

import argparse
import csv
import json
import math
import os
import sys
import time
from collections import Counter, defaultdict
from datetime import datetime
from pathlib import Path

from evals.coach.score import score

HERE = Path(__file__).parent
CASES = HERE / "cases.json"                  # hand-written
GENERATED = HERE / "cases_generated.json"    # from generate.py
RESULTS = HERE / "results"


def ask(case):
    """One fresh conversation: answer text, tools called, guardrail label, seconds to first words."""
    from coach import agent  # imported here so scoring tests need no model

    messages = [{"role": "user", "content": case["question"]}]
    text, tools, guard = [], [], None
    start, first = time.time(), None
    for kind, value in agent.chat_stream(messages, case["customer_id"]):
        if kind == "text":
            first = first or time.time() - start
            text.append(value)
        elif kind == "tool":
            tools.append(value)
        elif kind == "guardrail":
            guard = value
    return "".join(text), tools, guard, first, time.time() - start, messages


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--only", nargs="+", metavar="ID", help="run only these case ids")
    parser.add_argument("--cases", choices=["all", "handwritten", "generated"], default="all",
                        help="which case files to run (default: all)")
    parser.add_argument("--repeat", type=int, default=1,
                        help="ask every case this many times; answers vary between runs")
    parser.add_argument("--name", help="name for this run (default: model and guardrail setting)")
    parser.add_argument("--rescore", type=Path, metavar="FOLDER",
                        help="score a saved run again (after changing the checks), without the model")
    args = parser.parse_args(argv)

    if args.rescore:
        rescore(args.rescore)
        return

    from coach import agent, guardrail

    if os.getenv("COACH_TODAY") != "2026-09-10":
        print("Warning: COACH_TODAY is not 2026-09-10, so expected numbers won't match.", file=sys.stderr)

    cases = load_cases(args.cases)
    if args.only:
        cases = [c for c in cases if c["id"] in args.only]

    name = args.name or f"{agent.COACH_MODEL}-{'guard' if guardrail.enabled() else 'noguard'}"
    folder = RESULTS / f"{datetime.now():%Y%m%d-%H%M}-{name}"
    folder.mkdir(parents=True, exist_ok=True)

    rows = []
    for case in [c for c in cases for _ in range(args.repeat)]:
        print(f"{case['id']:20} ", end="", flush=True)
        try:
            answer, tools, guard, first, total, messages = ask(case)
            error = None
        except Exception as e:  # keep going; a failed case counts as failed
            answer, tools, guard, first, total, messages, error = "", [], None, None, 0, [], f"{type(e).__name__}: {e}"
        result = score(case, answer, tools, guard) if not error else {"passed": False, "checks": {}, "notes": [error]}
        print("PASS" if result["passed"] else "FAIL", "; ".join(result["notes"])[:150])
        rows.append({**case, "answer": answer, "tools": tools, "guardrail": guard,
                     "first_words_s": round(first, 2) if first else None, "total_s": round(total, 2),
                     "model": agent.COACH_MODEL, "error": error, **result, "messages": messages})

    save(rows, folder, name, agent.COACH_MODEL, guardrail.enabled())


def load_cases(which="all"):
    cases = []
    if which in ("all", "handwritten"):
        cases += json.loads(CASES.read_text(encoding="utf-8"))
    if which in ("all", "generated") and GENERATED.exists():
        cases += json.loads(GENERATED.read_text(encoding="utf-8"))["cases"]
    return cases


def wilson(passed, total, z=1.96):
    """95% range for a pass rate, in percent: how sure we can be with this many cases."""
    if not total:
        return None
    p, d = passed / total, 1 + z * z / total
    centre = (p + z * z / (2 * total)) / d
    half = z * math.sqrt(p * (1 - p) / total + z * z / (4 * total * total)) / d
    return [round(100 * (centre - half)), round(100 * (centre + half))]


def rescore(folder):
    rows = [json.loads(line) for line in (folder / "answers.jsonl").read_text(encoding="utf-8").splitlines() if line]
    old = json.loads((folder / "summary.json").read_text(encoding="utf-8"))
    for r in rows:
        if not r.get("error"):
            r.update(score(r, r["answer"], r["tools"], r["guardrail"]))
    save(rows, folder, old["name"], old["model"], old["guardrail"])


def describe(must):
    """The case's rules in plain words, for the review sheet."""
    parts = []
    if must.get("tools_any"):
        parts.append("use one of: " + ", ".join(must["tools_any"]))
    if must.get("numbers"):
        parts.append("say " + ", ".join(f"{n} €" for n in must["numbers"]))
    if must.get("mention_any"):
        parts.append("mention one of: " + ", ".join(must["mention_any"]))
    if must.get("refused"):
        parts.append("decline")
    if must.get("care"):
        parts.append("point to help")
    if must.get("not_refused"):
        parts.append("answer (not decline)")
    return "; ".join(parts) + ("; " if parts else "") + "no internal names; Finnish without errors (fi)"


def write_review_sheet(rows, folder):
    # utf-8-sig so Excel shows ä and ö correctly.
    with open(folder / "review.csv", "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["id", "group", "lang", "customer_id", "question", "must", "model", "answer",
                    "result", "why_failed", "agree (y/n)", "comment"])
        for r in rows:
            w.writerow([r["id"], r["group"], r["lang"], r["customer_id"], r["question"], describe(r["must"]),
                        r.get("model"), r["answer"], "PASS" if r["passed"] else "FAIL",
                        "; ".join(r.get("notes", [])), "", ""])


def save(rows, folder, name, model, guard):
    with open(folder / "answers.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    write_review_sheet(rows, folder)

    by_group = defaultdict(list)
    for r in rows:
        by_group[r["group"]].append(r["passed"])
    firsts = [r["first_words_s"] for r in rows if r["first_words_s"]]
    summary = {
        "name": name,
        "model": model,
        "guardrail": guard,
        "coach_today": os.getenv("COACH_TODAY"),
        "cases": len(rows),
        "passed": sum(r["passed"] for r in rows),
        "groups": {g: [sum(v), len(v)] for g, v in sorted(by_group.items())},
        "range_95": wilson(sum(r["passed"] for r in rows), len(rows)),
        "group_ranges_95": {g: wilson(sum(v), len(v)) for g, v in sorted(by_group.items())},
        "median_first_words_s": sorted(firsts)[len(firsts) // 2] if firsts else None,
        "failed_checks": dict(Counter(k for r in rows for k, ok in r["checks"].items() if not ok)),
    }
    (folder / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"\n{summary['passed']}/{summary['cases']} passed (95% range {summary['range_95']} %)  "
          + "  ".join(f"{g} {p}/{n}" for g, (p, n) in summary["groups"].items()))
    print(f"Results: {folder}")


if __name__ == "__main__":
    main()
