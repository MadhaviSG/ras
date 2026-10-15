"""Round 5: assemble rejects.jsonl (gate rejects + fixture failures + hand-read drops) and print tables.

Run from anywhere: python3 analysis_outputs/v9_tasks/round5/finalize_round5.py
Reads only files under round5/; writes round5/rejects.jsonl and round5/summary.json.
"""

import json
from collections import Counter
from pathlib import Path

R5 = Path(__file__).resolve().parent


def rows(name):
    p = R5 / name
    if not p.exists():
        return []
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()]


gate_rejects = rows("v9_rejects.jsonl")
fixture = rows("fixture_table.jsonl")
drops = rows("tasks_dropped.jsonl")
gated = {t["instance_id"]: t for t in rows("tasks.jsonl")}
final = rows("tasks_round5.jsonl")

out = [dict(r, source="gate") for r in gate_rejects]
for r in fixture:
    if r["status"] not in ("ok", "fixture_pending"):
        t = gated.get(r["instance_id"], {})
        out.append({"instance_id": r["instance_id"], "hook": r["hook"], "outcome": r["outcome"],
                    "stage": "docker_fixture", "reasons": [r["detail"]], "source": "fixture", "task": t})
for d in drops:
    out.append({"instance_id": d["instance_id"], "hook": d["task"]["axes"]["hook"], "outcome": d["task"]["axes"]["outcome"],
                "stage": "hand_read", "reasons": [d["reason"]], "source": "hand_read", "task": d["task"]})
(R5 / "rejects.jsonl").write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in out))

gen = {}
for r in rows("generated.jsonl"):
    gen[r["brief"]["brief_id"]] = r
summary = {
    "briefs_attempted": len(gen),
    "gen_calls_recorded": sum(r.get("gen_calls", 0) for r in gen.values()),
    "gen_errors": {k: r.get("gen_errors_all") or [r["gen_error"]] for k, r in gen.items() if r.get("gen_error") or r.get("gen_errors_all")},
    "review_errors": {k: a["review"]["error"] for k, r in gen.items() for a in r.get("attempts", []) if (a.get("review") or {}).get("error")},
    "funnel": json.loads((R5 / "gate_counts.json").read_text())["funnel"] if (R5 / "gate_counts.json").exists() else {},
    "reject_stages": Counter(r["stage"] for r in out),
    "fixture": Counter(r["status"] for r in fixture),
    "final": len(final),
    "hook_x_outcome": Counter(f"{t['axes']['hook']}/{t['axes']['outcome']}" for t in final),
}
(R5 / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
print(json.dumps(summary, indent=2))
