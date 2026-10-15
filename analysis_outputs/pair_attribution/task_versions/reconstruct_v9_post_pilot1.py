"""Rebuild the v9 task versions that pilot 2 ran against (post-pilot-1 revision).

Pilot 2 ran the 7 tasks changed after pilot 1. No copy of that version was kept: tasks_final.jsonl
also carries the post-pilot-2 revision (revise_post_pilot2.FIXES2). This applies only the
post-pilot-1 FIXES of ../../v9_tasks/post_pilot/revise_post_pilot.py to tasks_final_prepilot.jsonl.
Check: applying FIXES and then FIXES2 reproduces tasks_final.jsonl / tasks_dropped.jsonl exactly
for all 16 tasks, and every pilot-2 run's problem statement, evaluator code, checkpoint text and
NPC strategy hint match this rebuild.

usage: python reconstruct_v9_post_pilot1.py   (writes v9_post_pilot1.jsonl next to this file)
"""
from __future__ import annotations

import copy
import importlib.util
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
POST_PILOT = HERE.parents[1] / "v9_tasks" / "post_pilot"


def main() -> None:
    sys.path.insert(0, str(POST_PILOT))  # revise_post_pilot imports revise_post_pilot2 by name
    spec = importlib.util.spec_from_file_location("revise_post_pilot", POST_PILOT / "revise_post_pilot.py")
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    rows = [json.loads(line) for line in (POST_PILOT / "tasks_final_prepilot.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    out = []
    for row in rows:
        if row["instance_id"] not in module.FIXES:
            continue
        task = copy.deepcopy(row)
        module.FIXES[task["instance_id"]](task)
        out.append(task)
    with (HERE / "v9_post_pilot1.jsonl").open("w", encoding="utf-8") as handle:
        for task in out:
            handle.write(json.dumps(task, ensure_ascii=False) + "\n")
    print(f"wrote {len(out)} tasks: {[t['instance_id'] for t in out]}")


if __name__ == "__main__":
    main()
