# Test results: Gemma 4 vs Claude Opus 5.5

Results of the coach test set ([evals/coach](evals/coach/README.md)) and a blind Finnish review by a native speaker, 14 Nov 2026. How the cases are scored and what each group means: [evals/coach/README.md](evals/coach/README.md) and [POLICY.md](POLICY.md).

## Setup

| | Gemma 4 | Claude Opus 5.5 |
|---|---|---|
| Model | `google/gemma-4-31B-it`, FP8, 1× H100 on Verda | `claude-opus-5-5`, Anthropic API |
| Runs | every case 3 times (441 answers) | every case once (147 answers) |
| Result folder | `evals/coach/results/20261114-1819-gemma-guardrail-x3/` | `evals/coach/results/20261114-1829-claude-opus/` |

Both runs: all 147 cases (31 hand-written, 116 generated), guardrail on, demo date `COACH_TODAY=2026-09-10`. Result folders are not in git.

## Automatic tests

Scored with the Finnish rules as of 14 Nov 2026 evening, including the native reviewer's corrections. Each score has a 95% range; a difference counts only when the ranges barely overlap.

| | Gemma 4 | Opus 5.5 |
|---|---|---|
| Correct numbers and tools | 158/225 (64–76 %) | 56/75 (64–83 %) |
| Answers awkward-but-allowed questions | 39/66 (47–70 %) | 14/22 (43–80 %) |
| Declines harmful / off-topic | 60/60 (94–100 %) | 20/20 (84–100 %) |
| Points to help when needed | 33/33 (90–100 %) | 11/11 (74–100 %) |
| Investment/loan/tax: general only | 32/33 (85–99 %) | 9/11 (52–95 %) |
| Small talk | 17/24 (51–85 %) | 6/8 (41–93 %) |
| **All cases** | **339/441 (73–81 %)** | **116/147 (72–85 %)** |
| Leaked internal names | 0 | 0 |
| Median time to first words | 1.4 s | 8.6 s |

Most failures come from one new rule: the reviewer said the three groups are *kulutuskategoriat*, not *korit*, and both runs predate that change, so nearly every Finnish answer said "-koriin".

| All cases | Gemma 4 | Opus 5.5 |
|---|---|---|
| With the rules before the review | 427/441 (97 %) | 137/147 (93 %) |
| With the new rules, "kori" not counted | 421/441 (95 %) | 134/147 (91 %) |
| With all new rules | 339/441 (77 %) | 116/147 (79 %) |

What remains after "kori": Gemma mostly English words or odd word choices in Finnish (cinema, Lifestyle, salary sweep); Opus mostly capitals mid-sentence, partly false alarms after a date ("15.9. Ennen …").

The time row is not comparable: the coach streams Gemma's answer word by word but receives Claude's answer in one piece.

## Blind Finnish review

A native speaker rated answers to the same Finnish questions without knowing which model wrote which (`evals/coach/blind.py`).

**Scores** (1–5, 4 questions rated of 30):

| | Finnish | Bank language | Chosen as best |
|---|---|---|---|
| Gemma 4 | 4.00 | 4.00 | 1 |
| Opus 5.5 | 4.50 | 4.75 | 2 |

**Sentences marked wrong** (8 suspicious sentences reviewed one at a time):

| | Wrong sentences |
|---|---|
| Gemma 4 | 6: a garbled idiom ("arki heittää kumppanista"), "menit" for "kulutit", "kuukauden väliset menot", an English heading, "ostoskori", "käytät viihdettä (Entertainment)" |
| Opus 5.5 | 3: "lähimmäs pääsee nämä", "helpoimmin … kuin", "suurin osa oli kaksi lääkärikäyntiä" |

Not counted against either model: "-koriin", which both used.

**Limits:** 4 rated questions are too few to rank the models; treat the scores as a hint. Claude (Opus) chose the 8 sentences, which may favour Opus; the scores were given before that and don't have this problem.

**Reviewer's preferences:** shorter answers (chosen in 3 of 4 questions), no dashes between clauses, no quote marks, no English words, and *kategoria* instead of *kori*. All are now coach instructions and Finnish checks (`evals/finnish/bad_phrases.py`).

## Conclusion

- **Safety:** equal. Both declined every harmful question and pointed to help every time.
- **Correctness:** Gemma slightly ahead, but within the ranges.
- **Finnish:** Opus slightly better in the blind review; Gemma's mistakes (English words, odd idioms, wrong verbs) are the kind fine-tuning fixes well ([FINE_TUNING.md](FINE_TUNING.md)).
- **Speed and cost:** Gemma answers first words in about 1.4 s and runs on our own GPU.

## After the review

The coach's instructions now ask for *kategoria*, short answers and Finnish-only headings. A quick check on Gemma with 3 Finnish questions (`results/20261114-2043-gemma-kategoria-short/`): all three said "kategoria" and were short. New errors found there ("mihin … koostuu", a stray Thai character) are now checks. The full test set hasn't been rerun yet; do that after fine-tuning:

```
COACH_TODAY=2026-09-10 COACH_MODEL=gemma .venv/bin/python -m evals.coach.run --repeat 3 --name gemma-x3
.venv/bin/python -m evals.coach.compare evals/coach/results/<new run> evals/coach/results/20261114-1829-claude-opus
```
