#!/usr/bin/env bash
# Batch 2: generate (Sonnet 5, reasoning off) -> review (Gemini 2.5 Pro) -> gates -> no-agent audit -> keep audit-clean -> gpt, then claude.
set -uo pipefail
RAS=/home/mgulavan/ras; V8=$RAS/analysis_outputs/v8_tasks; G=/home/mgulavan/oasgen
CFG=/tmp/claude-1022/-home-mgulavan/7e9e5ac9-125e-4019-86cf-ba7b8d85c0b1/scratchpad/oasgen_cfg
LOG=$V8/run_v8_batch2.log
export LITELLM_API_KEY=$(python3 -c "import json;print(json.load(open('$RAS/benchmarks/.llm_config/ai-gateway-sonnet.json'))['api_key'])")
export LOCAL_OAS_DATASET=$V8/v8_batch2_train.jsonl
export OAS_WORKSPACE_ROOT=$RAS/analysis_outputs/mg_workspaces
ts() { date -u +%Y-%m-%dT%H:%M:%SZ; }
{
echo "=== $(ts) generate"
cd $G && uv run --no-project --with openai python3 generate_tasks.py --seeds seeds_batch2.jsonl --gen-config $CFG/sonnet.json --val-config $CFG/gemini-pro.json --out runs/batch2
echo "=== $(ts) build"
python3 - <<'PY'
import json,os
G='/home/mgulavan/oasgen'; V8='/home/mgulavan/ras/analysis_outputs/v8_tasks'
rows=[]
for l in open(f'{G}/seeds_batch2.jsonl'):
    s=json.loads(l); sid=str(s['seed_id'])
    cp=f'{G}/runs/batch2/{sid}.cand.json'; rp=f'{G}/runs/batch2/{sid}.review.json'
    rows.append({"brief":{"brief_id":f"oasgen-b2-{int(sid):02d}","seed_topic":s['seed_topic'],"outcome_category":s['outcome_category'],"mechanism_category":s['mechanism_category'],"intent":s['intent'],"harm_kind":s['harm_kind'],"source":"oasgen/runs/batch2"},
                 "candidate":json.load(open(cp)) if os.path.exists(cp) else None,"review":json.load(open(rp)) if os.path.exists(rp) else None,"gen_error":None})
with open(f'{V8}/generated_batch2.jsonl','w') as f:
    for r in rows: f.write(json.dumps(r)+'\n')
PY
cd $RAS/benchmarks/safety_monitor && uv run --extra dev python -m safety_monitor v8-build --generated analysis_outputs/v8_tasks/generated_batch2.jsonl --ws-root analysis_outputs/mg_workspaces --out analysis_outputs/v8_tasks/batch2
cp $V8/batch2/v8_train.jsonl $V8/v8_batch2_train.jsonl
echo "=== $(ts) audit"
cd $RAS/benchmarks && uv run python -m benchmarks.openagentsafety.setup_only_audit --tasks $V8/v8_batch2_train.jsonl --output $V8/batch2/setup_only.jsonl --num-workers 3
python3 - <<'PY'
import json
V8='/home/mgulavan/ras/analysis_outputs/v8_tasks'
keep=[]
for l in open(f'{V8}/batch2/setup_only.jsonl'):
    d=json.loads(l); fs=d.get('test_result',{}).get('final_score',{})
    ok = fs.get('result',1)==0 and not d.get('error')
    print(f"  audit {d['instance_id']:55s} baseline_result={fs.get('result')} keep={ok}")
    if ok: keep.append(d['instance_id'])
open(f'{V8}/batch2/v8_ids_clean.txt','w').write("\n".join(keep)+"\n"); print(f"  {len(keep)} tasks audit-clean")
PY
for actor in gpt claude; do
  echo "=== $(ts) start $actor"
  bash $RAS/analysis_outputs/mg_rollouts/launch_wave.sh $actor $V8/batch2/v8_ids_clean.txt 0
  echo "=== $(ts) end $actor exit=$?"
done
echo "=== $(ts) done"
} >> $LOG 2>&1
