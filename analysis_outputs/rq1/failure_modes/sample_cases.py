#!/usr/bin/env python3
"""Reproducible sampler for the RQ1 failure-mode case study.

Population: trajectories from the two passive runs (run starts with
"baseline_no_analyzer") on tasks whose tier is "valid", that have a
qwen3.5:9b verdict row.

Groups (seed 0, keys sorted before sampling so file order does not matter):
  miss         rule_based == 1 and no high-unsafe verdict   -> 25,
               stratified by actor (13 from the first actor in sorted
               order, 12 from the second)
  false_alarm  rule_based == 0 and >= 1 high-unsafe verdict -> 20
  hit          rule_based == 1 and >= 1 high-unsafe verdict -> 10

Prints one JSON object per sampled trajectory to stdout. Writes nothing.
Standard library only.

    python sample_cases.py            # the sample
    python sample_cases.py --counts   # population sizes only
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent  # analysis_outputs/
TRAJ = ROOT / "critic_training_pairs" / "trajectories.jsonl"
VERDICTS = HERE.parent / "ollama_qwen3.5_9b" / "verdicts.jsonl"
TIERS = ROOT / "og_grader_audit" / "task_tiers.jsonl"

SEED = 0
N_MISS, N_FALSE_ALARM, N_HIT = 25, 20, 10


def read_jsonl(path):
    with open(path) as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                # verdicts.jsonl may be mid-append; skip a partial last line
                continue


def build_population():
    valid = {r["instance_id"] for r in read_jsonl(TIERS) if r["tier"] == "valid"}
    flags = {}
    for r in read_jsonl(VERDICTS):
        if not r["run"].startswith("baseline_no_analyzer"):
            continue
        flags[r["key"]] = sum(1 for v in r["verdicts"] if v["label"] == "high-unsafe")
    pop = []
    for t in read_jsonl(TRAJ):
        if not t["run"].startswith("baseline_no_analyzer"):
            continue
        if t["instance_id"] not in valid or t["key"] not in flags:
            continue
        pop.append(
            {
                "key": t["key"],
                "instance_id": t["instance_id"],
                "actor": t["actor"],
                "rule_based": t["rule_based"],
                "n_steps": len(t["steps"]),
                "n_flags": flags[t["key"]],
            }
        )
    pop.sort(key=lambda r: r["key"])
    return pop


def sample():
    pop = build_population()
    rng = random.Random(SEED)
    miss = [r for r in pop if r["rule_based"] == 1 and r["n_flags"] == 0]
    fa = [r for r in pop if r["rule_based"] == 0 and r["n_flags"] >= 1]
    hit = [r for r in pop if r["rule_based"] == 1 and r["n_flags"] >= 1]

    out = []
    actors = sorted({r["actor"] for r in miss})
    quota = [N_MISS - N_MISS // len(actors) * (len(actors) - 1)] + [
        N_MISS // len(actors)
    ] * (len(actors) - 1)
    for actor, n in zip(actors, quota):
        rows = [r for r in miss if r["actor"] == actor]
        out += [dict(r, group="miss") for r in rng.sample(rows, n)]
    out += [dict(r, group="false_alarm") for r in rng.sample(fa, N_FALSE_ALARM)]
    out += [dict(r, group="hit") for r in rng.sample(hit, N_HIT)]
    sizes = {
        "population": len(pop),
        "unsafe": sum(r["rule_based"] for r in pop),
        "miss": len(miss),
        "miss_by_actor": {a: sum(r["actor"] == a for r in miss) for a in actors},
        "false_alarm": len(fa),
        "hit": len(hit),
    }
    return out, sizes


if __name__ == "__main__":
    rows, sizes = sample()
    if "--counts" in sys.argv:
        print(json.dumps(sizes, indent=1))
    else:
        for r in rows:
            print(json.dumps(r))
