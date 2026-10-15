#!/usr/bin/env bash
# Three runs per actor of the five v7 main tasks (30 rollouts), one wave at a time.
# Each run writes to a distinct output dir (NOTE_OVERRIDE changes the run folder name),
# and ownCloud Incidents/ is emptied before EVERY run, because the dispatcher grader
# reads every file under Incidents/.
set -uo pipefail
RAS=/home/mgulavan/ras
DAV=http://localhost:8092/remote.php/dav/files/theagentcompany
export LITELLM_API_KEY=$(/home/mgulavan/ras/benchmarks/safety_monitor/.venv/bin/python -I -c 'import json,sys;print(json.load(open(sys.argv[1]))["api_key"])' $RAS/analysis_outputs/mg_rollouts/llm_configs/gpt.json)
export LOCAL_OAS_DATASET=$RAS/analysis_outputs/v7_tasks/v7_train.jsonl
ts() { date -u +%FT%TZ; }
echo "=== $(ts) rerun start"
for run in r1 r2 r3; do
  for actor in gpt claude; do
    del=$(curl -s -o /dev/null -w '%{http_code}' -u theagentcompany:theagentcompany -X DELETE "$DAV/Incidents/")
    mk=$(curl -s -o /dev/null -w '%{http_code}' -u theagentcompany:theagentcompany -X MKCOL "$DAV/Incidents/")
    n=$(curl -s -u theagentcompany:theagentcompany -X PROPFIND -H 'Depth: 1' "$DAV/Incidents/" | grep -o '<d:href>' | wc -l)
    echo "=== $(ts) reset ownCloud before $run $actor: DELETE Incidents -> $del MKCOL -> $mk PROPFIND entries=$n (1 = empty)"
    echo "=== $(ts) start $run $actor"
    NOTE_OVERRIDE=passive_none_$run OUT_OVERRIDE=$RAS/benchmarks/results_mg_v7_rerun_$actor \
      bash $RAS/analysis_outputs/mg_rollouts/launch_wave.sh "$actor" $RAS/analysis_outputs/v7_tasks/v7_main_ids.txt
    echo "=== $(ts) end $run $actor exit=$?"
  done
done
echo "=== $(ts) rerun done"
