#!/usr/bin/env python3
"""
Analyze differences between LLM safety levels and GraySwan Cygnal safety assessments.
Creates a detailed report organized by task and action type.
"""

import re
from pathlib import Path
from collections import Counter, defaultdict
import json
import argparse

def parse_safety_and_summary(lines, start_idx):
    """Parse safety analyzer message and extract action summary."""
    # Start from the security analyzer line
    # Extract the meaningful content after [DOCKER] prefix
    i = start_idx
    message_parts = []
    
    # The first line has: Security analyzer (GraySwanAnalyzer):
    # Next 2-3 lines have the actual message with lots of padding
    i += 1  # Move to next line
    
    # Collect the next few [DOCKER] lines that are continuations (have padding)
    while i < len(lines) and i < start_idx + 5:
        line = lines[i]
        if not line.startswith('[DOCKER]'):
            break
        
        # Extract content after the timestamp/INFO part
        # Format: [DOCKER]                              <actual content>
        # Look for content after many spaces
        content_match = re.search(r'\[DOCKER\]\s+(.+)', line)
        if content_match:
            content = content_match.group(1).strip()
            # Skip if it's just timestamp/INFO
            if content and not content.startswith('['):
                message_parts.append(content)
        
        i += 1
        # Stop if we hit a different log line or Agent Action
        if 'Agent Action' in line:
            break
    
    full_message = ' '.join(message_parts)
    
    # Now look for the Summary line
    summary = None
    while i < len(lines) and i < start_idx + 10:
        if lines[i].strip().startswith('Summary:'):
            summary = lines[i].strip().replace('Summary:', '').strip()
            break
        i += 1
    
    # Pattern: "LLM reported X, analyzer assessed Y for action 'Z'"
    pattern = r"LLM reported (\w+),?\s*analyzer assessed\s+(\w+) for action '([^']+)'"
    match = re.search(pattern, full_message)
    
    if match:
        return {
            'llm_level': match.group(1),
            'cygnal_level': match.group(2),
            'action': match.group(3),
            'summary': summary or 'N/A'
        }
    return None

def analyze_log_file(log_path):
    """Extract all safety comparisons from a log file with summaries."""
    comparisons = []
    instance_name = log_path.stem.replace('instance_', '').replace('.output', '')
    
    with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    
    # Find all "Security analyzer (GraySwanAnalyzer):" lines
    for i, line in enumerate(lines):
        if 'Security analyzer (GraySwanAnalyzer):' in line:
            parsed = parse_safety_and_summary(lines, i)
            if parsed:
                parsed['instance'] = instance_name
                comparisons.append(parsed)
    
    return comparisons

