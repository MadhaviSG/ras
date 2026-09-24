# Two annotators on the same 70 trajectories

## The question

The Sonnet credit labels failed the SFT gate. That failure has two possible
explanations: the labels are unusable, or one particular model is bad at this.
A second, independent annotator separates them. If two frontier models given
the same trajectories and the same prompt disagree about which actions caused
the outcome, then no single annotator's labels are a training signal.

## Setup

Both annotators saw the identical prompt: task id, instruction, the task-level
grader verdict, and each step's tool, arguments, and summary. Neither saw
observations, sink tags, the sink heuristic, or the other annotator's labels.

- Annotator A: `litellm_proxy/us.anthropic.claude-sonnet-5` (`../sonnet5/`)
- Annotator B: `litellm_proxy/gemini/gemini-2.5-pro` (`../gemini_pro/`)
- 70 trajectories, 808 steps, 35 unsafe and 35 safe
- Keys reused exactly from `../sonnet5/proposed_labels.jsonl` via
  `--keys-from`, verified identical in set and order

## Agreement

| Metric | `contributed` | `proposed_high` |
| --- | --- | --- |
| Raw agreement | 0.615 | 0.843 |
| Cohen's kappa | 0.279 | 0.429 |
| Jaccard on positives | 0.437 | 0.349 |
| Both marked | 241 | 68 |
| Only Sonnet | 261 | 93 |
| Only Gemini | 50 | 34 |

Within-trajectory credit rank: mean Spearman 0.710 across 61 trajectories
(9 were too short or constant to rank).

Raw agreement is the misleading number here, which is why kappa is reported
beside it: on `proposed_high` the two models agree on 84% of steps mostly by
jointly staying silent on 613 of them.

## Reading

The two annotators agree on ordering and disagree on the threshold. A mean
rank correlation of 0.710 says they largely concur about which actions in a
run mattered more than others. A kappa of 0.279 on the binary `contributed`
flag says they do not concur about where the line falls: Sonnet marks 502
actions as contributing, Gemini marks 291, and only 241 are marked by both.

So the binary per-action label is the unreliable part, not the notion of
credit itself. That is a more specific result than "the annotators disagree,"
and it points at relative credit as the part worth trying to use.

## Consensus gate

`consensus_labels.jsonl` keeps only actions both annotators marked, averaging
their credit. Strict AND, so a disagreement never becomes a positive label.

The gate is **closed**:

- Condition 1 passes. The consensus is not a copy of the sink oracle
  (fp=33, fn=52, F1=0.452) and is non-degenerate (68 positive, 740 negative).
- Condition 2 fails. Action-level AUROC is 0.420 against an out-of-fold
  task-identity probe at 0.576. The action signal is below a probe that never
  sees any action.

This is the third refusal, and the first on a label set built from two
annotators. Sonnet alone scored 0.598 against a 0.576 probe, a lead too small
to survive resampling. Intersecting with Gemini removed more signal than
noise.

## What this does not show

Agreement is a precondition, not correctness: two models can agree and both be
wrong. And two annotators from two families is not a general claim about
frontier models on this task.

A separate finding limits these trajectories further. Two task evaluators were
found to return unsafe on an untouched container (see
`../../prefix_resample/single_action/README.md`). How many of the 70
trajectories here come from tasks with unsafe-by-default evaluators has not
been measured, and any such task contributes a constant outcome that no
annotator could have assigned correctly.

## Reproduce

```
python analysis_outputs/credit_assignment/run_gateway_pass.py \
  --config benchmarks/.llm_config/ai-gateway-gemini-pro.json \
  --out analysis_outputs/credit_assignment/gemini_pro \
  --keys-from analysis_outputs/credit_assignment/sonnet5/proposed_labels.jsonl

python analysis_outputs/credit_assignment/run_agreement_and_gate.py
```
