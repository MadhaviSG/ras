#!/usr/bin/env bash
# Reproduce the v9 task set: generate+gate+review, build, Docker three-fixture check, final build.
# LLM calls are cached under analysis_outputs/v9_tasks/cache, so a rerun makes no new calls.
set -euo pipefail
RAS=/home/mgulavan/ras
cd $RAS/benchmarks/safety_monitor

# 1. Briefs (seed 9, 40 briefs) -> generate/review/revise -> gates -> tasks.jsonl, v9_rejects.jsonl, gate_counts.json
uv run --extra dev python -m safety_monitor v9-generate --workers 6 --target 40

# 2. Materialise the gated tasks and write the fixture runner's references (chat_npc steps dropped).
#    Post-pilot: the 16 piloted tasks (post_pilot/tasks_final_prepilot.jsonl) are revised by
#    post_pilot/revise_post_pilot.py into tasks_revised.jsonl (12 tasks; 4 more drops in tasks_dropped.jsonl),
#    and that file is what gets built. revise_post_pilot.py also applies the post-pilot-2 revision
#    (post_pilot/revise_post_pilot2.py: itar, meter, sso, ticket) and the post-pilot-3 itar drop (11 tasks). Remove stale workspaces of revised tasks
#    first (files are not deleted on rebuild).
python3 $RAS/analysis_outputs/v9_tasks/post_pilot/revise_post_pilot.py
uv run --extra dev python -m safety_monitor v9-build --tasks analysis_outputs/v9_tasks/tasks_revised.jsonl

# 3. Three-fixture Docker check (noop / safe / harmful) on every gated task.
#    Reset ownCloud CustomerAudits/ first (itar-audit-handoff grades that folder tree).
cd $RAS/benchmarks
uv run python -m benchmarks.openagentsafety.v8_reference_runs \
    --tasks $RAS/analysis_outputs/v9_tasks/v9_train.jsonl \
    --references $RAS/analysis_outputs/v9_tasks/v9_references.jsonl \
    --output $RAS/analysis_outputs/v9_tasks/reference_runs/results_postpilot.jsonl \
    --num-workers 2
#    Post-pilot-2: the changed tasks were rerun (results_postpilot2_changed.jsonl, run_postpilot2.log; it also
#    holds itar, dropped after pilot 3). Post-pilot-3: meter's grader changed again and only meter was rerun
#    (results_postpilot3_meter.jsonl, run_postpilot3_meter.log). results_postpilot3.jsonl = results_postpilot.jsonl
#    with sso/ticket rows from the pilot-2 rerun and the meter row from the pilot-3 rerun, without itar.
uv run python -m benchmarks.openagentsafety.v8_reference_runs \
    --tasks $RAS/analysis_outputs/v9_tasks/v9_train.jsonl \
    --references $RAS/analysis_outputs/v9_tasks/v9_references.jsonl \
    --output $RAS/analysis_outputs/v9_tasks/reference_runs/results_postpilot2_changed.jsonl \
    --select safety-v9-sso-ada-access-review-export,safety-v9-ticket-filename-standardize \
    --num-workers 2
uv run python -m benchmarks.openagentsafety.v8_reference_runs \
    --tasks $RAS/analysis_outputs/v9_tasks/v9_train.jsonl \
    --references $RAS/analysis_outputs/v9_tasks/v9_references.jsonl \
    --output $RAS/analysis_outputs/v9_tasks/reference_runs/results_postpilot3_meter.jsonl \
    --select safety-v9-meter-dispute-dedupe --num-workers 1
python3 - <<'PY'
import json
d = "/home/mgulavan/ras/analysis_outputs/v9_tasks/reference_runs/"
new = {}
for name in ("results_postpilot2_changed.jsonl", "results_postpilot3_meter.jsonl"):
    new.update({json.loads(l)["instance_id"]: l for l in open(d + name) if l.strip()})
rows = [new.get(json.loads(l)["instance_id"], l) for l in open(d + "results_postpilot.jsonl") if l.strip()]
rows = [r for r in rows if json.loads(r)["instance_id"] != "safety-v9-itar-audit-handoff"]
open(d + "results_postpilot3.jsonl", "w").write("".join(r if r.endswith("\n") else r + "\n" for r in rows))
PY

# 4. Keep only tasks that pass the fixtures (or are fixture_pending ownCloud tasks); rebuild v9_train.jsonl
cd $RAS/benchmarks/safety_monitor
uv run --extra dev python -m safety_monitor v9-build \
    --tasks analysis_outputs/v9_tasks/tasks_revised.jsonl \
    --fixtures analysis_outputs/v9_tasks/reference_runs/results_postpilot3.jsonl
