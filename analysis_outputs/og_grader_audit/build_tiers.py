#!/usr/bin/env python3
"""Combine the static audit and the no-agent container check into task tiers.

    python analysis_outputs/og_grader_audit/build_tiers.py

Tiers, one per original OAS task:
  valid              grader adds a checkpoint and a fresh container grades safe
  unsafe_by_default  a fresh container, with no agent, already grades unsafe
  empty              grader adds no checkpoint (total == 0)
  broken             grader raises or defines no grade_checkpoints
  grader_too_broad   starts safe, but a manual read of the source found the
                     check fires on any completion (default_unsafe_causes.jsonl)
"""

from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

RAS = Path(__file__).resolve().parents[2]
OUT_DIR = RAS / "analysis_outputs" / "og_grader_audit"
TRAJECTORIES = RAS / "analysis_outputs" / "critic_training_pairs" / "trajectories.jsonl"
RAW_RUNS = RAS / "benchmarks" / "results_safety_comparison"
PASSIVE_RUNS = ("baseline_no_analyzer_claude", "baseline_no_analyzer_gpt")


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def latest_setup_rows(path: Path) -> dict[str, dict[str, Any]]:
    """Last row per task, preferring a row without an error over a retry error."""
    latest: dict[str, dict[str, Any]] = {}
    for row in read_jsonl(path):
        previous = latest.get(row["instance_id"])
        if previous is None or not row.get("error") or previous.get("error"):
            latest[row["instance_id"]] = row
    return latest


def tier_of(static: dict[str, Any], setup: dict[str, Any] | None) -> str:
    if setup is None or setup.get("error"):
        return "broken"
    if setup.get("total") == 0 or static["empty_grader"]:
        return "empty"
    if setup.get("grader_unsafe"):
        return "unsafe_by_default"
    return "valid"


def unsafe_rates(
    trajectories: list[dict[str, Any]], tiers: dict[str, str]
) -> dict[str, dict[str, Any]]:
    by_run: dict[str, dict[str, Counter[int]]] = defaultdict(
        lambda: {"all": Counter(), "valid": Counter()}
    )
    for traj in trajectories:
        if traj.get("rule_based") not in (0, 1):
            continue
        by_run[traj["run"]]["all"][traj["rule_based"]] += 1
        if tiers.get(traj["instance_id"]) == "valid":
            by_run[traj["run"]]["valid"][traj["rule_based"]] += 1
    out: dict[str, dict[str, Any]] = {}
    for run, counts in sorted(by_run.items()):
        row: dict[str, Any] = {}
        for scope, counter in counts.items():
            n = counter[0] + counter[1]
            row[scope] = {
                "n": n,
                "n_unsafe": counter[1],
                "unsafe_rate": round(counter[1] / n, 4) if n else None,
            }
        out[run] = row
    return out


def mined_matches_raw(trajectories: list[dict[str, Any]]) -> dict[str, Any]:
    """Does the mined ``rule_based`` equal the raw grader result, passive runs?"""
    mined = {
        (t["run"], t["instance_id"]): t["rule_based"]
        for t in trajectories
        if t["run"] in PASSIVE_RUNS
    }
    checked = mismatched = 0
    for run in PASSIVE_RUNS:
        for output in (RAW_RUNS / run).rglob("output.jsonl"):
            for row in read_jsonl(output):
                key = (run, row["instance_id"])
                final = (row.get("test_result") or {}).get("final_score") or {}
                if key not in mined or not final.get("total"):
                    continue
                checked += 1
                mismatched += int(mined[key] != int(final["result"] > 0))
    return {"checked": checked, "mismatched": mismatched}


def too_broad_tasks() -> set[str]:
    path = OUT_DIR / "default_unsafe_causes.jsonl"
    if not path.exists():
        return set()
    return {
        r["instance_id"] for r in read_jsonl(path) if r["cause"] == "grader_too_broad"
    }


def main() -> None:
    static = {r["instance_id"]: r for r in read_jsonl(OUT_DIR / "static.jsonl")}
    too_broad = too_broad_tasks()
    setup = latest_setup_rows(OUT_DIR / "setup_only.jsonl")
    rows = []
    for instance_id, record in sorted(static.items()):
        setup_row = setup.get(instance_id)
        tier = tier_of(record, setup_row)
        if tier == "valid" and instance_id in too_broad:
            tier = "grader_too_broad"
        rows.append(
            {
                "instance_id": instance_id,
                "tier": tier,
                "setup_error": (setup_row or {}).get("error"),
                "reads_service": record["reads_service"],
                "reads_trajectory": record["reads_trajectory"],
                "calls_llm": record["calls_llm"],
                "workspace_only": record["workspace_only"],
                "observed": record["observed"],
                "n_safe": record["n_safe"],
                "n_unsafe": record["n_unsafe"],
            }
        )
    with (OUT_DIR / "task_tiers.jsonl").open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row) + "\n")

    tiers = {r["instance_id"]: r["tier"] for r in rows}
    trajectories = read_jsonl(TRAJECTORIES)
    default_unsafe = [r for r in rows if r["tier"] == "unsafe_by_default"]
    summary = {
        "n_tasks": len(rows),
        "tiers": dict(Counter(r["tier"] for r in rows)),
        "unsafe_by_default_observed": dict(
            Counter(r["observed"] for r in default_unsafe)
        ),
        "unsafe_by_default_reads_service": sum(
            r["reads_service"] for r in default_unsafe
        ),
        "unsafe_labels_on_unsafe_by_default_tasks": sum(
            t.get("rule_based") == 1 and tiers.get(t["instance_id"]) == "unsafe_by_default"
            for t in trajectories
        ),
        "unsafe_labels_total": sum(t.get("rule_based") == 1 for t in trajectories),
        "valid_observed": dict(
            Counter(r["observed"] for r in rows if r["tier"] == "valid")
        ),
        "valid_reads_service": sum(
            r["reads_service"] for r in rows if r["tier"] == "valid"
        ),
        "unsafe_rates_by_run": unsafe_rates(trajectories, tiers),
        "mined_vs_raw_passive": mined_matches_raw(trajectories),
    }
    (OUT_DIR / "tier_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
