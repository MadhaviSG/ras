# Phase 2b — real OAS rollouts on v4 / v5 / v6

Compare **live** frontier-agent trajectories on the LLM-generated tasks against:

1. The constructed synthetic pairs in `analysis_outputs/synthetic_pairs/`
2. The original OAS passive baselines in `benchmarks/results_safety_comparison/baseline_no_analyzer_*`

| Actor | og-OAS rule-unsafe | n |
|---|---:|---:|
| claude-sonnet-4.5 | 38.7% | 266 |
| gpt-5-mini | 43.3% | 275 |

Condition must match those runs: `security_analyzer: none`, `security_mode: passive`, `max_iterations: 500`.

## Tasks on disk

Shipped corpus is **625 tasks / 1250 synthetic trajectories**:
15 v4 + 60 v5 + **550 v6**. Source of truth is the benchmarks copy
(`benchmarks/analysis_outputs/`), not the older ras-root snapshot (407 v6 / 482 total).

OAS task records (use the benchmarks paths):

- v4: `benchmarks/analysis_outputs/hf_cache/v4_train.jsonl`
- v5: `benchmarks/analysis_outputs/v5_generated_tasks/v5_train.jsonl`
- v6: `benchmarks/analysis_outputs/v6_generated_tasks/v6_train.jsonl`

## One-time prepare (fully local dataset)

```bash
python3 /home/mgulavan/ras/analysis_outputs/mg_rollouts/prepare_mg_rollouts.py
python3 /home/mgulavan/ras/analysis_outputs/mg_rollouts/infra_check.py
```

This writes the offline eval JSONL (`local_train.jsonl`, also copied to
`mg_train.jsonl`), `wave1_ids.txt` (50-task gate), and materializes workspace
and utils files under `analysis_outputs/mg_workspaces/`. Every
`workspace_files` / `utils_files` path is a local relative path under
`OAS_WORKSPACE_ROOT`. Eval does not hit HuggingFace or GitHub.

**Agent isolation (matches original OAS):** the evaluated agent only sees the
task instruction, workspace files, and agent-facing utils (`dependencies.yml`,
`init.sh` if present). `evaluator.py` / `eval.py` are **not** listed in
`utils_files` and `run_infer` will refuse to upload them. Host-side copies
remain under `mg_workspaces/.../utils/` for humans/rebuilds. Grading uses
`evaluator_code` on the task record after the agent run. `OAS_WORKSPACE_ROOT`
is host-only path resolution — it is not bind-mounted into the container.

Wave 1 is 15 v4 + 15 v5 + 20 v6. If either actor's rule-unsafe rate is outside
`[15%, 75%]` at n≥20, stop before the full 625×2.

## Launch (needs LITELLM_API_KEY + Docker + TAC)

```bash
export LITELLM_API_KEY=...
export LITELLM_BASE_URL=${LITELLM_BASE_URL:-https://ai-gateway.andrew.cmu.edu}
export OAS_WORKSPACE_ROOT=/home/mgulavan/ras/analysis_outputs/mg_workspaces
# optional override; default is local_train.jsonl
export LOCAL_OAS_DATASET=/home/mgulavan/ras/analysis_outputs/mg_rollouts/local_train.jsonl

# one-task smoke
bash /home/mgulavan/ras/analysis_outputs/mg_rollouts/launch_wave.sh smoke

# wave 1
bash /home/mgulavan/ras/analysis_outputs/mg_rollouts/launch_wave.sh claude
bash /home/mgulavan/ras/analysis_outputs/mg_rollouts/launch_wave.sh gpt

# full set after the gate
bash /home/mgulavan/ras/analysis_outputs/mg_rollouts/launch_wave.sh claude \
  /home/mgulavan/ras/analysis_outputs/mg_rollouts/all_ids.txt
bash /home/mgulavan/ras/analysis_outputs/mg_rollouts/launch_wave.sh gpt \
  /home/mgulavan/ras/analysis_outputs/mg_rollouts/all_ids.txt
```

Full rollout after the gate is **625 tasks × 2 actors**.

Score a finished `output.jsonl`:

```bash
python3 /home/mgulavan/ras/analysis_outputs/mg_rollouts/score_mg_rollouts.py \
  path/to/output.jsonl --actor claude-sonnet-4.5
```

Successful live traces are the real training trajectories if the transfer gap
holds (per-actor unsafe rate within ±10pp of the og baselines after composition
adjustment).
