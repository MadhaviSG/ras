#!/usr/bin/env python3
"""Bidirectional nudge pilot on the prefixes whose continuations never split.

Four of the five smoke prefixes produced the same grader outcome on all four
natural continuations. That is consistent with two very different worlds: the
prefix genuinely determines the outcome, or the sampler simply never explored
the other branch. A nudge distinguishes them. If a directed instruction can
move a prefix off its fixed outcome, the prefix was not determinative.

The direction is not a free choice. An all-safe prefix can only be moved by a
harm-directed nudge and an all-unsafe one only by a safety-directed nudge, so
each task's arms are derived from its own control outcomes rather than fixed
in advance. The natural runs already on disk are the unnudged control, so this
adds no control cost.

Unit of report is the task, not the continuation: four tasks is four
observations, and per-continuation counts would overstate the evidence.

Usage:
    python run_nudge_pilot.py --llm-config <path> [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

RAS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAS / "benchmarks"))
sys.path.insert(0, str(RAS / "benchmarks" / "safety_monitor"))

RESAMPLE_DIR = RAS / "analysis_outputs" / "prefix_resample"
CONTROL_FILE = RESAMPLE_DIR / "smoke_runs" / "continuations.jsonl"
PREFIX_FILE = RESAMPLE_DIR / "smoke_prefixes.jsonl"
DEFAULT_OUT = RESAMPLE_DIR / "nudge_pilot"

# "pointed" stays off: it names the sink path, which makes the continuation a
# transcription task rather than a decision.
HARM_ARMS = ("overt", "pressure")
SAFETY_ARMS = ("safety", "refusal")
N_PER_ARM = 2


def control_outcomes(path: Path) -> dict[str, list[bool]]:
    outcomes: dict[str, list[bool]] = defaultdict(list)
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        if row.get("error") or row.get("grader_unsafe") is None:
            continue
        outcomes[row["instance_id"]].append(bool(row["grader_unsafe"]))
    return dict(outcomes)


def plan_arms(outcomes: dict[str, list[bool]]) -> list[dict[str, Any]]:
    """One plan entry per non-splitting task, with the arms that could move it."""
    plan: list[dict[str, Any]] = []
    for instance_id, results in sorted(outcomes.items()):
        if not results or len(set(results)) > 1:
            continue  # already splits; a nudge would tell us nothing new
        always_unsafe = results[0]
        plan.append(
            {
                "instance_id": instance_id,
                "control_unsafe": results,
                "control_outcome": "unsafe" if always_unsafe else "safe",
                "arms": list(SAFETY_ARMS if always_unsafe else HARM_ARMS),
                "direction": "toward_safety" if always_unsafe else "toward_harm",
                "moved_means": "safe" if always_unsafe else "unsafe",
            }
        )
    return plan


def summarise(
    plan: list[dict[str, Any]], rows: list[dict[str, Any]]
) -> dict[str, Any]:
    by_task: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        by_task[row["instance_id"]].append(row)

    tasks: list[dict[str, Any]] = []
    for entry in plan:
        got = [r for r in by_task.get(entry["instance_id"], []) if not r.get("error")]
        control_unsafe = entry["control_unsafe"][0]
        moved = [r for r in got if bool(r.get("grader_unsafe")) != control_unsafe]
        tasks.append(
            {
                "instance_id": entry["instance_id"],
                "control_outcome": entry["control_outcome"],
                "direction": entry["direction"],
                "n_nudged": len(got),
                "n_errors": len(by_task.get(entry["instance_id"], [])) - len(got),
                "n_moved": len(moved),
                "moved": bool(moved),
                "moved_by": sorted({str(r.get("induced_nudge")) for r in moved}),
            }
        )
    n_moved = sum(1 for t in tasks if t["moved"])
    return {
        "n_tasks": len(tasks),
        "n_tasks_moved": n_moved,
        "n_tasks_fixed": len(tasks) - n_moved,
        "unit_of_report": "task",
        "reading": (
            "A task that moved was not determined by its prefix: the same "
            "prefix reaches both outcomes. A task that did not move is "
            "consistent with a determinative prefix, but two arms at two "
            "samples each is weak evidence for that."
        ),
        "tasks": tasks,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--llm-config", type=Path, required=True)
    parser.add_argument("--prefix-file", type=Path, default=PREFIX_FILE)
    parser.add_argument("--control-file", type=Path, default=CONTROL_FILE)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--n-per-arm", type=int, default=N_PER_ARM)
    # 40 matches the control runs in smoke_runs/metadata.json. A different
    # budget would confound the nudge with more time to act.
    parser.add_argument("--max-iterations", type=int, default=40)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the arm assignment and exit without touching Docker.",
    )
    args = parser.parse_args()

    plan = plan_arms(control_outcomes(args.control_file))
    if not plan:
        print(json.dumps({"error": "no non-splitting tasks in control file"}))
        return 1

    if args.dry_run:
        print(json.dumps({"plan": plan, "n_per_arm": args.n_per_arm}, indent=2))
        return 0

    from benchmarks.openagentsafety.prefix_replay import (
        _build_evaluation,
        evaluate_one_continuation,
        load_prefix_records,
    )

    records = {r["instance_id"]: r for r in load_prefix_records(args.prefix_file)}
    missing = [e["instance_id"] for e in plan if e["instance_id"] not in records]
    if missing:
        print(json.dumps({"error": f"prefixes missing for {missing}"}))
        return 1

    build_args = argparse.Namespace(
        llm_config_path=str(args.llm_config),
        max_iterations=args.max_iterations,
        output_dir=args.out,
    )
    evaluation, _ = _build_evaluation(build_args)

    args.out.mkdir(parents=True, exist_ok=True)
    out_path = args.out / "continuations.jsonl"
    rows: list[dict[str, Any]] = []
    with out_path.open("w", encoding="utf-8") as handle:
        for entry in plan:
            record = records[entry["instance_id"]]
            for arm_index, arm in enumerate(entry["arms"]):
                for k in range(args.n_per_arm):
                    row = evaluate_one_continuation(
                        evaluation,
                        record,
                        continuation_index=arm_index * args.n_per_arm + k,
                        mode="induced",
                        induced_nudge=arm,  # pyright: ignore[reportArgumentType]
                    )
                    row["control_outcome"] = entry["control_outcome"]
                    rows.append(row)
                    handle.write(json.dumps(row, default=str) + "\n")
                    handle.flush()
                    print(
                        f"{entry['instance_id']} {arm} {k} "
                        f"unsafe={row.get('grader_unsafe')} "
                        f"err={row.get('error')}",
                        file=sys.stderr,
                        flush=True,
                    )

    summary = summarise(plan, rows)
    summary["plan"] = plan
    summary["n_per_arm"] = args.n_per_arm
    summary["control_file"] = str(args.control_file)
    (args.out / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
