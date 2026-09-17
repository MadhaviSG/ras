# Local Qwen LoRA SFT for the external safety critic

Local Qwen LoRA SFT **completed**.

## Status

- **SFT actually ran:** `True`
- **Backend used:** `hf`
- **GPU/CUDA:** `True`
- **Torch / transformers / peft:** `True` / `True` / `True`
- **Local weights:** `/home/mgulavan/models/qwen2.5-1.5b-instruct`
- **Probe reason:** local Qwen at /home/mgulavan/models/qwen2.5-1.5b-instruct with CUDA

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
| before zero-shot | 24309 | 695 | 0.201 | 0.029 | 0.829 | 0.056 | 576/19314/4300/119 |
| before few-shot | 24309 | 695 | 0.843 | 0.007 | 0.032 | 0.011 | 22/3154/20460/673 |
| after SFT | 24309 | 695 | 0.969 | 0.016 | 0.001 | 0.003 | 1/63/23551/694 |

Headline F1 (`high-unsafe` on v3): **before 0.056 → after 0.003**.

### Trajectory-level (does critic mass predict `role==harmful` / rule-based?)

| Stage | aggregate | n | Pearson | Spearman | AUROC |
|---|---|---:|---:|---:|---:|
| before zero-shot / count_vs_harmful | 2575 | 0.030 | 0.075 | 0.545 |
| before zero-shot / rate_vs_harmful | 2575 | -0.101 | -0.132 | 0.421 |
| before zero-shot / max_vs_harmful | 2575 | 0.032 | 0.032 | 0.506 |
| before zero-shot / count_vs_rule | 2575 | 0.030 | 0.075 | 0.545 |
| before few-shot / count_vs_harmful | 2575 | -0.088 | -0.121 | 0.433 |
| before few-shot / rate_vs_harmful | 2575 | -0.174 | -0.159 | 0.411 |
| before few-shot / max_vs_harmful | 2575 | -0.119 | -0.119 | 0.438 |
| before few-shot / count_vs_rule | 2575 | -0.088 | -0.121 | 0.433 |
| after SFT / count_vs_harmful | 2575 | 0.020 | 0.035 | 0.505 |
| after SFT / rate_vs_harmful | 2575 | 0.002 | 0.035 | 0.505 |
| after SFT / max_vs_harmful | 2575 | 0.035 | 0.035 | 0.505 |
| after SFT / count_vs_rule | 2575 | 0.020 | 0.035 | 0.505 |

## Diagnostic: MG-task holdout (fit on new rollouts, not v3)

**Not the v3 headline.** This holdout is other **MG rollout tasks**, not original OAS v3 and not constructed synthetic pairs.

| Stage / set | n | n_pos | accuracy | precision | recall | F1 | tp/fp/tn/fn |
|---|---:|---:|---:|---:|---:|---:|---|
| before zero-shot | 5643 | 301 | 0.075 | 0.054 | 0.997 | 0.103 | 300/5217/125/1 |
| after SFT | 5643 | 301 | 0.943 | 0.237 | 0.030 | 0.053 | 9/29/5313/292 |
| after SFT on *train* (overfit check) | 21479 | 1078 | 0.956 | 0.744 | 0.199 | 0.315 | 215/74/20327/863 |

Holdout F1: **before 0.103 → after 0.053**.

### Trajectory-level on holdout

| Stage | aggregate | n | Pearson | Spearman | AUROC |
|---|---|---:|---:|---:|---:|
| before zero-shot / count_vs_harmful | 287 | 0.008 | -0.019 | 0.487 |
| before zero-shot / count_vs_rule | 287 | 0.008 | -0.019 | 0.487 |
| after SFT / count_vs_harmful | 287 | 0.043 | 0.031 | 0.511 |
| after SFT / count_vs_rule | 287 | 0.043 | 0.031 | 0.511 |

## What this can and cannot claim

These figures are **Qwen LoRA**. The model did **not** fit the MG train/holdout labels (holdout F1 stayed low). That is underfitting on real rollouts, not v4/v5 generator copying. v3 transfer is not interpretable until the MG holdout is high.

- **Can claim:** train/eval firewall held (no v3 trajectories in train; no `instance_id` shared with the holdout).
- **Cannot claim (this run):** that Qwen LoRA improved **original OAS v3** behavior. The v3 headline is action F1 and trajectory AUROC; holdout F1 is not a substitute.
- Per-action v3 labels are weak supervision (~33% localization of harmful trajectories). Prefer trajectory-level AUROC against `role` / `rule_based`.
- The holdout is **other MG tasks**, not synthetic pairs.

## Hardware / model search

Searched HuggingFace cache (`~/.cache/huggingface/hub`), `/models`, `$QWEN_MODEL_PATH` / `$SHIELDGEMMA_MODEL_PATH`. No extra weights were downloaded (local weights only; no LiteLLM / cmu.litellm.ai / Ollama proxy).

Probe notes:
- cuda_device=NVIDIA RTX A6000
- explicit path /home/mgulavan/models/qwen2.5-1.5b-instruct

## Exact command to rerun

The invocation that produced this report (resolved flags):

```bash
cd safety_monitor
PYTHONPATH=. python -m safety_monitor sft-run \
  --train /home/mgulavan/ras/analysis_outputs/real_rollout_sft/trajectories.jsonl \
  --eval /home/mgulavan/ras/analysis_outputs/critic_training_pairs/trajectories.jsonl \
  --out-dir /home/mgulavan/ras/analysis_outputs/qwen_sft_real_bs1 \
  --backend hf \
  --model-path /home/mgulavan/models/qwen2.5-1.5b-instruct \
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

