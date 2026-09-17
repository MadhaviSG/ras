# Real MG passive rollout SFT dataset

Converted from finished Claude / GPT / Gemini `output.jsonl` rows only.
Labels are environment-evaluator `test_result.final_score.result`
(1 = unsafe / harmful, 0 = safe / clean). Failed conversations and empty
evaluators are skipped. Per-action `high-unsafe` is weak localization:
sink actions on evaluator-unsafe trajectories (`evaluator_sink`).

Do not treat this as constructed synthetic pairs.

## Counts

| Model | Trajectories | Safe | Unsafe | Actions | high-unsafe | low-unsafe |
|---|---:|---:|---:|---:|---:|---:|
| Claude | 537 | 423 | 114 | 6877 | 306 | 6571 |
| GPT | 490 | 383 | 107 | 10461 | 582 | 9879 |
| Gemini | 277 | 214 | 63 | 9784 | 491 | 9293 |
| **All** | **1304** | **1020** | **284** | **27122** | **1379** | **25743** |

546 unique tasks. Files: `trajectories.jsonl`, `counts.json`.
