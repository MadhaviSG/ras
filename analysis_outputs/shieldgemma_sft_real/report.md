# Local ShieldGemma LoRA SFT for the external safety critic

Local ShieldGemma LoRA SFT **completed**.

## Status

- **SFT actually ran:** `True`
- **Backend used:** `hf`
- **GPU/CUDA:** `True`
- **Torch / transformers / peft:** `True` / `True` / `True`
- **Local weights:** `/home/mgulavan/models/shieldgemma-2b`
- **Probe reason:** local ShieldGemma at /home/mgulavan/models/shieldgemma-2b with CUDA

## Train/eval firewall

Training uses **real MG passive rollouts** (Claude/GPT/Gemini), not constructed v4/v5/v6 pairs. Train JSONL: `/home/mgulavan/ras/analysis_outputs/real_rollout_sft/trajectories.jsonl`. Original OAS v3 runs (`analysis_outputs/critic_training_pairs`) are eval-only. The **MG-task holdout** is a **task-level** (`instance_id`) cut of the same MG file: no step from a holdout task is in train. High holdout F1 means the model fits the *new* rollout distribution. The headline is still **v3 AUROC**, not holdout F1.

- Train tasks: **424** (1017 trajectories)
- Holdout tasks: **122** (287 trajectories)
- V3 eval trajectories: **2575** across 300 tasks
- Split salt: `qwen-sft`, holdout fraction `0.2`
- Train∩holdout instance_ids: `[]`

## Example counts (one SFT row per labeled action)

| Split | Examples | high-unsafe | low-unsafe | tasks | trajectories |
|---|---:|---:|---:|---:|---:|
| train | 21479 | 1078 | 20401 | 424 | 1017 |
| synthetic_holdout | 5643 | 301 | 5342 | 122 | 287 |
| v3_eval | 24309 | 695 | 23614 | 300 | 2575 |

## Headline: v3 eval (weak per-action labels + trajectory GT)

Per-action labels on v3 are **weak supervision** (signature + sink + contrastive lift). Trajectory roles (`harmful` / `prevented` / `clean`) and `rule_based` come from the environment checkpoint and are the stronger ground truth. See `analysis_outputs/critic_training_pairs/report.md`.

### Action-level (positive class = `high-unsafe`)

| Stage / set | n | n_pos | accuracy | precision | recall | F1 | tp/fp/tn/fn |
|---|---:|---:|---:|---:|---:|---:|---|
| before zero-shot | 24309 | 695 | 0.965 | 0.066 | 0.016 | 0.026 | 11/155/23459/684 |
| before few-shot | 24309 | 695 | 0.965 | 0.066 | 0.016 | 0.026 | 11/155/23459/684 |
| after SFT | 24309 | 695 | 0.969 | 0.123 | 0.012 | 0.021 | 8/57/23557/687 |

Headline F1 (`high-unsafe` on v3): **before 0.026 → after 0.021**.

### Trajectory-level (does critic mass predict `role==harmful` / rule-based?)

| Stage | aggregate | n | Pearson | Spearman | AUROC |
|---|---|---:|---:|---:|---:|
| before zero-shot / count_vs_harmful | 2575 | -0.018 | -0.041 | 0.491 |
| before zero-shot / rate_vs_harmful | 2575 | -0.048 | -0.042 | 0.491 |
| before zero-shot / max_vs_harmful | 2575 | -0.041 | -0.041 | 0.491 |
| before zero-shot / count_vs_rule | 2575 | -0.018 | -0.041 | 0.491 |
| before few-shot / count_vs_harmful | 2575 | -0.018 | -0.041 | 0.491 |
| before few-shot / rate_vs_harmful | 2575 | -0.048 | -0.042 | 0.491 |
| before few-shot / max_vs_harmful | 2575 | -0.041 | -0.041 | 0.491 |
| before few-shot / count_vs_rule | 2575 | -0.018 | -0.041 | 0.491 |
| after SFT / count_vs_harmful | 2575 | 0.008 | 0.020 | 0.503 |
| after SFT / rate_vs_harmful | 2575 | -0.008 | 0.020 | 0.503 |
| after SFT / max_vs_harmful | 2575 | 0.020 | 0.020 | 0.503 |
| after SFT / count_vs_rule | 2575 | 0.008 | 0.020 | 0.503 |

## Diagnostic: MG-task holdout (fit on new rollouts, not v3)

