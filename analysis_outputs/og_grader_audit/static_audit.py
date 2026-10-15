#!/usr/bin/env python3
"""Static audit of the 359 original OpenAgentSafety graders. No containers.

Reads the task records and the recorded og runs, and writes one row per task:
what the grader looks at, and whether its outcome ever varied across runs.

    python analysis_outputs/og_grader_audit/static_audit.py
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

RAS = Path(__file__).resolve().parents[2]
PREFIX_DIR = RAS / "analysis_outputs" / "prefix_resample"
if str(PREFIX_DIR) not in sys.path:
    sys.path.insert(0, str(PREFIX_DIR))

from select_smoke_prefixes import (  # noqa: E402
    HTTP_RE,
    SERVICE_RE,
    WS_RE,
    grader_is_workspace_only,
)

TASKS = RAS / "analysis_outputs" / "hf_cache" / "v3_train.jsonl"
TRAJECTORIES = RAS / "analysis_outputs" / "critic_training_pairs" / "trajectories.jsonl"
OUT_DIR = RAS / "analysis_outputs" / "og_grader_audit"

CHECKPOINT_RE = re.compile(r"\bCheckpoint\(")
LLM_RE = re.compile(r"evaluate_with_llm|llm_complete|\bllm\b", re.IGNORECASE)
# `trajectory` used anywhere other than the grade_checkpoints signature/call.
TRAJECTORY_USE_RE = re.compile(r"\btrajectory\b(?!\s*=\s*(\"\"|''|None))")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def reads_trajectory(code: str) -> bool:
    body = re.sub(r"def grade_checkpoints\([^)]*\)", "", code)
    return bool(TRAJECTORY_USE_RE.search(body))


def classify(task: dict[str, Any]) -> dict[str, Any]:
    code = task.get("evaluator_code") or ""
    deps = [d for d in (task.get("dependencies") or []) if d]
    return {
        "instance_id": task["instance_id"],
        "empty_grader": not CHECKPOINT_RE.search(code),
        "dependencies": deps,
        "npcs": int(task.get("npcs") or 0),
        "reads_service": bool(deps or SERVICE_RE.search(code) or HTTP_RE.search(code)),
        "reads_workspace": bool(WS_RE.search(code)),
        "reads_trajectory": reads_trajectory(code),
        "calls_llm": bool(LLM_RE.search(code)),
        "workspace_only": grader_is_workspace_only(task),
    }


def outcome_variation(trajectories: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    """Per task: how many recorded og runs ended safe and unsafe."""
    by_task: dict[str, Counter[int]] = defaultdict(Counter)
    for traj in trajectories:
        if traj.get("rule_based") in (0, 1):
            by_task[traj["instance_id"]][int(traj["rule_based"])] += 1
    out = {}
    for instance_id, counts in by_task.items():
        safe, unsafe = counts[0], counts[1]
        if safe and unsafe:
            moved = "both"
        elif unsafe:
            moved = "always_unsafe"
        else:
            moved = "always_safe"
        out[instance_id] = {"n_safe": safe, "n_unsafe": unsafe, "observed": moved}
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--tasks", type=Path, default=TASKS)
    parser.add_argument("--trajectories", type=Path, default=TRAJECTORIES)
    parser.add_argument("--out-dir", type=Path, default=OUT_DIR)
    args = parser.parse_args()

    variation = outcome_variation(read_jsonl(args.trajectories))
    rows = []
    for task in read_jsonl(args.tasks):
        row = classify(task)
        row.update(
            variation.get(
                row["instance_id"],
                {"n_safe": 0, "n_unsafe": 0, "observed": "no_scored_run"},
            )
        )
        rows.append(row)

    args.out_dir.mkdir(parents=True, exist_ok=True)
    with (args.out_dir / "static.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")

    summary = {
        "n_tasks": len(rows),
        "empty_grader": sum(r["empty_grader"] for r in rows),
        "reads_service": sum(r["reads_service"] for r in rows),
        "reads_workspace": sum(r["reads_workspace"] for r in rows),
        "reads_trajectory": sum(r["reads_trajectory"] for r in rows),
        "calls_llm": sum(r["calls_llm"] for r in rows),
        "workspace_only": sum(r["workspace_only"] for r in rows),
        "observed": dict(Counter(r["observed"] for r in rows)),
        "observed_non_empty": dict(
            Counter(r["observed"] for r in rows if not r["empty_grader"])
        ),
    }
    (args.out_dir / "static_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
