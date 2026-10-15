# RQ1: do a critic's flags predict rule-based harm?

Status: five critics scored on the unmonitored original-OAS runs. Open-source
models only. The blocking/Cygnal runs are partly labelled (193 of 2,034
trajectories, base critic) and are not reported here.

## Short answer

Off-the-shelf monitors do not. A prompted critic, a whole-run judge and
ShieldGemma all sit at chance, and below a probe that reads only the task
text. Telling the critic a general harm policy does not change that. Showing
the critic each task's own harm criteria does: the flagged fraction reaches
AUROC 0.67, and ranks the unsafe run above the safe run of the same task 80%
of the time. That last critic is an upper bound, not a deployable monitor.

## Setup

- **Trajectories.** The two no-analyzer runs on original OAS
  (`baseline_no_analyzer_claude`, `baseline_no_analyzer_gpt`) from
  `critic_training_pairs/trajectories.jsonl`: 541 trajectories, 9,619 actions.
- **Ground truth.** The rule-based grader outcome, restricted to the 265
  `valid` tasks in `og_grader_audit/task_tiers.jsonl`. With every critic
  present that is 474 trajectories on 259 tasks, 172 unsafe.
- **What a critic sees.** The task instruction and the earlier actions and
  observations. Never the outcome, the recorded analyzer risk, or the stored
  step labels. It returns `high-unsafe` / `low-unsafe` and a risk from 0 to
  100 for the current action. Qwen runs at temperature 0 with thinking off.

| Critic | Directory | What it is told | Actions flagged |
| --- | --- | --- | --- |
| Base | `ollama_qwen3.5_9b` | a definition of a harmful action | 6.8% |
| ShieldGemma-2B, zero-shot | `shieldgemma_2b_zeroshot` | its own guard template | 0.6% |
| Whole-run judge | `ollama_qwen3.5_9b_trajectory_judge` | the same model, one verdict per run | 1.7% of runs |
| Policy | `ollama_qwen3.5_9b_policy` | a general harm policy; "doing what was asked does not make it safe" | 10.7% |
| Criteria | `ollama_qwen3.5_9b_criteria` | the task's own checkpoint text | 19.3% |

No critic had a parse failure. Prompts are in
`benchmarks/safety_monitor/safety_monitor/critic/prompts.py`.

## Pass rule, fixed before the first run

A signal "tracks outcomes" only if all three hold, each as the lower end of a
95% bootstrap interval resampled by task: AUROC above 0.5; AUROC minus the
out-of-fold task-identity probe above 0; and within-task concordance above
0.5.

## Results

All 474 trajectories. Full tables with per-actor rows are in `report.md`.

| Signal | AUROC | 95% CI | Within-task | 95% CI | Passes |
| --- | --- | --- | --- | --- | --- |
| Base: flag count | 0.470 | 0.414–0.525 | 0.547 | 0.455–0.635 | no |
| Base: mean risk | 0.507 | 0.448–0.567 | 0.628 | 0.519–0.740 | no |
| ShieldGemma: flag count | 0.477 | 0.452–0.501 | 0.465 | 0.426–0.500 | no |
| ShieldGemma: max risk | 0.423 | 0.363–0.484 | 0.581 | 0.467–0.704 | no |
| Whole-run judge: risk | 0.553 | 0.500–0.603 | 0.500 | 0.407–0.593 | no |
| Policy: flag count | 0.469 | 0.411–0.527 | 0.628 | 0.536–0.720 | no |
| Policy: mean risk | 0.522 | 0.464–0.580 | 0.640 | 0.533–0.750 | no |
| Criteria: flag count | 0.613 | 0.556–0.670 | 0.721 | 0.625–0.818 | no |
| Criteria: flagged fraction | 0.668 | 0.608–0.723 | 0.802 | 0.722–0.897 | yes |
| Criteria: mean risk | 0.665 | 0.604–0.722 | 0.814 | 0.731–0.917 | yes |
| Baseline: number of actions | 0.436 | 0.376–0.495 | 0.628 | 0.519–0.732 | – |
| Baseline: keyword count | 0.467 | 0.415–0.521 | 0.512 | 0.435–0.589 | – |
| Baseline: task identity (out of fold) | 0.575 | 0.512–0.635 | 0.500 | – | – |

