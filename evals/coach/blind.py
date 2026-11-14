"""
Blind rating of Finnish answers: the same questions, answers from two or more
models shuffled into unlabelled columns, rated by a native speaker.

    # 1. Make the sheet from saved runs (the first answer of each case is used):
    .venv/bin/python -m evals.coach.blind make evals/coach/results/<gemma run> evals/coach/results/<opus run>

    # 2. A native speaker fills in the scores (1-5) without knowing which model is which.

    # 3. Reveal: average scores per model
    .venv/bin/python -m evals.coach.blind reveal <filled sheet.xlsx> <key.json>

The key (which column is which model) is written next to the results, not next to
the sheet: don't open it before rating. Only Finnish questions whose answer is
written by the model are used; guardrail replies are fixed texts, identical for
every model, so they're left out.
"""

import argparse
import json
import random
import sys
from datetime import datetime
from pathlib import Path

from evals.coach.run import RESULTS

GROUPS = ("correct", "overrefusal", "advice", "chat")
LETTERS = "ABCDE"
SCORES = ("Finnish 1-5", "Bank language 1-5")


def first_answers(folder):
    rows = [json.loads(l) for l in (Path(folder) / "answers.jsonl").read_text(encoding="utf-8").splitlines() if l]
    summary = json.loads((Path(folder) / "summary.json").read_text(encoding="utf-8"))
    answers = {}
    for r in rows:
        if r["id"] not in answers and not r.get("error") and r["answer"] and r.get("guardrail") is None:
            answers[r["id"]] = r
    return summary["name"], answers


def make(folders, count, out, seed):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font

    runs = [first_answers(f) for f in folders]
    shared = sorted(set.intersection(*(set(a) for _, a in runs)))
    cases = [cid for cid in shared
             if runs[0][1][cid]["lang"] == "fi" and runs[0][1][cid]["group"] in GROUPS]
    rng = random.Random(seed)
    cases = rng.sample(cases, min(count, len(cases)))

    wb = Workbook()
    ws = wb.active
    ws.title = "rating"
    n = len(runs)
    header = ["#", "question"] + [f"answer {LETTERS[i]}" for i in range(n)]
    header += [f"{LETTERS[i]}: {s}" for i in range(n) for s in SCORES] + ["best (A/B/…/same)", "comment"]
    ws.append(header)
    key = {"made": datetime.now().isoformat(timespec="minutes"), "runs": [name for name, _ in runs], "rows": []}
    for i, cid in enumerate(cases, 1):
        order = list(range(n))
        rng.shuffle(order)
        ws.append([i, runs[0][1][cid]["question"]] + [runs[j][1][cid]["answer"] for j in order])
        key["rows"].append({"row": i, "case": cid, "columns": {LETTERS[k]: runs[j][0] for k, j in enumerate(order)}})

    wrap = Alignment(wrap_text=True, vertical="top")
    widths = [4, 30] + [60] * n + [12] * (n * len(SCORES)) + [14, 40]
    for col, width in enumerate(widths, 1):
        ws.column_dimensions[ws.cell(1, col).column_letter].width = width
    for row in ws.iter_rows():
        for cell in row:
            cell.alignment = wrap
    for cell in ws[1]:
        cell.font = Font(bold=True)
    ws.freeze_panes = "C2"

    info = wb.create_sheet("how to rate")
    for line in [
        "Rate every answer without trying to guess which model wrote it.",
        "Finnish 1-5: 1 = clearly wrong or unnatural, 3 = understandable but clumsy, 5 = natural, correct Finnish.",
        "Bank language 1-5: 1 = wrong or English terms, 3 = OK, 5 = sounds like S-Bank (friendly, sinuttelu, right banking words).",
        "Best: which answer you'd rather show a customer (A, B, ... or same).",
        "Comment: anything worth fixing; better wording is very welcome.",
        "Don't open the key file before you've finished.",
    ]:
        info.append([line])
    info.column_dimensions["A"].width = 120

    out.parent.mkdir(parents=True, exist_ok=True)
    wb.save(out)
    key_path = RESULTS / f"blind-key-{datetime.now():%Y%m%d-%H%M}.json"
    key_path.write_text(json.dumps(key, indent=1, ensure_ascii=False), encoding="utf-8")
    print(f"{len(cases)} questions, {n} models -> {out}\nKey (don't open before rating): {key_path}")


def reveal(sheet, key_path):
    from openpyxl import load_workbook

    key = json.loads(Path(key_path).read_text(encoding="utf-8"))
    ws = load_workbook(sheet, data_only=True)["rating"]
    rows = list(ws.iter_rows(values_only=True))
    header = rows[0]
    by_row = {r["row"]: r for r in key["rows"]}
    totals = {name: {s: [] for s in SCORES} | {"best": 0} for name in key["runs"]}
    rated = 0
    for values in rows[1:]:
        k = by_row.get(values[0])
        if not k:
            continue
        cell = dict(zip(header, values))
        any_score = False
        for letter, name in k["columns"].items():
            for s in SCORES:
                v = cell.get(f"{letter}: {s}")
                if isinstance(v, (int, float)):
                    totals[name][s].append(float(v))
                    any_score = True
        best = str(cell.get("best (A/B/…/same)") or "").strip().upper()
        if best in k["columns"]:
            totals[k["columns"][best]]["best"] += 1
        rated += any_score
    print(f"{rated} rated questions\n")
    print("| Model | " + " | ".join(SCORES) + " | Chosen as best |")
    print("|---|" + "---|" * (len(SCORES) + 1))
    for name, t in totals.items():
        avgs = [f"{sum(v) / len(v):.2f} ({len(v)})" if v else "–" for v in (t[s] for s in SCORES)]
        print(f"| {name} | " + " | ".join(avgs) + f" | {t['best']} |")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    m = sub.add_parser("make", help="make a blind rating sheet from saved runs")
    m.add_argument("runs", nargs="+", type=Path, help="two or more run folders")
    m.add_argument("--count", type=int, default=30, help="number of questions (default 30)")
    m.add_argument("--out", type=Path, default=Path("finnish-blind-rating.xlsx"))
    m.add_argument("--seed", type=int, default=1)
    r = sub.add_parser("reveal", help="average the scores per model")
    r.add_argument("sheet", type=Path)
    r.add_argument("key", type=Path)
    args = parser.parse_args(argv)
    if args.command == "make":
        if not 2 <= len(args.runs) <= len(LETTERS):
            sys.exit("give 2-5 run folders")
        make(args.runs, args.count, args.out, args.seed)
    else:
        reveal(args.sheet, args.key)


if __name__ == "__main__":
    main()
