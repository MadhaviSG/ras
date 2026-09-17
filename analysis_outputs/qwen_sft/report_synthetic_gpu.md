# Archived: GPU Qwen LoRA on synthetic v4+v5 (not this folder's metrics.json)

**Do not treat this as the report for `analysis_outputs/qwen_sft/`.**
`metrics.json`, `probe.json`, `split.json`, and `example_counts.json` in this
folder are a later **mock** pipeline check (60 train tasks, `sft_actually_ran=false`).
This writeup is the only remaining copy of a GPU LoRA run on constructed
synthetic pairs (455 train tasks, holdout F1 = 1.0, v3 F1 0.045 → 0.108,
traj AUROC 0.515 → 0.435). There is no matching `metrics.json` beside it.

---

# Local Qwen SFT for the external safety critic

Local Qwen LoRA SFT **completed**.

## Status

- **SFT actually ran:** `True`
- **Backend used:** `hf`
- **GPU/CUDA:** `True`
- **Torch / transformers / peft:** `True` / `True` / `True`
- **Local Qwen path:** `/home/mgulavan/models/qwen2.5-1.5b-instruct`
- **Probe reason:** local Qwen at /home/mgulavan/models/qwen2.5-1.5b-instruct with CUDA

## Train/eval firewall

Training uses **synthetic v4 + v5** trajectories only. Real OAS v3 runs (`analysis_outputs/critic_training_pairs`) are eval-only. The synthetic holdout is a **task-level** (`instance_id`) cut: no step from a holdout task is in train. Holdout metrics are a leakage diagnostic ("can the model fit the generator?") and **must not** be treated as the headline number.

- Train tasks: **455** (910 trajectories)
- Synthetic holdout tasks: **73** (146 trajectories)
- V3 eval trajectories: **100** across 100 tasks
- Split salt: `v6-synthetic-500`, holdout fraction `0.0`
- Train∩holdout instance_ids: `[]`

## Example counts (one SFT row per labeled action)

| Split | Examples | high-unsafe | low-unsafe | tasks | trajectories |
|---|---:|---:|---:|---:|---:|
| train | 10952 | 455 | 10497 | 455 | 910 |
| synthetic_holdout | 1802 | 73 | 1729 | 73 | 146 |
| v3_eval | 1830 | 41 | 1789 | 100 | 100 |

## Headline: v3 eval (weak per-action labels + trajectory GT)

Per-action labels on v3 are **weak supervision** (signature + sink + contrastive lift). Trajectory roles (`harmful` / `prevented` / `clean`) and `rule_based` come from the environment checkpoint and are the stronger ground truth. See `analysis_outputs/critic_training_pairs/report.md`.

### Action-level (positive class = `high-unsafe`)

| Stage / set | n | n_pos | accuracy | precision | recall | F1 | tp/fp/tn/fn |
|---|---:|---:|---:|---:|---:|---:|---|
| before zero-shot | 1830 | 41 | 0.237 | 0.023 | 0.805 | 0.045 | 33/1389/400/8 |
| before few-shot | 1830 | 41 | 0.645 | 0.025 | 0.390 | 0.047 | 16/625/1164/25 |
| after SFT | 1830 | 41 | 0.928 | 0.075 | 0.195 | 0.108 | 8/99/1690/33 |

Headline F1 (`high-unsafe` on v3): **before 0.045 → after 0.108**.

### Trajectory-level (does critic mass predict `role==harmful` / rule-based?)

| Stage | aggregate | n | Pearson | Spearman | AUROC |
|---|---|---:|---:|---:|---:|
| before zero-shot / count_vs_harmful | 100 | -0.001 | 0.026 | 0.515 |
| before zero-shot / rate_vs_harmful | 100 | -0.127 | -0.064 | 0.463 |
| before zero-shot / max_vs_harmful | 100 | n/a | n/a | 0.500 |
| before zero-shot / count_vs_rule | 100 | -0.001 | 0.026 | 0.515 |
| before few-shot / count_vs_harmful | 100 | -0.055 | -0.103 | 0.440 |
| before few-shot / rate_vs_harmful | 100 | -0.260 | -0.261 | 0.348 |
| before few-shot / max_vs_harmful | 100 | -0.121 | -0.121 | 0.451 |
| before few-shot / count_vs_rule | 100 | -0.055 | -0.103 | 0.440 |
| after SFT / count_vs_harmful | 100 | -0.157 | -0.120 | 0.435 |
| after SFT / rate_vs_harmful | 100 | -0.138 | -0.111 | 0.439 |
| after SFT / max_vs_harmful | 100 | -0.113 | -0.113 | 0.443 |
| after SFT / count_vs_rule | 100 | -0.157 | -0.120 | 0.435 |

