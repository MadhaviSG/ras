#!/usr/bin/env bash
set -uo pipefail
RAS=/home/mgulavan/ras
DAV=http://localhost:8092/remote.php/dav/files/theagentcompany
export LITELLM_API_KEY=$(/home/mgulavan/ras/benchmarks/safety_monitor/.venv/bin/python -I -c 'import json,sys;print(json.load(open(sys.argv[1]))["api_key"])' $RAS/analysis_outputs/mg_rollouts/llm_configs/gpt.json)
export LOCAL_OAS_DATASET=$RAS/analysis_outputs/v7_tasks/v7_train.jsonl
for actor in gpt claude; do
  # The dispatcher grader reads every file under Incidents/ (v7 runs left Incidents/.env
  # behind for the next actor), so empty the folder and its share links before each actor.
  echo "=== $(date -u +%FT%TZ) reset ownCloud before $actor: DELETE Incidents -> $(curl -s -o /dev/null -w '%{http_code}' -u theagentcompany:theagentcompany -X DELETE "$DAV/Incidents/") MKCOL -> $(curl -s -o /dev/null -w '%{http_code}' -u theagentcompany:theagentcompany -X MKCOL "$DAV/Incidents/")"
  echo "=== $(date -u +%FT%TZ) start $actor"
  bash $RAS/analysis_outputs/mg_rollouts/launch_wave.sh "$actor" $RAS/analysis_outputs/v7_tasks/v7_main_ids.txt
  echo "=== $(date -u +%FT%TZ) end $actor exit=$?"
done
