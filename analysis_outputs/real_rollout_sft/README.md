# Real MG passive rollout SFT dataset

Converted from finished Claude / GPT / Gemini `output.jsonl` rows only.
Labels are environment-evaluator `test_result.final_score.result`
(1 = unsafe / harmful, 0 = safe / clean). Failed conversations and empty
evaluators are skipped. Per-action `high-unsafe` is weak localization:
sink actions on evaluator-unsafe trajectories (`evaluator_sink`).

Do not treat this as constructed synthetic pairs.

## Counts

`counts.json` is the pre-decontamination file. Use `counts.decontaminated.json`
and `trajectories.decontaminated.jsonl` for every new count, comparison, or
training decision. Three `safety-data-destruction` trajectories are
`outcome_status` `unknown` and are in neither column below.

| Model | Trajectories | Safe | Unsafe | Actions | high-unsafe | low-unsafe | Unsafe rate |
|---|---:|---:|---:|---:|---:|---:|---:|
| Claude | 536 | 531 | 5 | 6859 | 29 | 6830 | 0.9% |
| GPT | 489 | 484 | 5 | 10437 | 32 | 10405 | 1.0% |
| Gemini | 276 | 270 | 6 | 9765 | 17 | 9748 | 2.2% |
| **Labeled** | **1301** | **1285** | **16** | **27061** | **78** | **26983** | **1.2%** |
| Unknown | 3 |  |  |  |  |  |  |

545 labeled tasks. The historical table, from `trajectories.jsonl` before this
correction, was 1304 trajectories and 284 unsafe.

On tasks that were not flagged and are not unknown, the unsafe rate is Claude
1.2% (5/428), GPT 1.3% (5/388), Gemini 2.7% (6/220).

## Decontamination

`trajectories.jsonl` is unchanged. `trajectories.decontaminated.jsonl` relabels
265 trajectories whose unsafe label came from a grader that fires because its
target file was never staged, and whose recorded actions never named that
file. It also marks the 3 `safety-data-destruction` trajectories unknown.
Sixteen unsafe labels remain, all on graders that start safe. The pre-change
copy is `../grader_contamination/backup/trajectories.jsonl`. See
`../grader_contamination/README.md`.

SFT and credit assignment refuse `real_rollout_sft/trajectories.jsonl`. Pass
`trajectories.decontaminated.jsonl`.
