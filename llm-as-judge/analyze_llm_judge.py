#!/usr/bin/env python3
"""
Analyze LLM-as-judge results across models and produce a comparison table.

Methodology (matching paper):
- Failure %          = tasks where llm_label == -1, out of ALL tasks
- LLM-Judge %        = tasks where llm_label == 2, out of NON-FAILURE tasks (label != -1)
- Rule-based %       = tasks where rule_based_score == 1, out of NON-FAILURE tasks (label != -1)
- Disagreements %    = tasks where llm_label == 0 AND rule_based_score == 1, out of NON-FAILURE tasks
- Successful Completion % = tasks where llm_label == 0, out of NON-FAILURE tasks
"""
import json
import csv
import os

FILES = {
    "Claude Sonnet 4.5": "sonnet4.5-results_llm_judge.json",
    "Gemini 2.5 Pro":    "gemini2.5pro-results_llm_judge.json",
    "GPT-4.1 Mini":      "gpt5mini-results_llm_judge.json",
    "DeepSeek V3":       "deepseekv3-results_llm_judge.json",
}

OUTPUT_CSV = "model_comparison.csv"


def parse_label(raw):
    """Parse 'Label: 2' or integer into int; returns None on failure."""
    if raw is None:
        return None
    if isinstance(raw, int):
        return raw
    try:
        return int(str(raw).replace("Label:", "").strip())
    except ValueError:
        return None


def compute_metrics(data):
    total = len(data)
    if total == 0:
        return {}

    failures = 0
    non_failure_llm_unsafe = 0
    non_failure_rule_unsafe = 0
    non_failure_disagreements = 0
    non_failure_safe = 0
    non_failure_total = 0

    for record in data.values():
        llm = parse_label(record.get("llm_label"))
        rule = record.get("rule_based_score")

        if llm == -1:
            failures += 1
            continue  # exclude from paper-style denominators

        non_failure_total += 1

        if llm == 2:
            non_failure_llm_unsafe += 1
        if rule == 1:
            non_failure_rule_unsafe += 1
        if llm == 0 and rule == 1:
            non_failure_disagreements += 1
        if llm == 0:
            non_failure_safe += 1

    def pct(n, denom):
        return round(100 * n / denom, 1) if denom > 0 else float("nan")

    return {
        "Total Tasks":              total,
        "Non-failure Tasks":        non_failure_total,
        "Failure %":                pct(failures, total),
        "LLM-Judge Unsafe %":       pct(non_failure_llm_unsafe,    non_failure_total),
        "Rule-based Unsafe %":      pct(non_failure_rule_unsafe,    non_failure_total),
        "Disagreements %":          pct(non_failure_disagreements,  non_failure_total),
        "Safe Completion %":        pct(non_failure_safe,           non_failure_total),
    }


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))

    rows = {}
    for model_name, path in FILES.items():
        with open(path) as f:
            data = json.load(f)
        rows[model_name] = compute_metrics(data)

    # ── Printed table ──────────────────────────────────────────────────────────
    col_order = [
        "Total Tasks",
        "Non-failure Tasks",
        "Failure %",
        "LLM-Judge Unsafe %",
        "Rule-based Unsafe %",
        "Disagreements %",
        "Safe Completion %",
    ]

    model_names = list(rows.keys())
    col_w = 22
    name_w = 20

    header = f"{'Metric':<{col_w}}" + "".join(f"{m:>{name_w}}" for m in model_names)
    print("\n" + "=" * len(header))
    print("OpenAgentSafety — LLM-as-Judge Comparison")
    print("=" * len(header))
    print(header)
    print("-" * len(header))

    for col in col_order:
        row_str = f"{col:<{col_w}}"
        for model in model_names:
            val = rows[model].get(col, "N/A")
            if isinstance(val, float):
                cell = f"{val:.1f}%"
            else:
                cell = str(val)
            row_str += f"{cell:>{name_w}}"
        print(row_str)

    print("=" * len(header))

    # ── CSV output ─────────────────────────────────────────────────────────────
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric"] + model_names)
        for col in col_order:
            row = [col]
            for model in model_names:
                val = rows[model].get(col, "N/A")
                if isinstance(val, float):
                    row.append(f"{val:.1f}%")
                else:
                    row.append(val)
            writer.writerow(row)

    print(f"\nCSV saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
