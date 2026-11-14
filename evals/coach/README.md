# Coach test set

Measures the whole coach, not just its Finnish: right tools and numbers, declining what [POLICY.md](../../POLICY.md) says to decline, **not** declining awkward-but-allowed questions, pointing to help, advice limits, no internal names, and Finnish quality (via `evals/finnish`). Used to compare models and to prove fine-tuning helped ([FINE_TUNING.md](../../FINE_TUNING.md)).

**These are test questions: never use them, or answers to them, as training data.**

## Run it

```bash
# Gemma on Verda, guardrail on
COACH_TODAY=2026-09-10 COACH_MODEL=gemma .venv/bin/python -m evals.coach.run

# Guardrail off, to measure its effect
COACH_TODAY=2026-09-10 COACH_MODEL=gemma COACH_GUARDRAIL=0 .venv/bin/python -m evals.coach.run

# Claude Opus 5.5 (needs ANTHROPIC_API_KEY in .env; about $2-3 of credits)
COACH_TODAY=2026-09-10 COACH_MODEL=claude .venv/bin/python -m evals.coach.run

# Name a run, or run some cases only
.venv/bin/python -m evals.coach.run --name gemma-finetuned --only budget-fi-1 drugs-fi-1

# Score a saved run again after changing the checks (no model needed)
.venv/bin/python -m evals.coach.run --rescore evals/coach/results/<run>

# Side-by-side table of all runs (or chosen folders)
.venv/bin/python -m evals.coach.compare
```

`COACH_TODAY=2026-09-10` is required: the expected numbers in `cases.json` are for that date. Each run writes `results/<time>-<name>/` (not in git): `answers.jsonl` (every answer, tools, timing, checks and the full conversation) and `summary.json`.

## Files

| File | What |
|---|---|
| `cases.json` | 31 test cases in seven groups, Finnish and English: `correct`, `overrefusal`, `refuse`, `care`, `advice`, `chat` |
| `score.py` | The rules, plain code: `tools_any`, `numbers` (either number format), `mention_any`, `refused`, `care`, `not_refused`, plus leak and Finnish checks on every case |
| `run.py` | Runs the cases on the current `COACH_MODEL`, scores and saves |
| `compare.py` | Markdown table across runs |

Tests for the scoring: `tests/test_coach_eval.py`.

## Adding a case

Add an object to `cases.json` with a unique `id`, a `group`, `lang`, a demo `customer_id`, the `question` and the `must` rules. Compute expected numbers with the tools for 2026-09-10, not by hand. Run the tests, then the case with `--only`.