def main():
    parser = argparse.ArgumentParser(description='Analyze safety level differences between LLM and GraySwan Cygnal')
    parser.add_argument('logs_dir', type=Path, help='Path to directory containing log files')
    args = parser.parse_args()
    
    logs_dir = args.logs_dir
    
    all_comparisons = []
    log_files = list(logs_dir.glob('*.log'))
    
    print(f"Analyzing {len(log_files)} log files...")
    
    for log_file in log_files:
        comparisons = analyze_log_file(log_file)
        all_comparisons.extend(comparisons)
    
    # Calculate statistics
    total_comparisons = len(all_comparisons)
    
    if total_comparisons == 0:
        print("ERROR: No safety comparisons found in log files!")
        print("Please check the log file format and parsing logic.")
        return
    
    differences = [c for c in all_comparisons if c['llm_level'] != c['cygnal_level']]
    agreements = [c for c in all_comparisons if c['llm_level'] == c['cygnal_level']]
    
    # Count by combination
    combination_counts = Counter()
    for comp in all_comparisons:
        key = f"{comp['llm_level']} -> {comp['cygnal_level']}"
        combination_counts[key] += 1
    
    # Count differences by action type
    action_differences = defaultdict(lambda: {'total': 0, 'differences': 0, 'agreements': 0})
    for comp in all_comparisons:
        action = comp['action']
        action_differences[action]['total'] += 1
        if comp['llm_level'] != comp['cygnal_level']:
            action_differences[action]['differences'] += 1
        else:
            action_differences[action]['agreements'] += 1
    
    # Count instances with differences
    instances_with_diffs = set(c['instance'] for c in differences)
    
    # Generate detailed report
    report = []
    report.append("=" * 100)
    report.append("SAFETY LEVEL COMPARISON REPORT - TASK-WISE ANALYSIS")
    report.append("LLM vs GraySwan Cygnal Analyzer")
    report.append("=" * 100)
    report.append("")
    
    report.append("EXECUTIVE SUMMARY")
    report.append("-" * 100)
    report.append(f"Total safety assessments:        {total_comparisons:,}")
    report.append(f"Agreements (LLM = Cygnal):       {len(agreements):,} ({len(agreements)/total_comparisons*100:.1f}%)")
    report.append(f"Differences (LLM ≠ Cygnal):      {len(differences):,} ({len(differences)/total_comparisons*100:.1f}%)")
    report.append(f"Instances with differences:      {len(instances_with_diffs)}")
    report.append(f"Total instances analyzed:        {len(log_files)}")
    report.append("")
    
    report.append("ASSESSMENT COMBINATIONS")
    report.append("-" * 100)
    report.append(f"{'LLM Level -> Cygnal Level':<40} {'Count':>10} {'Percentage':>12}")
    report.append("-" * 100)
    for combo, count in combination_counts.most_common():
        percentage = count / total_comparisons * 100
        is_diff = combo.split(' -> ')[0] != combo.split(' -> ')[1]
        marker = " *" if is_diff else ""
        report.append(f"{combo:<40} {count:>10,} {percentage:>11.1f}%{marker}")
    report.append("")
    report.append("* = Difference between LLM and Cygnal")
    report.append("")
    
    report.append("DIFFERENCES BY ACTION TYPE")
    report.append("-" * 100)
    report.append(f"{'Action':<20} {'Total':>10} {'Agreements':>12} {'Differences':>12} {'Diff %':>10}")
    report.append("-" * 100)
    for action, stats in sorted(action_differences.items(), key=lambda x: x[1]['differences'], reverse=True):
        diff_pct = stats['differences'] / stats['total'] * 100 if stats['total'] > 0 else 0
        report.append(f"{action:<20} {stats['total']:>10,} {stats['agreements']:>12,} {stats['differences']:>12,} {diff_pct:>9.1f}%")
    report.append("")
    
    # Task-wise detailed report
    report.append("TASK-WISE DETAILED ANALYSIS")
    report.append("=" * 100)
    report.append("")
    
    # Group by instance
    by_instance = defaultdict(list)
    for comp in all_comparisons:
        by_instance[comp['instance']].append(comp)
    
    # Report only instances with differences
    instances_to_report = sorted([inst for inst in by_instance.keys() 
                                  if any(c['llm_level'] != c['cygnal_level'] for c in by_instance[inst])])
    
    for instance in instances_to_report:
        comps = by_instance[instance]
        diffs_in_instance = [c for c in comps if c['llm_level'] != c['cygnal_level']]
        
        report.append(f"\nTask: {instance}")
        report.append("-" * 100)
        report.append(f"Total actions: {len(comps)}, Differences: {len(diffs_in_instance)}")
        report.append("")
        
        # Group by action type
        by_action_type = defaultdict(list)
        for comp in diffs_in_instance:
            by_action_type[comp['action']].append(comp)
        
        for action_type in sorted(by_action_type.keys()):
            action_comps = by_action_type[action_type]
            report.append(f"  Action Type: {action_type} ({len(action_comps)} differences)")
            report.append("  " + "-" * 96)
            
            for comp in action_comps:
                report.append(f"    LLM: {comp['llm_level']:<10} Cygnal: {comp['cygnal_level']:<10} Summary: {comp['summary']}")
        
        report.append("")
    
    # Pattern-based analysis
    report.append("\nDIFFERENCE PATTERNS BREAKDOWN")
    report.append("=" * 100)
    
    diff_patterns = defaultdict(list)
    for diff in differences:
        pattern = f"{diff['llm_level']} -> {diff['cygnal_level']}"
        diff_patterns[pattern].append(diff)
    
    for pattern, diffs in sorted(diff_patterns.items(), key=lambda x: len(x[1]), reverse=True):
        report.append(f"\n{pattern} ({len(diffs)} occurrences)")
        report.append("-" * 100)
        
        # Group by action within this pattern
        by_action = defaultdict(list)
        for d in diffs:
            by_action[d['action']].append((d['instance'], d['summary']))
        
        for action, inst_summaries in sorted(by_action.items(), key=lambda x: len(x[1]), reverse=True):
            report.append(f"  Action '{action}': {len(inst_summaries)} cases")
            # Show first 3 examples with summaries
            for inst, summary in sorted(inst_summaries)[:3]:
                report.append(f"    - {inst}")
                report.append(f"      Summary: {summary}")
            if len(inst_summaries) > 3:
                report.append(f"    ... and {len(inst_summaries) - 3} more")
    
    report.append("")
    report.append("=" * 100)
    report.append("END OF REPORT")
    report.append("=" * 100)
    
    # Print report
    full_report = "\n".join(report)
    print(full_report)
    
    # Save to file
    output_path = Path('/home/ubuntu/benchmarks-main/benchmarks/safety_differences_report.txt')
    with open(output_path, 'w') as f:
        f.write(full_report)
    
    print(f"\n\nReport saved to: {output_path}")
    
    # Also save raw data as JSON
    json_path = Path('/home/ubuntu/benchmarks-main/benchmarks/safety_differences_data.json')
    with open(json_path, 'w') as f:
        json.dump({
            'total_comparisons': total_comparisons,
            'total_differences': len(differences),
            'total_agreements': len(agreements),
            'combination_counts': dict(combination_counts),
            'action_statistics': dict(action_differences),
            'all_comparisons': all_comparisons,
            'differences_only': differences
        }, f, indent=2)
    
    print(f"Raw data saved to: {json_path}")

if __name__ == '__main__':
    main()
