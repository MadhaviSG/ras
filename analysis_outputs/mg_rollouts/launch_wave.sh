#!/usr/bin/env bash
# Passive OAS rollouts on local v4+v5+v6 (security_analyzer: none).
# Dataset and workspace files are fully local — no HuggingFace / GitHub at eval.
# Matches results_safety_comparison/baseline_no_analyzer_* condition.
set -euo pipefail

RAS=/home/mgulavan/ras
BENCH=$RAS/benchmarks
ROLL=$RAS/analysis_outputs/mg_rollouts
# Host-only file lookup for file_upload. Not bind-mounted into the agent container.
export OAS_WORKSPACE_ROOT=${OAS_WORKSPACE_ROOT:-$RAS/analysis_outputs/mg_workspaces}
DATASET=${LOCAL_OAS_DATASET:-$ROLL/local_train.jsonl}

ACTOR=${1:-}
SELECT=${2:-$ROLL/wave1_ids.txt}
N_LIMIT=${3:-0}

if [[ -z "${ACTOR}" || ! "${ACTOR}" =~ ^(claude|gpt|gemini|smoke)$ ]]; then
  echo "usage: $0 claude|gpt|gemini|smoke [select_file] [n_limit]" >&2
  exit 2
fi

LITELLM_API_KEY=${LITELLM_API_KEY:-${OPENAI_API_KEY:-${AI_GATEWAY_API_KEY:-}}}
if [[ -z "${LITELLM_API_KEY}" ]]; then
  echo "No API key in LITELLM_API_KEY / OPENAI_API_KEY / AI_GATEWAY_API_KEY" >&2
  exit 1
fi

BASE_URL=${LITELLM_BASE_URL:-https://ai-gateway.andrew.cmu.edu}
CFG_DIR=$ROLL/llm_configs
mkdir -p "$CFG_DIR"

write_cfg() {
  local name=$1 model=$2
  python3 - "$CFG_DIR/$name.json" "$model" "$BASE_URL" "$LITELLM_API_KEY" <<'PY'
import json, sys
path, model, base_url, key = sys.argv[1:]
# Bedrock Claude 4.6+ rejects temperature and top_p together.
# OpenHands defaults both; omit top_p so only temperature is sent.
json.dump({
    "model": model,
    "base_url": base_url,
    "api_key": key,
    "timeout": 300,
    "num_retries": 5,
    "drop_params": True,
    "native_tool_calling": True,
    "top_p": None,
}, open(path, "w"), indent=2)
print(path)
PY
}

# CompServ Cloud IDs from GET https://ai-gateway.andrew.cmu.edu/v1/models
# (team access groups: CompServ Cloud - AWS / Google / Azure). Never use neulab/*.
# OpenHands agent uses the litellm_proxy/ provider prefix and strips it.
# chat_npc is a raw OpenAI client and sends the model string as-is; the gateway
# 403s litellm_proxy/* with team_model_access_denied. NPC must be a raw ID.
CLAUDE_MODEL=${CLAUDE_MODEL:-litellm_proxy/us.anthropic.claude-sonnet-4-6}
GPT_MODEL=${GPT_MODEL:-litellm_proxy/gpt-5-mini}
# CompServ Google Gemini (GET /v1/models). Agent uses litellm_proxy/ prefix; NPC does not.
# Prefer 2.5-pro over flash-lite (NPC). No DeepSeek ID on this team — do not invent one.
GEMINI_MODEL=${GEMINI_MODEL:-litellm_proxy/gemini/gemini-2.5-pro}
# Cheap CompServ Google chat; probed 200 with chat_npc shape (temp=0.7, max_tokens=500).
NPC_CHAT_MODEL=${NPC_CHAT_MODEL:-gemini/gemini-2.5-flash-lite}

case "$ACTOR" in
  claude)
    CFG=$(write_cfg claude "$CLAUDE_MODEL")
    OUT=$BENCH/results_mg_baseline_claude
    NOTE=passive_none
    ;;
  gpt)
    CFG=$(write_cfg gpt "$GPT_MODEL")
    OUT=$BENCH/results_mg_baseline_gpt
    NOTE=passive_none
    ;;
  gemini)
    CFG=$(write_cfg gemini "$GEMINI_MODEL")
    OUT=$BENCH/results_mg_baseline_gemini
    NOTE=passive_none
    ;;
  smoke)
    CFG=$(write_cfg claude "$CLAUDE_MODEL")
    OUT=$BENCH/results_mg_smoke
    NOTE=passive_none_smoke
    N_LIMIT=1
    SELECT=$ROLL/wave1_ids.txt
    ;;
esac

export NPC_API_KEY=${NPC_API_KEY:-$LITELLM_API_KEY}
export NPC_BASE_URL=${NPC_BASE_URL:-$BASE_URL}
export NPC_MODEL=${NPC_MODEL:-$NPC_CHAT_MODEL}
NUM_WORKERS=${NUM_WORKERS:-10}
echo "NPC_MODEL=$NPC_MODEL NPC_BASE_URL=$NPC_BASE_URL NUM_WORKERS=$NUM_WORKERS"

cd "$BENCH"
if [[ -x .venv/bin/uv ]]; then
  UV=".venv/bin/uv"
elif command -v uv >/dev/null 2>&1; then
  UV=uv
else
  UV=""
fi

CMD=(openagentsafety-infer "$CFG"
  --dataset "$DATASET"
  --split train
  --output-dir "$OUT"
  --num-workers "$NUM_WORKERS"
  --max-attempts 1
  --max-iterations 500
  --critic pass
  --select "$SELECT"
  --note "$NOTE"
)
if [[ "$N_LIMIT" != "0" ]]; then
  CMD+=(--n-limit "$N_LIMIT")
fi

echo "OAS_WORKSPACE_ROOT=$OAS_WORKSPACE_ROOT"
echo "dataset=$DATASET"
echo "select=$SELECT n_limit=$N_LIMIT out=$OUT"
if [[ -n "$UV" ]]; then
  exec $UV run "${CMD[@]}"
else
  PY=$(command -v python3 || command -v python || true)
  if [[ -z "$PY" ]]; then
    echo "Neither uv nor python3/python found" >&2
    exit 127
  fi
  exec "$PY" -m benchmarks.openagentsafety.run_infer "${CMD[@]:1}"
fi