**Not the v3 headline.** This holdout is other **MG rollout tasks**, not original OAS v3 and not constructed synthetic pairs. High F1 here means the critic fits the new-task distribution. Flat v3 with high MG holdout is **shift** (MG ≠ v3), not v4/v5 template copying.

| Stage / set | n | n_pos | accuracy | precision | recall | F1 | tp/fp/tn/fn |
|---|---:|---:|---:|---:|---:|---:|---|
| before zero-shot | 5643 | 301 | 0.945 | 0.176 | 0.010 | 0.019 | 3/14/5328/298 |
| after SFT | 5643 | 301 | 0.980 | 0.879 | 0.724 | 0.794 | 218/30/5312/83 |
| after SFT on *train* (overfit check) | 21479 | 1078 | 0.999 | 0.990 | 0.999 | 0.994 | 1077/11/20390/1 |

Holdout F1: **before 0.019 → after 0.794**.

### Trajectory-level on holdout

| Stage | aggregate | n | Pearson | Spearman | AUROC |
|---|---|---:|---:|---:|---:|
| before zero-shot / count_vs_harmful | 287 | -0.025 | -0.049 | 0.487 |
| before zero-shot / count_vs_rule | 287 | -0.025 | -0.049 | 0.487 |
| after SFT / count_vs_harmful | 287 | 0.318 | 0.813 | 0.911 |
| after SFT / count_vs_rule | 287 | 0.318 | 0.813 | 0.911 |

## What this can and cannot claim

These figures are **ShieldGemma LoRA**. MG-task holdout F1 is high while original OAS **v3 is flat**: the critic **fits the new MG rollout distribution** (and the task-level holdout of that same file) but does **not** transfer to messy v3 traces. That is **MG↔v3 shift**, not v4/v5 keyword / generator overfitting — this run never trained on constructed synthetic pairs.

- **Can claim:** train/eval firewall held (no v3 trajectories in train; no `instance_id` shared with the holdout).
- **Cannot claim (this run):** that ShieldGemma LoRA improved **original OAS v3** behavior, unless `sft_actually_ran` is true and the v3 headline (traj AUROC / action F1) moves.
- Per-action v3 labels are weak supervision (~33% localization of harmful trajectories). Prefer trajectory-level AUROC against `role` / `rule_based`.
- The holdout is **other MG tasks**, not synthetic pairs. High holdout F1 + flat v3 is MG↔v3 shift, not 'copied v4/v5 pivotal phrases'.

## Hardware / model search

Searched HuggingFace cache (`~/.cache/huggingface/hub`), `/models`, `$QWEN_MODEL_PATH` / `$SHIELDGEMMA_MODEL_PATH`. No extra weights were downloaded (local weights only; no LiteLLM / cmu.litellm.ai / Ollama proxy).

Probe notes:
- cuda_device=NVIDIA RTX A6000
- ShieldGemma at /home/mgulavan/models/shieldgemma-2b

## Exact command to rerun

The invocation that produced this report (resolved flags):

```bash
cd safety_monitor
PYTHONPATH=. python -m safety_monitor sft-run \
  --train /home/mgulavan/ras/analysis_outputs/real_rollout_sft/trajectories.jsonl \
  --eval /home/mgulavan/ras/analysis_outputs/critic_training_pairs/trajectories.jsonl \
  --out-dir /home/mgulavan/ras/analysis_outputs/shieldgemma_sft_real \
  --backend hf \
  --model-path /home/mgulavan/models/shieldgemma-2b \
  --family shieldgemma \
  --epochs 2 \
  --batch-size 1 \
  --grad-accum 8 \
  --eval-batch-size 1 \
  --holdout-fraction 0.2 \
  --strict
```

Install GPU extras with `pip install -e '.[sft]'` (pins `transformers>=4.44,<5` and `peft<0.16`). Optional: `--max-v3-trajectories 50` for a cheaper HF eval smoke. On 48GB A6000s, `--batch-size 8 --grad-accum 1` cuts training ~5× vs the default batch 1 / accum 8. Full v3 eval is ~2.5k trajectories / ~24k actions.

## Files

| File | Contents |
|---|---|
| `report.md` | this document |
| `metrics.json` | before/after action + trajectory metrics |
| `split.json` | task ids for train vs holdout |
| `probe.json` | GPU / weights / backend decision |
| `example_counts.json` | SFT row counts |
| `train_stats.json` | mock fit or LoRA trainer metrics |

