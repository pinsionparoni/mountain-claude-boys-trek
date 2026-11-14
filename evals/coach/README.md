# Coach test set

Measures the whole coach, not just its Finnish: right tools and numbers, declining what [POLICY.md](../../POLICY.md) says to decline, **not** declining awkward-but-allowed questions, pointing to help, advice limits, no internal names, and Finnish quality (via `evals/finnish`). Used to compare models and to prove fine-tuning helped ([FINE_TUNING.md](../../FINE_TUNING.md)). Latest results: [RESULTS.md](../../RESULTS.md).

**These are test questions: never use them, or answers to them, as training data.**

## Run it

```bash
# Gemma on Verda, guardrail on
COACH_TODAY=2026-09-10 COACH_MODEL=gemma .venv/bin/python -m evals.coach.run

# Guardrail off, to measure its effect
COACH_TODAY=2026-09-10 COACH_MODEL=gemma COACH_GUARDRAIL=0 .venv/bin/python -m evals.coach.run

# Claude Opus 5.5 (needs ANTHROPIC_API_KEY in .env; about $2-3 of credits)
COACH_TODAY=2026-09-10 COACH_MODEL=claude .venv/bin/python -m evals.coach.run

# Ask every case 3 times (answers vary between runs) and name the run
COACH_TODAY=2026-09-10 COACH_MODEL=gemma .venv/bin/python -m evals.coach.run --repeat 3 --name gemma-x3

# Only the hand-written or generated cases, or some cases only
.venv/bin/python -m evals.coach.run --cases handwritten
.venv/bin/python -m evals.coach.run --only budget-fi-1 drugs-fi-1

# Regenerate the generated cases (after changing templates; needs the database)
.venv/bin/python -m evals.coach.generate

# Score a saved run again after changing the checks (no model needed)
.venv/bin/python -m evals.coach.run --rescore evals/coach/results/<run>

# Side-by-side table of all runs (or chosen folders)
.venv/bin/python -m evals.coach.compare
```

`COACH_TODAY=2026-09-10` is required: the expected numbers in `cases.json` are for that date. Each run writes `results/<time>-<name>/` (not in git): `answers.jsonl` (every answer, tools, timing, checks and the full conversation) and `summary.json`.

## Files

| File | What |
|---|---|
| `cases.json` | 31 hand-written test cases, Finnish and English, in six groups: `correct`, `overrefusal`, `refuse`, `care`, `advice`, `chat` |
| `cases_generated.json` | 116 cases from `generate.py`: question templates × real customers × both languages, expected numbers computed with the coach's own tools. Lists the customers it uses |
| `generate.py` | Builds `cases_generated.json` deterministically (same output every time) |
| `score.py` | The rules, plain code: `tools_any`, `numbers` (either number format), `mention_any`, `refused`, `care`, `not_refused`, plus leak and Finnish checks on every case |
| `run.py` | Runs the cases on the current `COACH_MODEL` (`--repeat`, `--cases`, `--rescore`), scores and saves, with a 95% range per group |
| `compare.py` | Markdown table across runs, with ranges |

## How sure is a score?

Each score comes with a **95% range**: with 31 cases, 28 passing means "somewhere between 75% and 97%"; with all 147 cases the range is a few percentage points either way. Answers also vary between runs, so `--repeat 3` is the recommended setting for numbers you report. A difference between two models only counts if their ranges don't overlap much.

## Keeping training data separate

The test set's customers are listed in `cases_generated.json` (`customers`) plus the ones in `cases.json`. **Training data must use other customers and other question wording**, or a fine-tuned model can score well by memorising instead of learning.

Tests for the scoring: `tests/test_coach_eval.py`.

## Adding a case

Add an object to `cases.json` with a unique `id`, a `group`, `lang`, a demo `customer_id`, the `question` and the `must` rules. Compute expected numbers with the tools for 2026-09-10, not by hand. Run the tests, then the case with `--only`.
