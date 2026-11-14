"""
Ask the coach the fixed Finnish questions and check the language of its answers.

    # Run the model (uses COACH_MODEL, COACH_TODAY and the keys in .env):
    .venv/bin/python -m evals.finnish.run

    # Only re-check answers saved earlier (no model, no database). Use this
    # after editing the checks, or on answers from a fine-tuned model saved
    # in the same JSONL format:
    .venv/bin/python -m evals.finnish.run --check evals/finnish/results/<run>/answers.jsonl

Each run writes a folder under evals/finnish/results/ (ignored by git):

- answers.jsonl: one line per question: id, customer_id, question, answer,
  tools called, model, seconds, issues, and the full conversation including
  tool results (what fine-tuning needs).
- report.md: issue counts by type, then every flagged answer with excerpts.
- review.csv: one row per answer for a native speaker: the answer, its
  issues, and empty corrected_answer and notes columns. Corrected answers
  become fine-tuning examples. Opens in Excel and Google Sheets.
"""

import argparse
import csv
import json
import os
import sys
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

from evals.finnish.checks import ERROR, check_answer

HERE = Path(__file__).parent
QUESTIONS = HERE / "questions.json"
RESULTS = HERE / "results"


def ask(question):
    """One fresh conversation: returns the answer, the tools called and the messages."""
    from coach import agent  # imported here so --check needs no model or database

    messages = [{"role": "user", "content": question["question"]}]
    text, tools = [], []
    for kind, value in agent.chat_stream(messages, question["customer_id"]):
        (text if kind == "text" else tools).append(value)
    return "".join(text), tools, messages


def run_model(questions, only=None):
    from coach.agent import COACH_MODEL

    rows = []
    for q in questions:
        if only and q["id"] not in only:
            continue
        print(f"{q['id']:16} {q['customer_id']}  {q['question']}", flush=True)
        start = time.time()
        try:
            answer, tools, messages = ask(q)
            error = None
        except Exception as e:  # keep going; a failed question is reported, not fatal
            answer, tools, messages, error = "", [], [], f"{type(e).__name__}: {e}"
            print(f"  failed: {error}", file=sys.stderr)
        rows.append({
            **q,
            "answer": answer,
            "tools": tools,
            "model": COACH_MODEL,
            "coach_today": os.getenv("COACH_TODAY") or None,
            "seconds": round(time.time() - start, 1),
            "error": error,
            "messages": messages,
        })
    return rows


def add_issues(rows):
    for row in rows:
        row["issues"] = [i.as_dict() for i in check_answer(row["answer"])]
    return rows


def write_report(rows, folder, title):
    counts = Counter((i["code"], i["severity"]) for r in rows for i in r["issues"])
    answers_with = Counter(code for r in rows for code in {i["code"] for i in r["issues"]})
    errors = sum(1 for r in rows if any(i["severity"] == ERROR for i in r["issues"]))
    clean = sum(1 for r in rows if not r["issues"] and not r.get("error"))
    failed = [r for r in rows if r.get("error")]

    lines = [
        f"# Finnish language check: {title}",
        "",
        f"- Answers: {len(rows)} (model: {', '.join(sorted({str(r.get('model')) for r in rows}))})",
        f"- Clean: {clean}",
        f"- With at least one error: {errors}",
        f"- Issues in total: {sum(counts.values())}",
    ]
    if failed:
        lines.append(f"- Failed to answer: {len(failed)} ({', '.join(r['id'] for r in failed)})")
    lines += ["", "| Issue | Severity | Count | Answers |", "|---|---|---|---|"]
    for (code, severity), n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        lines.append(f"| `{code}` | {severity} | {n} | {answers_with[code]} |")
    lines.append("")

    for r in rows:
        if not r["issues"] and not r.get("error"):
            continue
        lines += [f"## {r['id']} ({r['customer_id']})", "", f"**Q:** {r['question']}", ""]
        if r.get("error"):
            lines += [f"**Failed:** {r['error']}", ""]
        for i in r["issues"]:
            lines.append(f"- **{i['code']}** ({i['severity']}): `{i['excerpt']}`  \n  {i['hint']}")
        lines += ["", "<details><summary>Full answer</summary>", "", r["answer"], "", "</details>", ""]

    (folder / "report.md").write_text("\n".join(lines), encoding="utf-8")


def write_review_sheet(rows, folder):
    # utf-8-sig so Excel shows ä and ö correctly.
    with open(folder / "review.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["id", "customer_id", "question", "answer", "issues", "corrected_answer", "notes"])
        for r in rows:
            issues = "\n".join(f"{i['code']}: {i['excerpt']}" for i in r["issues"])
            writer.writerow([r["id"], r["customer_id"], r["question"], r["answer"], issues, "", ""])


def save(rows, folder, title):
    folder.mkdir(parents=True, exist_ok=True)
    with open(folder / "answers.jsonl", "w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False, default=str) + "\n")
    write_report(rows, folder, title)
    write_review_sheet(rows, folder)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--check", type=Path, help="re-check a saved answers.jsonl instead of running the model")
    parser.add_argument("--only", nargs="+", metavar="ID", help="run only these question ids")
    parser.add_argument("--out", type=Path, help="output folder (default: results/<time>-<model>)")
    args = parser.parse_args(argv)

    if args.check:
        rows = [json.loads(line) for line in args.check.read_text(encoding="utf-8").splitlines() if line.strip()]
        folder = args.out or args.check.parent
        title = f"re-check of {args.check}"
    else:
        rows = run_model(json.loads(QUESTIONS.read_text(encoding="utf-8")), args.only)
        model = rows[0]["model"] if rows else "none"
        folder = args.out or RESULTS / f"{datetime.now():%Y%m%d-%H%M}-{model}"
        title = f"{model}, {datetime.now():%Y-%m-%d %H:%M}"

    add_issues(rows)
    save(rows, folder, title)
    counts = Counter(i["code"] for r in rows for i in r["issues"])
    print(f"\n{len(rows)} answers, {sum(counts.values())} issues: "
          + (", ".join(f"{c} {n}" for c, n in counts.most_common()) or "none"))
    print(f"Report: {folder / 'report.md'}\nReview sheet: {folder / 'review.csv'}")


if __name__ == "__main__":
    main()
