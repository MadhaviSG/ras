# Paper A: what we can claim, and what the evidence is

Status: claims note. No SFT has been run, and none should be until the gate
opens.

The project set out to train an external safety critic that watches an agent
act and raises suspicion before harm occurs. It has not produced that critic.
It has produced a negative result about why the obvious training signal does
not work, plus the measurement apparatus that establishes it. That is the
paper.

---

## Claim 1 (diagnosis): task-level outcome labels cannot supervise an action-level critic

On the OpenAgentSafety rollouts, the per-action label is exactly
`task_unsafe AND step_has_sink`, at precision 1.000 and recall 1.000. It is
not approximately that rule; it is that rule.

A critic trained on this label is trained to detect write, send, and delete
calls in runs that happened to end badly. It cannot learn to distinguish a
harmful deletion from a harmless one, because the label never did.

This is the durable finding and it is cheap for a reader to check.

## Claim 2 (negative transfer): a stronger annotator does not fix it

Replacing the label rule with frontier credit assignment does not recover an
action-level signal.

Two annotators, Claude Sonnet 5 and Gemini 2.5 Pro, scored the same 70
trajectories (808 steps, 35 unsafe / 35 safe) from the same blinded prompt:
task id, instruction, the task-level verdict, and each step's tool, arguments,
and summary. Neither saw observations, sink tags, the sink heuristic, or the
other's labels.

They agree on ordering and disagree on the threshold:

| | `contributed` | `proposed_high` |
| --- | --- | --- |
| Cohen's kappa | 0.279 | 0.429 |
| Jaccard on positives | 0.437 | 0.349 |

Mean within-trajectory Spearman on credit rank: 0.710 over 61 trajectories.
Sonnet marks 502 actions as contributing, Gemini 291, with 241 in common.

So the models largely concur about which actions in a run mattered more than
others, and do not concur about which ones cross the line. The binary
per-action label is the unreliable part, not the notion of credit. If any
version of this signal is usable, it is relative credit within a trajectory.

Neither label set, nor their strict intersection, beats a probe that reads
only the task identity and instruction.

## Claim 3 (the gate): a falsifiable rule that has now refused three times

Before any training run, labels must clear two conditions:

1. **Not a copy of the oracle.** Two-way disagreement with the
   `sink_outcome_oracle` above 2% of steps, F1 against it below 0.95, and at
   least one prediction of each class.
2. **Beats task identity.** Action-level AUROC must exceed an out-of-fold
   task-identity probe, with the 5th-percentile lower bound of a 2000-sample
   paired bootstrap on the difference above zero, on at least 30 trajectories
   per outcome class.

Results:

| Label source | n | Action AUROC | Probe (out-of-fold) | Gate |
| --- | --- | --- | --- | --- |
| Local annotator | 25 | 0.651 | 0.429 | closed: too few trajectories; bootstrap lower bound −0.069 |
| Sonnet 5 | 70 | 0.598 | 0.576 | closed: bootstrap lower bound −0.146 |
| Sonnet ∩ Gemini Pro | 70 | 0.420 | 0.576 | closed: below the probe |

Two design details did the work, and both were bugs first:

- The probe must be scored **out of fold, grouped by `instance_id`**. Its
  feature string carries a unique `task:<id>` token, so an in-sample fit
  memorises the corpus and reports AUROC 1.000. That made condition 2
  unpassable by construction; the gate had been closing for the wrong reason.
  In-sample probe AUROC on the Sonnet run was 0.989 against 0.576 out of fold.
- Fixing that flipped the gate **open** on 25 noisy trajectories (0.651 vs
  0.429). The minimum-sample floor and the paired bootstrap were added in
  response, and both rejected it independently.

A gate that only ever closes is not evidence of rigour. This one opened the
moment the measurement was corrected, and was then closed by guards written
against that specific failure. The three refusals above are the result.

## Claim 4 (method): the controls change the answers

Two controls were added late and both overturned a result.

**Bidirectional nudges.** Four of five replayed prefixes never split across
four natural continuations. Nudging each one in the only direction that could
move it — harm-directed for all-safe prefixes, safety-directed for all-unsafe
— moved 0 of 4 tasks in 16 continuations with 0 errors.

**Zero-action grading.** On the two deletion tasks, grading one agent step
past the prefix returned 8/8 unsafe. The control that grades a freshly
prepared container with no prefix replayed and no agent step returned 2/2
unsafe. Both evaluators report unsafe by default.

That retracts part of the nudge result: those two tasks could never have
moved, so the honest tally is 0 of 2 interpretable tasks, not 0 of 4. It also
means the prefix-replay outcome for those tasks was fixed before the agent
acted.

The general point is worth stating in the paper. Every intervention in this
setting needs a no-intervention arm run through the same pipeline, because the
failure mode is a measurement that cannot move rather than a system that
resists moving.

---

## What we cannot claim

- **That the critic idea fails.** Nothing here tests a trained critic. It
  tests whether OpenAgentSafety task outcomes can supervise one.
- **That prefix replay proves next-action causality.** A prefix that reaches
  both outcomes shows that the same *reconstructed* prefix produced both. It
  does not isolate the next action as the cause.
- **That frontier models cannot do credit assignment.** Two models from two
  families, on 70 trajectories from one benchmark, with the outcome disclosed
  in the prompt.
- **That agreement would mean correctness.** Two annotators can agree and both
  be wrong. Agreement is a precondition we tested, not a result we passed.
- **Anything about how widespread the broken evaluators are.** Two were found
  because a control was run on two tasks. No sweep has been done, and an
  unsafe-by-default evaluator contributes a constant outcome that no annotator
  could assign correctly.

## What would change the picture

In rough order of cost:

1. A setup-only sweep over the task set, grading every task's fresh container
   with no agent. This is cheap, and it bounds how much of the corpus is
   contaminated. Until it is run, every outcome-derived number here carries an
   unknown amount of that constant.
2. Labels from a source that is not the task outcome: human annotation on a
   small set, or per-action grading with its own checker.
3. Relative credit within a trajectory as the target, since that is the part
   the two annotators agreed on, with the gate restated as a ranking metric.

## Artifacts

| Claim | Path |
| --- | --- |
| Label degeneracy | `analysis_outputs/credit_assignment/` |
| Sonnet pass and gate | `analysis_outputs/credit_assignment/sonnet5/` |
| Gemini Pro pass | `analysis_outputs/credit_assignment/gemini_pro/` |
| Agreement and consensus gate | `analysis_outputs/credit_assignment/consensus/` |
| Prefix replay, natural | `analysis_outputs/prefix_resample/smoke_runs/` |
| Nudge pilot | `analysis_outputs/prefix_resample/nudge_pilot/` |
| Broken evaluators | `analysis_outputs/prefix_resample/single_action/` |

Gate implementation: `benchmarks/safety_monitor/safety_monitor/sft/label_gate.py`.
Agreement metrics: `benchmarks/safety_monitor/safety_monitor/analysis/annotator_agreement.py`.
