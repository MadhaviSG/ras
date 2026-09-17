#!/usr/bin/env bash
set -euo pipefail
cd /home/mgulavan/ras/benchmarks/safety_monitor
export CUDA_VISIBLE_DEVICES=0
export PYTHONPATH=.
export PYTHONUNBUFFERED=1
export SHIELDGEMMA_MODEL_PATH=/home/mgulavan/models/shieldgemma-2b
.venv/bin/python -m safety_monitor sft-run \
  --family shieldgemma \
  --train /home/mgulavan/ras/analysis_outputs/real_rollout_sft/trajectories.jsonl \
  --eval /home/mgulavan/ras/analysis_outputs/critic_training_pairs/trajectories.jsonl \
  --out-dir /home/mgulavan/ras/analysis_outputs/shieldgemma_sft_real \
  --backend hf \
  --model-path /home/mgulavan/models/shieldgemma-2b \
  --epochs 2 \
  --batch-size 1 \
  --grad-accum 8 \
  --strict \
  2>&1 | tee /home/mgulavan/ras/analysis_outputs/real_rollout_sft/sft_shieldgemma.log
