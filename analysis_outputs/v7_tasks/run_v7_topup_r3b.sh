#!/usr/bin/env bash
# Top-up: re-run the two gpt r3 instances that hung (agent-caused pager / set -e hangs) into a fresh run dir.
set -uo pipefail
RAS=/home/mgulavan/ras
DAV=http://localhost:8092/remote.php/dav/files/theagentcompany
export LITELLM_API_KEY=$(/home/mgulavan/ras/benchmarks/safety_monitor/.venv/bin/python -I -c 'import json,sys;print(json.load(open(sys.argv[1]))["api_key"])' $RAS/analysis_outputs/mg_rollouts/llm_configs/gpt.json)
export LOCAL_OAS_DATASET=$RAS/analysis_outputs/v7_tasks/v7_train.jsonl
ts() { date -u +%FT%TZ; }
del=$(curl -s -o /dev/null -w '%{http_code}' -u theagentcompany:theagentcompany -X DELETE "$DAV/Incidents/")
mk=$(curl -s -o /dev/null -w '%{http_code}' -u theagentcompany:theagentcompany -X MKCOL "$DAV/Incidents/")
n=$(curl -s -u theagentcompany:theagentcompany -X PROPFIND -H 'Depth: 1' "$DAV/Incidents/" | grep -o '<d:href>' | wc -l)
echo "=== $(ts) reset ownCloud before r3b gpt: DELETE Incidents -> $del MKCOL -> $mk PROPFIND entries=$n (1 = empty)"
echo "=== $(ts) start r3b gpt"
NOTE_OVERRIDE=passive_none_r3b OUT_OVERRIDE=$RAS/benchmarks/results_mg_v7_rerun_gpt \
  bash $RAS/analysis_outputs/mg_rollouts/launch_wave.sh gpt $RAS/analysis_outputs/v7_tasks/v7_topup_r3b_ids.txt
echo "=== $(ts) end r3b gpt exit=$?"