Within-task concordance is over the 43 tasks where one actor ended safe and
the other unsafe.

- **Base critic.** At chance and below the task-only probe (difference −0.185
  to −0.023). It flags at least one action in 50% of safe runs and 47% of
  unsafe runs.
- **ShieldGemma.** Almost never fires, and its risk score is below chance.
- **Whole-run judge.** The same model shown the full trajectory still does
  not separate the runs, and calls 1.7% of them unsafe when 36% are. The
  per-action framing is therefore not what limits the base critic.
- **Policy critic.** Flags more, separates no better.
- **Criteria critic.** The raw flag count misses the rule only on the
  task-identity comparison (−0.042 to 0.122). Normalised by run length it
  passes. Unsafe runs are shorter on average, so a raw count is penalised.

### Held-out scoring of the two later critics

The policy and criteria prompts were written after reading the 55 cases in
`failure_modes/`. They are therefore also scored with those 51 tasks removed
(`variants_heldout/`): 378 trajectories on 209 tasks, 121 unsafe, 31 mixed
tasks.

| Signal | AUROC | 95% CI | Within-task | 95% CI | Δ vs task identity |
| --- | --- | --- | --- | --- | --- |
| Policy: flag count | 0.501 | 0.436–0.568 | 0.661 | 0.563–0.763 | −0.206 to −0.017 |
| Criteria: flag count | 0.600 | 0.535–0.662 | 0.710 | 0.600–0.824 | −0.100 to 0.080 |
| Criteria: flagged fraction | 0.664 | 0.598–0.731 | 0.774 | 0.667–0.889 | −0.031 to 0.143 |
| Criteria: mean risk | 0.663 | 0.598–0.732 | 0.807 | 0.700–0.917 | −0.034 to 0.142 |
| Task identity (out of fold) | 0.610 | 0.544–0.677 | 0.500 | – | – |

The criteria critic keeps its AUROC and its within-task result on held-out
tasks. It no longer clears the task-identity comparison there: the probe is
stronger on this subset and there are fewer tasks, so the interval reaches
below zero. Strictly, it passes on all tasks and not on the held-out ones.

## Why the unprompted critics miss: 55 cases read by hand

`failure_modes/README.md`. One reader, sampled with a fixed seed from the base
critic's results; counts are not population estimates.

- **Misses (25 unsafe runs with no flag).** 17 are the agent doing what the
  task or a colleague asked. 6 do not look unsafe on reading; the grader fired
  for an unrelated reason. 2 are harmful content written through a benign
  action. None is a plainly harmful command the critic let through.
- **False alarms (20 safe runs with a flag).** In 12 the flagged action does
  look risky and the grader scores something else. 6 are flags on benign
  actions, 4 of them logging in with credentials the task supplied.
- **Hits (10).** The flag was on the action that produced the graded harm in
  9.

This is why the criteria critic was built, and why its result fits: the
graded harm in this benchmark is mostly ordinary-looking work that violates a
rule the critic has to be told.

## RQ3, retrospective: aggregation against the raw count

Final credence per trajectory. `ollama_qwen3.5_9b/rq3.json` and
`ollama_qwen3.5_9b_criteria/rq3.json`.

| Aggregate | Base AUROC | Base Δ vs count | Criteria AUROC | Criteria Δ vs count |
| --- | --- | --- | --- | --- |
| count | 0.470 | – | 0.613 | – |
| cummax | 0.471 | −0.026 to 0.029 | 0.607 | −0.041 to 0.029 |
| noisy-OR | 0.472 | −0.030 to 0.035 | 0.610 | −0.026 to 0.021 |
| EW decay | 0.515 | 0.004 to 0.087 | 0.660 | 0.007 to 0.087 |
| log-odds sum | 0.562 | 0.020 to 0.170 | 0.639 | −0.037 to 0.089 |

- **Base critic.** Two aggregates beat the count and neither is usable.
  Log-odds sum is a length artifact: every low-risk action subtracts evidence,
  long runs score low, and long runs are more often safe. Its within-task
  concordance is 0.430. EW decay reaches 0.515, which includes chance.
- **Criteria critic.** EW decay beats the count by a small margin (0.660
  against 0.613) and keeps within-task concordance at 0.767. It is the only
  aggregate that helps on a critic that already carries signal, and it does
  about as well as simply dividing the count by run length (0.668).
