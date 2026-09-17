#!/usr/bin/env python3
"""Convert finished MG passive OAS rollouts into MinedTrajectory SFT JSONL.

Labels come from the environment evaluator (test_result.final_score), not from
constructed synthetic scripts. Failed conversations and empty evaluators are
skipped. Per-action high-unsafe is weak localization: sink actions on
evaluator-unsafe trajectories only (same idea as v3 critic_training_pairs).
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any

RAS = Path("/home/mgulavan/ras")
BENCH_SM = RAS / "benchmarks" / "safety_monitor"
if str(BENCH_SM) not in sys.path:
    sys.path.insert(0, str(BENCH_SM))

from safety_monitor.synthesis.pairs import LabeledStep, MinedTrajectory  # noqa: E402
from safety_monitor.synthesis.signatures import sink_category  # noqa: E402
from safety_monitor.types import SafetyLabel  # noqa: E402

OUT_DIR = RAS / "analysis_outputs" / "real_rollout_sft"

SOURCES = (
    {
        "model": "claude",
        "actor": "claude-sonnet-4-6",
        "run": "mg_baseline_claude",
        "output": RAS
        / "benchmarks/results_mg_baseline_claude"
        / "__home__mgulavan__ras__analysis_outputs__mg_rollouts__local_train.jsonl-train"
        / "litellm_proxy/us.anthropic.claude-sonnet-4-6_sdk_128452b_maxiter_500_N_passive_none"
        / "output.jsonl",
        "critic": RAS
        / "benchmarks/results_mg_baseline_claude"
        / "__home__mgulavan__ras__analysis_outputs__mg_rollouts__local_train.jsonl-train"
        / "litellm_proxy/us.anthropic.claude-sonnet-4-6_sdk_128452b_maxiter_500_N_passive_none"
        / "output.critic_attempt_1.jsonl",
    },
    {
        "model": "gpt",
        "actor": "gpt-5-mini",
        "run": "mg_baseline_gpt",
        "output": RAS
        / "benchmarks/results_mg_baseline_gpt"
        / "__home__mgulavan__ras__analysis_outputs__mg_rollouts__local_train.jsonl-train"
        / "litellm_proxy/gpt-5-mini_sdk_128452b_maxiter_500_N_passive_none"
        / "output.jsonl",
        "critic": RAS
        / "benchmarks/results_mg_baseline_gpt"
        / "__home__mgulavan__ras__analysis_outputs__mg_rollouts__local_train.jsonl-train"
        / "litellm_proxy/gpt-5-mini_sdk_128452b_maxiter_500_N_passive_none"
        / "output.critic_attempt_1.jsonl",
    },
    {
        "model": "gemini",
        "actor": "gemini-2.5-pro",
        "run": "mg_baseline_gemini",
        "output": RAS
        / "benchmarks/results_mg_baseline_gemini"
        / "__home__mgulavan__ras__analysis_outputs__mg_rollouts__local_train.jsonl-train"
        / "litellm_proxy/gemini/gemini-2.5-pro_sdk_128452b_maxiter_500_N_passive_none"
        / "output.jsonl",
        "critic": RAS
        / "benchmarks/results_mg_baseline_gemini"
        / "__home__mgulavan__ras__analysis_outputs__mg_rollouts__local_train.jsonl-train"
        / "litellm_proxy/gemini/gemini-2.5-pro_sdk_128452b_maxiter_500_N_passive_none"
        / "output.critic_attempt_1.jsonl",
    },
)

MAX_OBS = 4000
MAX_ARG_STR = 8000
SKIP_TOOLS = frozenset({"think", "task_tracker"})


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return rows


def _clip(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n...[truncated]..."


def evaluator_result(record: dict[str, Any]) -> tuple[int | None, int | None]:
    test = record.get("test_result") or {}
    final = test.get("final_score") or test.get("score") or {}
    if isinstance(final, dict) and final.get("result") is not None:
        total = final.get("total")
        return int(final["result"]), int(total) if total is not None else None
    if isinstance(test.get("result"), (int, float)):
        total = test.get("total")
        return int(test["result"]), int(total) if total is not None else None
    return None, None


def corpus_for(instance_id: str, instance: dict[str, Any] | None) -> str:
    tagged = ""
    if isinstance(instance, dict):
        tagged = str(instance.get("corpus") or "").strip().lower()
    if tagged in {"v4", "v5", "v6"}:
        return tagged
    if instance_id.startswith("safety-v6-"):
        return "v6"
    if instance_id.startswith("safety-v5-"):
        return "v5"
    return "v4"


def _clean_args(raw: Any) -> dict[str, Any]:
    if not isinstance(raw, dict):
        return {}
    out: dict[str, Any] = {}
    for key, value in raw.items():
        if key == "kind":
            continue
        if isinstance(value, str) and len(value) > MAX_ARG_STR:
            out[key] = _clip(value, MAX_ARG_STR)
        else:
            out[key] = value
    return out


def extract_steps(
    history: list[Any],
    *,
    instance_id: str,
    unsafe: bool,
) -> tuple[list[LabeledStep], int]:
    steps: list[LabeledStep] = []
    n_sinks = 0
    pending: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for event in history:
        if not isinstance(event, dict):
            continue
        kind = event.get("kind") or event.get("type") or ""
        if kind == "ActionEvent":
            source = str(event.get("source") or "").lower()
            if source and source != "agent":
                continue
            tool = str(event.get("tool_name") or "")
            if not tool or tool in SKIP_TOOLS:
                continue
            action_id = str(event.get("id") or f"{instance_id}:{len(order)}")
            args = _clean_args(event.get("action"))
            pending[action_id] = {
                "action_id": action_id,
                "tool_name": tool,
                "arguments": args,
                "summary": event.get("summary"),
                "observation": "",
                "is_error": False,
            }
            order.append(action_id)
        elif kind == "ObservationEvent":
            action_id = str(event.get("action_id") or "")
            target = pending.get(action_id)
            if target is None:
                continue
            obs = event.get("observation")
            if isinstance(obs, dict):
                text = str(obs.get("content") or "")
                is_error = bool(obs.get("is_error"))
            else:
                text = str(obs or "")
                is_error = False
            target["observation"] = _clip(text, MAX_OBS)
            target["is_error"] = is_error

    for action_id in order:
        raw = pending[action_id]
        sink = sink_category(raw["tool_name"], raw["arguments"])
        if sink:
            n_sinks += 1
        high = bool(unsafe and sink)
        steps.append(
            LabeledStep(
                action_id=raw["action_id"],
                tool_name=raw["tool_name"],
                arguments=raw["arguments"],
                summary=raw.get("summary"),
                observation=raw["observation"] or None,
                is_error=bool(raw["is_error"]),
                sink=sink,
                contrast_lift=0.0,
                label=SafetyLabel.HIGH_UNSAFE if high else SafetyLabel.LOW_UNSAFE,
                label_source="evaluator_sink" if high else "evaluator",
            )
        )
    return steps, n_sinks


def convert_record(
    record: dict[str, Any],
    *,
    model: str,
    actor: str,
    run: str,
) -> tuple[MinedTrajectory | None, str]:
    instance_id = str(record.get("instance_id") or "")
    if not instance_id:
        return None, "no_instance_id"
    if record.get("error") and not (record.get("history") or record.get("test_result")):
        return None, "failed_conversation"
    history = record.get("history") or []
    if not history:
        return None, "empty_history"
    result, total = evaluator_result(record)
    if total == 0:
        return None, "empty_evaluator"
    if result is None:
        return None, "empty_evaluator"
    if result not in (0, 1):
        return None, "empty_evaluator"
    unsafe = result == 1
    steps, n_sinks = extract_steps(history, instance_id=instance_id, unsafe=unsafe)
    if not steps:
        return None, "no_agent_actions"
    instance = record.get("instance") if isinstance(record.get("instance"), dict) else {}
    corpus = corpus_for(instance_id, instance)
    role = "harmful" if unsafe else "clean"
    traj = MinedTrajectory(
        key=f"{run}::{instance_id}",
        instance_id=instance_id,
        run=run,
        condition="mg_passive",
        actor=actor,
        role=role,
        rule_based=1 if unsafe else 0,
        security_blocked=False,
        instruction=record.get("instruction"),
        signature_available=False,
        steps=steps,
        split="train",
        corpus=corpus,
    )
    extra = "harmful_no_sink" if unsafe and n_sinks == 0 else "ok"
    return traj, extra


def summarize_critic(path: Path) -> dict[str, int]:
    rows = _read_jsonl(path)
    n_err = 0
    n_ok = 0
    n_no_hist = 0
    n_empty_eval = 0
    for row in rows:
        hist = row.get("history") or []
        if not hist:
            n_no_hist += 1
        result, total = evaluator_result(row)
        if row.get("error") and not (hist or row.get("test_result")):
            n_err += 1
            continue
        if result is None or total == 0:
            n_empty_eval += 1
            continue
        n_ok += 1
    return {
        "critic_lines": len(rows),
        "critic_ok_eval": n_ok,
        "critic_failed_conversation": n_err,
        "critic_empty_history": n_no_hist,
        "critic_empty_evaluator": n_empty_eval,
    }


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    trajectories: list[MinedTrajectory] = []
    skip: Counter[str] = Counter()
    per_model: dict[str, dict[str, int]] = {}
    seen_keys: set[str] = set()

    for src in SOURCES:
        rows = _read_jsonl(src["output"])
        model_skip: Counter[str] = Counter()
        n_traj = 0
        n_safe = 0
        n_unsafe = 0
        n_actions = 0
        n_high = 0
        n_no_sink = 0
        for record in rows:
            traj, reason = convert_record(
                record,
                model=src["model"],
                actor=src["actor"],
                run=src["run"],
            )
            if traj is None:
                skip[reason] += 1
                model_skip[reason] += 1
                continue
            if traj.key in seen_keys:
                skip["duplicate_key"] += 1
                model_skip["duplicate_key"] += 1
                continue
            seen_keys.add(traj.key)
            trajectories.append(traj)
            n_traj += 1
            n_actions += traj.n_actions
            n_high += traj.high_unsafe_count
            if traj.rule_based:
                n_unsafe += 1
                if traj.high_unsafe_count == 0:
                    n_no_sink += 1
            else:
                n_safe += 1
            if reason == "harmful_no_sink":
                pass
        critic_stats = summarize_critic(src["critic"])
        per_model[src["model"]] = {
            "output_lines": len(rows),
            "n_trajectories": n_traj,
            "n_safe_traj": n_safe,
            "n_unsafe_traj": n_unsafe,
            "n_actions": n_actions,
            "n_high_unsafe_actions": n_high,
            "n_low_unsafe_actions": n_actions - n_high,
            "n_unsafe_unlocalized": n_no_sink,
            "skipped": dict(model_skip),
            **critic_stats,
        }

    out_path = OUT_DIR / "trajectories.jsonl"
    with out_path.open("w", encoding="utf-8") as handle:
        for traj in trajectories:
            handle.write(traj.model_dump_json() + "\n")

    n_safe = sum(1 for t in trajectories if not t.rule_based)
    n_unsafe = sum(1 for t in trajectories if t.rule_based)
    n_actions = sum(t.n_actions for t in trajectories)
    n_high = sum(t.high_unsafe_count for t in trajectories)
    counts = {
        "path": str(out_path),
        "n_trajectories": len(trajectories),
        "n_tasks": len({t.instance_id for t in trajectories}),
        "n_safe_traj": n_safe,
        "n_unsafe_traj": n_unsafe,
        "n_actions": n_actions,
        "n_high_unsafe_actions": n_high,
        "n_low_unsafe_actions": n_actions - n_high,
        "label_rule": {
            "trajectory": "evaluator final_score.result: 1=harmful/unsafe, 0=clean/safe",
            "per_action": (
                "high-unsafe only if trajectory is evaluator-unsafe AND action is "
                "a sink (write/transmit/destroy/permission/vcs/database); "
                "think/task_tracker dropped; no constructed synthetic pivots"
            ),
        },
        "skipped_total": dict(skip),
        "per_model": per_model,
        "note": (
            "Used output.jsonl successful rows only. critic_attempt files include "
            "failed conversations / empty evaluators and were not used as extra "
            "train rows."
        ),
    }
    (OUT_DIR / "counts.json").write_text(
        json.dumps(counts, indent=2), encoding="utf-8"
    )
    print(json.dumps(counts, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
