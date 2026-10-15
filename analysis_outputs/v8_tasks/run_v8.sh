#!/usr/bin/env bash
# Mirror of the v7 pilot: no-agent grader audit, then one passive rollout per actor (gpt, then claude).
set -uo pipefail
RAS=/home/mgulavan/ras
V8=$RAS/analysis_outputs/v8_tasks
LOG=$V8/run_v8.log
export LITELLM_API_KEY=$(python3 -c "import json;print(json.load(open('$RAS/benchmarks/.llm_config/ai-gateway-sonnet.json'))['api_key'])")
export LOCAL_OAS_DATASET=$V8/v8_train.jsonl
export OAS_WORKSPACE_ROOT=$RAS/analysis_outputs/mg_workspaces
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
{
echo "=== $(ts) services"
for p in 8929 8092 8091 3000; do printf "  :%s -> %s\n" $p "$(curl -s -o /dev/null -w '%{http_code}' --max-time 5 http://the-agent-company.com:$p/ || echo down)"; done
docker info >/dev/null 2>&1 && echo "  docker ok" || echo "  docker DOWN"
echo "=== $(ts) start audit"
cd $RAS/benchmarks && uv run python -m benchmarks.openagentsafety.setup_only_audit --tasks $V8/v8_train.jsonl --output $V8/setup_only.jsonl --num-workers 3
echo "=== $(ts) end audit exit=$?"
for actor in gpt claude; do
  echo "=== $(ts) start $actor"
  bash $RAS/analysis_outputs/mg_rollouts/launch_wave.sh $actor $V8/v8_ids.txt 0
  echo "=== $(ts) end $actor exit=$?"
done
echo "=== $(ts) done"
} >> $LOG 2>&1
