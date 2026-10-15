#!/usr/bin/env bash
# v9 pilot 2: one run per actor on the 7 tasks changed after pilot 1 (14 rollouts), gpt wave then claude wave.
# Before each wave ownCloud CustomerAudits/ (read by the itar grader) is emptied; after each wave it is
# copied read-only to pilot2_owncloud_snapshots/<actor>/.
set -uo pipefail
RAS=/home/mgulavan/ras
V9=$RAS/analysis_outputs/v9_tasks
DAV=http://localhost:8092/remote.php/dav/files/theagentcompany
PY=$RAS/benchmarks/safety_monitor/.venv/bin/python
export LITELLM_API_KEY=$($PY -I -c 'import json,sys;print(json.load(open(sys.argv[1]))["api_key"])' $RAS/analysis_outputs/mg_rollouts/llm_configs/gpt.json)
export LOCAL_OAS_DATASET=$V9/v9_train.jsonl
IDS=$V9/v9_pilot2_ids.txt
ts() { date -u +%FT%TZ; }
reset_folder() {
  local f=$1
  del=$(curl -s -o /dev/null -w '%{http_code}' -u theagentcompany:theagentcompany -X DELETE "$DAV/$f/")
  mk=$(curl -s -o /dev/null -w '%{http_code}' -u theagentcompany:theagentcompany -X MKCOL "$DAV/$f/")
  n=$(curl -s -u theagentcompany:theagentcompany -X PROPFIND -H 'Depth: 1' "$DAV/$f/" | grep -o '<d:href>' | wc -l)
  echo "=== $(ts) reset ownCloud $f: DELETE -> $del MKCOL -> $mk PROPFIND entries=$n (1 = empty)"
}
echo "=== $(ts) v9 pilot2 start"
for actor in gpt claude; do
  reset_folder CustomerAudits
  echo "=== $(ts) start $actor"
  NOTE_OVERRIDE=passive_none_p2 OUT_OVERRIDE=$RAS/benchmarks/results_mg_v9_pilot2_$actor \
    bash $RAS/analysis_outputs/mg_rollouts/launch_wave.sh "$actor" "$IDS"
  echo "=== $(ts) end $actor exit=$?"
  $PY -I $V9/snapshot_owncloud.py $V9/pilot2_owncloud_snapshots/$actor CustomerAudits/
done
echo "=== $(ts) v9 pilot2 done"
