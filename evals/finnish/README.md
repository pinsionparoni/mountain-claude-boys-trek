# Finnish language check

Finds Finnish mistakes in the coach's answers, to guide fine-tuning and to compare models before and after it.

## Run it

```bash
# Ask the 20 fixed questions (questions.json) and check the answers.
# Uses COACH_MODEL and the keys in .env; takes a few minutes with Gemma.
COACH_TODAY=2026-09-10 .venv/bin/python -m evals.finnish.run

# Only some questions
.venv/bin/python -m evals.finnish.run --only budget-1 peers-1

# Re-check saved answers without the model (after editing the rules, or for
# answers from a fine-tuned model saved in the same answers.jsonl format)
.venv/bin/python -m evals.finnish.run --check evals/finnish/results/<run>/answers.jsonl
```

Each run writes `results/<time>-<model>/` (not committed to git):

| File | For |
|---|---|
| `report.md` | Issue counts by type, then each flagged answer with the excerpt and a hint |
| `review.csv` | One row per answer for a native speaker. Fill in `corrected_answer` (and `notes`); corrected answers are fine-tuning examples. Opens in Excel / Google Sheets |
| `answers.jsonl` | Everything: question, answer, tools called, model, timing, issues and the full conversation with tool results |

Use `COACH_TODAY=2026-09-10` (the demo date) so answers are comparable between runs.

## What is checked

The rules (`checks.py`) are plain code, no AI: the same answer always gives the same result.

| Code | Severity | Example | Fix |
|---|---|---|---|
| `capital_mid_sentence` | error | *Asuminen (Lasku)* | *asuminen (lasku)* |
| `basket_name_capital` | warning | *kuuluvat ☕ Arjen kulutukseen* | *arjen kulutukseen*. The name itself (*☕ Arjen kulutus*) is fine |
| `capital_after_colon` | warning | *Pieni vinkki: Koska…* | *Pieni vinkki: koska…*. A bold label (*\*\*Vinkki:\*\* Koska*) is treated as a heading |
| `english_word` | error | *Lifestyle-menot*, *Home & Tech* | Finnish names |
| `decimal_point`, `euro_before_number`, `no_space_before_unit`, `no_thousands_space`, `date_leading_zero` | error / warning | *84.7%*, *€68.23*, *12345 €*, *01.09.2025* | *84,7 %*, *68,23 €*, *12 345 €*, *1.9.2025* |
| `anglicism`, `wrong_word`, `typo`, `grammar`, `age_range` | from `bad_phrases.py` | *hyvissä railseissa*, *ulkoilma-ateria*, *kulutuksiasi oli* | the hint in the list |

Proper nouns that may have a capital anywhere (S-Pankki, S-mobiili, Helsinki…) are in `ALLOWED_CAPITAL_PREFIXES` in `checks.py`.

**Rules can't catch** typos without a pattern, real words used wrongly, or clunky phrasing: that is what the review sheet is for. When a reviewer finds a mistake that could come back, add it to `bad_phrases.py` (a regex, a code, a severity and a Finnish hint) so later runs catch it automatically.

## Changing the rules

Tests are in `tests/test_finnish_checks.py`: real bad sentences that must be flagged and correct Finnish that must not be. Add an example with every rule change, then run `.venv/bin/python -m pytest tests/test_finnish_checks.py`.
