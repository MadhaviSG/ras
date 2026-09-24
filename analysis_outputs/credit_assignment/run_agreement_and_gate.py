#!/usr/bin/env python3
"""Agreement between two credit annotators, then the gate on their consensus.

The first annotator's labels already failed the gate. The open question is
whether that failure is a property of the labels or of one particular model.
If a second, independent annotator disagrees action by action, no single
annotator's labels are a training signal. If they agree closely and the
consensus still fails the gate, the failure is about the label source itself.

The second annotator never sees the first annotator's labels or the sink
heuristic; both see the same prompt, including the same task-level grader
outcome.

Usage:
    python run_agreement_and_gate.py --a DIR --b DIR --out DIR
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

RAS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAS / "benchmarks" / "safety_monitor"))

CREDIT = RAS / "analysis_outputs" / "credit_assignment"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--a", type=Path, default=CREDIT / "sonnet5")
    parser.add_argument("--b", type=Path, default=CREDIT / "gemini_pro")
    parser.add_argument("--out", type=Path, default=CREDIT / "consensus")
    parser.add_argument("--name-a", default="sonnet5")
    parser.add_argument("--name-b", default="gemini-2.5-pro")
    args = parser.parse_args()

    from safety_monitor.analysis.annotator_agreement import run_agreement
    from safety_monitor.sft.label_gate import run_sft_gate

    result = run_agreement(
        a_path=args.a / "proposed_labels.jsonl",
        b_path=args.b / "proposed_labels.jsonl",
        out_dir=args.out,
        annotator_a=args.name_a,
        annotator_b=args.name_b,
    )
    print((args.out / "agreement.txt").read_text(encoding="utf-8"))

    # The trajectories come from the first annotator's run because that file
    # already holds exactly the shared 70. The consensus assignments override
    # its per-step labels, so nothing from annotator A's labels leaks in.
    gate = run_sft_gate(
        trajectories_path=args.a / "labeled_trajectories.jsonl",
        labels_path=result["consensus_labels"],
        out_dir=args.out,
        launch_if_open=False,
    )
    print(f"gate open: {gate['open']}")
    print(gate["reason"])

    summary = {
        "agreement": result["report"],
        "gate": gate,
        "annotator_a": args.name_a,
        "annotator_b": args.name_b,
    }
    (args.out / "summary.json").write_text(
        json.dumps(summary, indent=2), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
