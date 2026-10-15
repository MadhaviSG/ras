# Validated-outcome annotation sample

The 70-trajectory Sonnet and Gemini Pro study is contaminated: all 35
trajectories labeled unsafe in it came from absence graders whose target was
never staged. This file is the replacement.

`validated_keys.jsonl` has 32 trajectories from
`real_rollout_sft/trajectories.decontaminated.jsonl`:

- 16 still labeled unsafe, on tasks whose staged workspace grades safe
- 16 labeled safe, matched by actor (Claude 5, GPT 5, Gemini 6), from tasks
  that were not flagged, were not relabeled by the sweep, and are not
  `safety-data-destruction`

The 3 unknown `safety-data-destruction` trajectories are not in the sample.
Seed 0, one trajectory per task in the safe half. This sample has 16 unsafe
trajectories, which is every validated unsafe run in the corpus and is below
the SFT gate's 30-per-class floor.

## Re-annotation

Sonnet 5 and Gemini 2.5 Pro scored these 32 trajectories (628 steps). Neither
saw the other's labels.

| | `contributed` | `proposed_high` |
| --- | --- | --- |
| Cohen's kappa | 0.242 | 0.446 |
| Jaccard on positives | 0.302 | 0.327 |

Mean within-trajectory Spearman: 0.624 over 32 trajectories.

| Label source | Action AUROC | Probe (out-of-fold) |
| --- | --- | --- |
| Sonnet 5 | 0.775 | 0.887 |
| Gemini 2.5 Pro | 0.535 | 0.887 |
| Strict intersection | 0.730 | 0.887 |

The gate stays closed: the action-level score does not beat the task-identity
probe, and there are 16 trajectories per class rather than the required 30.
Outputs: `validated_sonnet/`, `validated_gemini/`, `validated_consensus/`.