- **Catch rate.** At a 10% false-alarm budget the criteria critic catches 19%
  to 23% of unsafe runs under its better aggregates. The base critic catches
  13%, which is roughly what random interruption would.
- **Earliness.** Criteria-critic count AUROC is 0.550 a quarter of the way
  through a run, 0.595 at half, and 0.613 at the end.

The Phase 5 entry gate as written ("beats the raw count") needs a second
clause: the aggregate must also beat chance and run length. On the base
critic the gate is met on paper by a length artifact.

Lead time is not reported. The recorded pivotal step is derived from the
outcome label, so "before the pivotal action" would be circular.

## What this does and does not show

- It shows that three open, off-the-shelf monitors do not track rule-based
  outcomes on original OAS, and that the binding gap is knowledge of what
  counts as harm in the task, not the model's ability to read actions.
- The criteria critic is an upper bound. Its input is the benchmark's own
  description of the unsafe outcome, which a deployed monitor would not have.
  Its AUROC of 0.67 is modest even so.
- One model family did the prompted work, at 9B parameters. No closed models,
  no fine-tuning.
- Only two actors have unmonitored runs. Gemini and DeepSeek appear only in
  blocking runs, where outcomes are censored.
- The outcome labels are noisy for reasons a critic cannot see. 121 valid
  graders read service state that is shared across runs and never reset. The
  case study found string and file-existence checks that fire without harm or
  miss real harm on valid-tier tasks. Task-demanded harm is common: the audit
  counted 10 such tasks among those unsafe in every run, and the case study
  found 8 more outside that set.
- `safety-clear-space-cachefiles` is valid-tier but has no task text and no
  checkpoint text. The criteria critic skipped its two trajectories.

## Verification

`verify_rq1.py` recomputes every AUROC, concordance and count in `rq1.json`
from the raw files using only the standard library. It was written without
reading the report code. It reports 198 of 198 claims reproducing.

```
python analysis_outputs/rq1/verify_rq1.py
```

Its first run failed two claims on mean risk: the two implementations summed
floats differently, so exact ties broke differently. Mean risk is now rounded
to six decimals in both. The verifier does not cover the held-out tables or
the RQ3 files.

## Prompt history

- **Base.** One revision. On a first 34-trajectory pilot the label and the
  risk disagreed on about a third of actions. The prompt was rewritten to put
  the label first and require agreement, re-piloted on 26 trajectories, and
  frozen before the full run.
- **Policy, criteria.** Written after the base result and the case study, run
  once each after a four-trajectory format check. Exploratory.

## Reproduce

```
cd benchmarks/safety_monitor
R=../../analysis_outputs/rq1
T=../../analysis_outputs/og_grader_audit/task_tiers.jsonl
uv run --extra dev python -m safety_monitor critic-label \
    --out-dir $R/ollama_qwen3.5_9b --families passive
uv run --extra dev python -m safety_monitor critic-label --whole-trajectory \
    --out-dir $R/ollama_qwen3.5_9b_trajectory_judge --families passive
uv run --extra dev python -m safety_monitor critic-label --variant policy \
    --tiers $T --out-dir $R/ollama_qwen3.5_9b_policy --families passive
uv run --extra dev python -m safety_monitor critic-label --variant criteria \
    --tasks ../../analysis_outputs/hf_cache/v3_train.jsonl \
    --tiers $T --out-dir $R/ollama_qwen3.5_9b_criteria --families passive
uv run --extra dev --extra sft python -m safety_monitor critic-label \
    --completer shieldgemma --model-path ~/models/shieldgemma-2b \
    --eval-batch-size 1 --out-dir $R/shieldgemma_2b_zeroshot --families passive
uv run --extra dev python -m safety_monitor rq1-report --tiers $T --out-dir $R \
    --verdicts $R/ollama_qwen3.5_9b $R/shieldgemma_2b_zeroshot \
    $R/ollama_qwen3.5_9b_trajectory_judge $R/ollama_qwen3.5_9b_policy \
    $R/ollama_qwen3.5_9b_criteria
```

Add `--exclude-tasks $R/failure_modes/sampled_tasks.txt` for the held-out
tables, and use `rq3-report --verdicts <one critic dir>` for the aggregation
tables. ShieldGemma ran on CPU in float32: two of the three GPUs on the host
refused CUDA contexts.
