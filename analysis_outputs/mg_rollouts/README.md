# Phase 2b — real OAS rollouts on v4 / v5 / v6

## What actually ran (this machine)

Passive rollouts (`security_analyzer: none`, `max_iterations: 500`), 10 workers,
CompServ / CMU gateway models, NPC `gemini/gemini-2.5-flash-lite`. 673 task IDs
in `all_ids.txt`. Converted SFT rows are in
`analysis_outputs/real_rollout_sft/` (environment `final_score` labels).

| Actor | Critic rows | Usable trajectories | Safe | Unsafe |
|---|---:|---:|---:|---:|
| Claude Sonnet 4.6 | 673 | 537 | 423 | 114 |
| GPT-5 mini | 673 | 490 | 383 | 107 |
| Gemini 2.5 Pro | 673 | 277 | 214 | 63 |
| **All (SFT file)** | | **1304** | **1020** | **284** |

Raw traces live under `benchmarks/results_mg_baseline_{claude,gpt,gemini}/`
(gitignored). Do not use `*_broken_npc_*` dirs. DeepSeek was not on the CompServ
allow list and was not run.

`launch_wave.sh` in this folder is a **stale 2-actor NeuLab template** (no Gemini,
wrong model IDs, writes API keys into `llm_configs/*.json`). It does not match
the finished runs.

Compare live traces against:

1. The constructed synthetic pairs in `analysis_outputs/synthetic_pairs/`
2. The original OAS passive baselines in `benchmarks/results_safety_comparison/baseline_no_analyzer_*`

| Actor (original OAS) | og-OAS rule-unsafe | n |
|---|---:|---:|
| claude-sonnet-4.5 | 38.7% | 266 |
| gpt-5-mini | 43.3% | 275 |

Condition for those og runs: `security_analyzer: none`, `security_mode: passive`, `max_iterations: 500`.

## Tasks on disk

Shipped corpus is **625 tasks / 1250 synthetic trajectories**:
15 v4 + 60 v5 + **550 v6**. Source of truth is the benchmarks copy
(`benchmarks/analysis_outputs/`), not the older ras-root snapshot (407 v6 / 482 total).

OAS task records (use the benchmarks paths):

- v4: `benchmarks/analysis_outputs/hf_cache/v4_train.jsonl`
- v5: `benchmarks/analysis_outputs/v5_generated_tasks/v5_train.jsonl`
- v6: `benchmarks/analysis_outputs/v6_generated_tasks/v6_train.jsonl`

## One-time prepare

```bash
python3 /home/mgulavan/ras/analysis_outputs/mg_rollouts/prepare_mg_rollouts.py
python3 /home/mgulavan/ras/analysis_outputs/mg_rollouts/infra_check.py
```

This writes `mg_train.jsonl`, `wave1_ids.txt` (50-task gate), and materializes
v5/v6 workspace files under `analysis_outputs/mg_workspaces/`.

Wave 1 is 15 v4 + 15 v5 + 20 v6. If either actor's rule-unsafe rate is outside
`[15%, 75%]` at n≥20, stop before the full 625×2.

## Launch (needs LITELLM_API_KEY + Docker + TAC)

```bash
export LITELLM_API_KEY=...
export LITELLM_BASE_URL=${LITELLM_BASE_URL:-https://ai-gateway.andrew.cmu.edu}
export OAS_WORKSPACE_ROOT=/home/mgulavan/ras/analysis_outputs/mg_workspaces

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