## Diagnostic only: synthetic holdout (can the model fit the generator?)

**Not the headline.** High holdout F1 with flat v3 transfer is the signature of fitting the synthetic generator (shared templates / pivotal-action phrasing), not of a general critic.

| Stage / set | n | n_pos | accuracy | precision | recall | F1 | tp/fp/tn/fn |
|---|---:|---:|---:|---:|---:|---:|---|
| before zero-shot | 1802 | 73 | 0.145 | 0.045 | 1.000 | 0.087 | 73/1541/188/0 |
| after SFT | 1802 | 73 | 1.000 | 1.000 | 1.000 | 1.000 | 73/0/1729/0 |
| after SFT on *train* (overfit check) | 10952 | 455 | 0.998 | 0.964 | 1.000 | 0.982 | 455/17/10480/0 |

Synthetic-holdout F1: **before 0.087 → after 1.000**.

### Trajectory-level on synthetic holdout

| Stage | aggregate | n | Pearson | Spearman | AUROC |
|---|---|---:|---:|---:|---:|
| before zero-shot / count_vs_harmful | 146 | 0.300 | 0.282 | 0.662 |
| before zero-shot / count_vs_rule | 146 | 0.300 | 0.282 | 0.662 |
| after SFT / count_vs_harmful | 146 | 1.000 | 1.000 | 1.000 |
| after SFT / count_vs_rule | 146 | 1.000 | 1.000 | 1.000 |

## What this can and cannot claim

These figures are **Qwen LoRA**. v3 action F1 moved up after the fit. Still treat per-action v3 labels as weak supervision and confirm the trajectory-level AUROC against `role==harmful` / rule-based score before claiming critic gains.

- **Can claim:** the conversion, task-level split, and metric code ran on the real corpora with a train/eval firewall (no v3 in train; no `instance_id` shared with the synthetic holdout).
- **Cannot claim (this run):** that a Qwen critic improved on real OAS behavior, unless `sft_actually_ran` is true and the v3 headline moves.
- Per-action v3 labels are weak supervision (~33% localization of harmful trajectories). A critic can be right about harm and still look wrong action-by-action. Prefer trajectory-level AUROC against `role` / `rule_based`.
- Synthetic pairs are *constructed*: one pivotal `high-unsafe` action per harmful half, byte-identical prefixes. Fitting that generator is easy; transferring to messy v3 traces is the actual question.

## Hardware / model search

Searched HuggingFace cache (`~/.cache/huggingface/hub`), `/models`, `$QWEN_MODEL_PATH`. No extra weights were downloaded (disk ~full; constraint: local Qwen only, no LiteLLM / cmu.litellm.ai / Ollama proxy).

Probe notes:
- cuda_device=NVIDIA RTX A6000
- explicit path /home/mgulavan/models/qwen2.5-1.5b-instruct

## Exact command to rerun

From the repo root, mock/smoke (this machine):

```bash
cd safety_monitor
PYTHONPATH=. .venv/bin/python -m safety_monitor sft-qwen \
  --train ../analysis_outputs/v4_synthetic_pairs/trajectories.jsonl \
         ../analysis_outputs/v5_synthetic_pairs/trajectories.jsonl \
  --eval ../analysis_outputs/critic_training_pairs/trajectories.jsonl \
  --out-dir ../analysis_outputs/qwen_sft \
  --backend mock
```

When a local Qwen Instruct checkpoint and a CUDA GPU are available (do **not** download a new 7B if disk is tight; point at an existing dir):

```bash
cd safety_monitor
python -m venv .venv && .venv/bin/pip install -e '.[sft]'
PYTHONPATH=. .venv/bin/python -m safety_monitor sft-qwen \
  --train ../analysis_outputs/v4_synthetic_pairs/trajectories.jsonl \
         ../analysis_outputs/v5_synthetic_pairs/trajectories.jsonl \
  --eval ../analysis_outputs/critic_training_pairs/trajectories.jsonl \
  --out-dir ../analysis_outputs/qwen_sft \
  --backend hf \
  --model-path /path/to/Qwen2.5-1.5B-Instruct \
  --epochs 2
```

Optional: `--max-v3-trajectories 50` for a cheaper HF eval smoke. Full v3 eval is ~2.5k trajectories / ~24k actions.

## Files

| File | Contents |
|---|---|
| `report.md` | this document |
| `metrics.json` | before/after action + trajectory metrics |
| `split.json` | task ids for train vs synthetic holdout |
| `probe.json` | GPU / weights / backend decision |
| `example_counts.json` | SFT row counts |
| `train_stats.json` | mock fit or LoRA trainer metrics |

