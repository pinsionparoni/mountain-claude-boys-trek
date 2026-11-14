"""
Put several test-set runs side by side as a Markdown table.

    .venv/bin/python -m evals.coach.compare                      # every run in results/
    .venv/bin/python -m evals.coach.compare results/A results/B  # chosen runs
"""

import json
import sys
from pathlib import Path

from evals.coach.run import RESULTS

GROUPS = [
    ("correct", "Correct numbers and tools"),
    ("overrefusal", "Answers awkward-but-allowed questions"),
    ("refuse", "Declines harmful / off-topic"),
    ("care", "Points to help when needed"),
    ("advice", "Investment/loan/tax: general only"),
    ("chat", "Small talk"),
]


def table(folders):
    runs = [json.loads((f / "summary.json").read_text(encoding="utf-8")) for f in folders]
    head = "| | " + " | ".join(r["name"] for r in runs) + " |"
    lines = [head, "|---" * (len(runs) + 1) + "|"]
    for key, label in GROUPS:
        cells = []
        for r in runs:
            p, n = r["groups"].get(key, [0, 0])
            span = r.get("group_ranges_95", {}).get(key)
            cells.append((f"{p}/{n}" + (f" ({span[0]}–{span[1]} %)" if span else "")) if n else "–")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines.append("| **All cases** | " + " | ".join(
        f"**{r['passed']}/{r['cases']}**" + (f" ({r['range_95'][0]}–{r['range_95'][1]} %)" if r.get("range_95") else "")
        for r in runs) + " |")
    lines.append("| Leaked internal names | " + " | ".join(str(r["failed_checks"].get("no_leaks", 0)) for r in runs) + " |")
    lines.append("| Finnish answers with errors | " + " | ".join(str(r["failed_checks"].get("finnish", 0)) for r in runs) + " |")
    lines.append("| Median time to first words | " + " | ".join(
        f"{r['median_first_words_s']} s" if r["median_first_words_s"] else "–" for r in runs) + " |")
    return "\n".join(lines)


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    folders = [Path(a) for a in args] or sorted(p for p in RESULTS.glob("*") if (p / "summary.json").exists())
    print(table(folders))


if __name__ == "__main__":
    main()
