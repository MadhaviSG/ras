#!/usr/bin/env python3
"""
Parse safety differences reports and produce a comparison table.

Columns:
  Total Assessments, Agreement %, Disagreement %,
  LOW→HIGH %, LOW→MEDIUM %, HIGH→LOW %, UNKNOWN→* % (agent didn't assess)
"""
import re
import csv
import os

os.chdir(os.path.dirname(os.path.abspath(__file__)))

FILES = {
    "Claude Sonnet 4.5": "benchmarks/sonnet4.5-safety_differences_report.txt",
    "Gemini 2.5 Pro":    "benchmarks/gemini2.5pro-safety_differences_report.txt",
    "GPT-4.1 Mini":      "benchmarks/gpt5mini-safety_differences_report.txt",
    "DeepSeek V3":       "benchmarks/deepseekv3_safety_differences_report.txt",
}

OUTPUT_CSV = "safety_policy_comparison.csv"


def parse_report(path):
    with open(path) as f:
        text = f.read()

    # Executive summary
    total = int(re.search(r'Total safety assessments:\s+([\d,]+)', text).group(1).replace(',', ''))
    agree_pct = float(re.search(r'Agreements \(LLM = Cygnal\):\s+[\d,]+ \(([\d.]+)%\)', text).group(1))
    diff_pct  = float(re.search(r'Differences \(LLM ≠ Cygnal\):\s+[\d,]+ \(([\d.]+)%\)', text).group(1))

    # Assessment combinations — parse all "A -> B   count   pct%" lines
    combos = {}
    for m in re.finditer(r'([A-Z]+)\s*->\s*([A-Z]+)\s+([\d,]+)\s+([\d.]+)%', text):
        key = f"{m.group(1)}->{m.group(2)}"
        combos[key] = {
            "count": int(m.group(3).replace(',', '')),
            "pct":   float(m.group(4)),
        }

    # UNKNOWN→* = sum of all UNKNOWN→anything (agent didn't assess)
    unknown_count = sum(v["count"] for k, v in combos.items() if k.startswith("UNKNOWN->"))
    # LOW→UNKNOWN = Cygnal assigned UNKNOWN (rare; Gemini-specific)
    low_to_unknown_count = combos.get("LOW->UNKNOWN", {}).get("count", 0)

    def combo_pct(key):
        return combos.get(key, {}).get("pct", 0.0)

    # UNKNOWN total % recalculated over total assessments
    unknown_pct = round(100 * unknown_count / total, 1) if total else 0.0

    return {
        "Total Assessments":  total,
        "Agreement %":        agree_pct,
        "Disagreement %":     diff_pct,
        "LOW→HIGH %":         combo_pct("LOW->HIGH"),
        "LOW→MEDIUM %":       combo_pct("LOW->MEDIUM"),
        "HIGH→LOW %":         combo_pct("HIGH->LOW"),
        "UNKNOWN→* % (no assessment)": unknown_pct,
    }


def main():
    rows = {name: parse_report(path) for name, path in FILES.items()}

    col_order = [
        "Total Assessments",
        "Agreement %",
        "Disagreement %",
        "LOW→HIGH %",
        "LOW→MEDIUM %",
        "HIGH→LOW %",
        "UNKNOWN→* % (no assessment)",
    ]

    models = list(rows.keys())
    col_w  = 32
    val_w  = 20

    header = f"{'Metric':<{col_w}}" + "".join(f"{m:>{val_w}}" for m in models)
    div    = "=" * len(header)

    print()
    print(div)
    print("OpenAgentSafety — Self-assessed vs GraySwan Cygnal Risk Comparison")
    print("(LLM = model's own safety policy assessment; Cygnal = ground-truth risk label)")
    print(div)
    print(header)
    print("-" * len(header))

    for col in col_order:
        row_str = f"{col:<{col_w}}"
        for model in models:
            val = rows[model].get(col, "N/A")
            if isinstance(val, float):
                cell = f"{val:.1f}%"
            elif col == "Total Assessments":
                cell = f"{val:,}"
            else:
                cell = str(val)
            row_str += f"{cell:>{val_w}}"
        print(row_str)

    print(div)

    # CSV
    with open(OUTPUT_CSV, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["Metric"] + models)
        for col in col_order:
            row = [col]
            for model in models:
                val = rows[model].get(col, "N/A")
                if isinstance(val, float):
                    row.append(f"{val:.1f}%")
                elif col == "Total Assessments":
                    row.append(f"{val:,}")
                else:
                    row.append(val)
            writer.writerow(row)

    print(f"\nCSV saved to: {OUTPUT_CSV}")


if __name__ == "__main__":
    main()
