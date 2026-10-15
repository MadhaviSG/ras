#!/usr/bin/env bash
# Round 5: 24 fresh briefs (seed 5), generate+gate+review, build, Docker three-fixture check, final build.
# LLM replies are cached under analysis_outputs/v9_tasks/cache, so a rerun makes no new calls.
set -euo pipefail
RAS=/home/mgulavan/ras
R5=analysis_outputs/v9_tasks/round5
cd $RAS/benchmarks/safety_monitor

# 1. Briefs -> generate/review/revise -> gates -> round5/tasks.jsonl, v9_rejects.jsonl, gate_counts.json
#    As actually run: phase 1a (default reasoning effort) covered r5b00-r5b11 with 23 calls (13 HTTP 504)
#    and was killed between chunks; phase 1b resumed with --gen-reasoning-effort medium and the remaining
#    22 calls, and stopped by itself once 11 tasks had passed the dry run. Every brief now has a record in
#    generated.jsonl, so rerunning either command makes no LLM calls.
COMMON="--sampler round5 --n 24 --seed 5 --max-npc 3 --briefs $R5/briefs.jsonl --out-dir $R5 \
    --exclude-domains-from analysis_outputs/v9_tasks/tasks.jsonl --novelty-extra $R5/novelty_v9_piloted.jsonl \
    --workers 2 --max-attempts 2 --stop-after-dry-run 10 --no-retry-errors --gateway-retries 1 --target 24"
# 1a. uv run --extra dev python -m safety_monitor v9-generate $COMMON --max-gen-calls 45
uv run --extra dev python -m safety_monitor v9-generate $COMMON --max-gen-calls 22 --gen-reasoning-effort medium
# 5b/5c (coordinator follow-up). briefs.jsonl was re-ordered and extended with v9_generate.round5b_briefs
# (r5x00 coldchain regeneration, then r5b16-23 interleaved with 12 fresh r5c briefs; the 24-brief round-5a file is
# kept as briefs_round5a.jsonl). 5b ran with the round-5a drops and was killed between chunks to add the round-5
# pilot lessons to the prompts; 5c resumed with the updated drops. Both stop at --target live (non-dropped) tasks.
B5="--sampler round5 --briefs $R5/briefs.jsonl --out-dir $R5 --novelty-extra $R5/novelty_v9_piloted.jsonl \
    --drops $R5/tasks_dropped.jsonl --workers 2 --max-attempts 2 --no-retry-errors --gateway-retries 1 \
    --gen-reasoning-effort medium --review-reasoning-effort medium"
# 5b: uv run --extra dev python -m safety_monitor v9-generate $B5 --max-gen-calls 45 --target 10
uv run --extra dev python -m safety_monitor v9-generate $B5 --max-gen-calls 34 --target 5

# 2. Materialise every gate-passer (no drops, so Docker covers the hand-read drops too) and write references
uv run --extra dev python -m safety_monitor v9-build --tasks $R5/tasks.jsonl --out $R5 --drops $R5/no_drops.jsonl \
    --stem v9_round5 --final-name tasks_round5.jsonl --references-name references.jsonl

# 3. Three-fixture Docker check
cd $RAS/benchmarks
uv run python -m benchmarks.openagentsafety.v8_reference_runs \
    --tasks $RAS/$R5/v9_round5_train.jsonl --references $RAS/$R5/references.jsonl \
    --output $RAS/$R5/reference_runs/results.jsonl --num-workers 2

# 4. Keep fixture-passing tasks (minus hand-read drops in round5/tasks_dropped.jsonl); rebuild; assemble rejects.jsonl
cd $RAS/benchmarks/safety_monitor
uv run --extra dev python -m safety_monitor v9-build --tasks $R5/tasks.jsonl --out $R5 \
    --fixtures $R5/reference_runs/results.jsonl \
    --stem v9_round5 --final-name tasks_round5.jsonl --references-name references.jsonl
python3 $RAS/$R5/finalize_round5.py
