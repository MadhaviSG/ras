#!/usr/bin/env bash
# v9 round-5 pilot: one run per actor on the 4 kept round-5 tasks (8 rollouts), gpt wave then claude wave.
# All four tasks are workspace-only, so no ownCloud reset or snapshot is needed.
# Ids, log and analysis outputs live in ../round5_pilot/ (round5/ is shared with the generation agent).
set -uo pipefail
RAS=/home/mgulavan/ras
V9=$RAS/analysis_outputs/v9_tasks
PY=$RAS/benchmarks/safety_monitor/.venv/bin/python
export LITELLM_API_KEY=$($PY -I -c 'import json,sys;print(json.load(open(sys.argv[1]))["api_key"])' $RAS/analysis_outputs/mg_rollouts/llm_configs/gpt.json)
export LOCAL_OAS_DATASET=$V9/round5/v9_round5_train.jsonl
IDS=$V9/round5_pilot/v9_round5_pilot_ids.txt
ts() { date -u +%FT%TZ; }
echo "=== $(ts) v9 round5 pilot start (dataset sha256 $(sha256sum $LOCAL_OAS_DATASET | cut -c1-16))"
for actor in gpt claude; do
  echo "=== $(ts) start $actor"
  NOTE_OVERRIDE=passive_none_r5p1 OUT_OVERRIDE=$RAS/benchmarks/results_mg_v9_round5_pilot_$actor \
    bash $RAS/analysis_outputs/mg_rollouts/launch_wave.sh "$actor" "$IDS"
  echo "=== $(ts) end $actor exit=$?"
done
echo "=== $(ts) v9 round5 pilot done"
