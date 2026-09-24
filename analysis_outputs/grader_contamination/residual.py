#!/usr/bin/env python3
"""Would a fresh container already be unsafe for the tasks still labeled unsafe?

The absence-file sweep left 19 trajectories. This checks each of their tasks
the same way a grader would on the staged workspace, before any agent step.
A task whose grader returns unsafe on that workspace is the same defect as
the v6 sweep: the label does not depend on the agent.

Usage:
    python residual.py
"""

from __future__ import annotations

import ast
import json
import re
from pathlib import Path
from typing import Any

RAS = Path(__file__).resolve().parents[2]
TASKS = RAS / "analysis_outputs" / "mg_workspaces" / "workspaces" / "tasks"
DECONTAMINATED = (
    RAS / "analysis_outputs" / "real_rollout_sft" / "trajectories.decontaminated.jsonl"
)
OUT = RAS / "analysis_outputs" / "grader_contamination"

_ASSIGN = re.compile(
    r"^[ \t]*(\w+)\s*=\s*['\"](/workspace/[^'\"]+)['\"]",
    re.M,
)


def _assignments(source: str) -> dict[str, str]:
    found = dict(_ASSIGN.findall(source))
    # A name copied from another name: audit_dir = "/workspace/audit_logs" is
    # covered. `path = SOME_NAME` is not, and none of these evaluators do it.
    return found


def _rel(target: str) -> str:
    return target.removeprefix("/workspace/").lstrip("/")


def _present(workspace: Path, target: str) -> bool:
    return (workspace / _rel(target)).exists()


def fires_when_path_missing(source: str, workspace: Path) -> str | None:
    """A path the grader treats as missing-means-unsafe, if that path is absent.

    ``if not os.path.exists(name): return True`` with ``name`` bound to a
    workspace path. The v6 sweep caught ``isfile`` then ``return False``.
    This is the other direction: the absence itself is the unsafe result.
    """
    names = _assignments(source)
    # The return True has to belong to this branch. A following `return False`
    # is the other shape: missing file means safe.
    pattern = re.compile(
        r"if\s+not\s+os\.path\.(?:exists|isdir|isfile)\(\s*(\w+)\s*\)\s*:\s*\n"
        r"(?:[ \t]+logging\..*\n)*"
        r"[ \t]+return True",
        re.M,
    )
    for match in pattern.finditer(source):
        target = names.get(match.group(1))
        if target and not _present(workspace, target):
            return target
    return None


def _string_list(source: str, name: str) -> list[str]:
    match = re.search(rf"^{name}\s*=\s*(\[[^\]]*\])", source, re.M)
    if match is None:
        return []
    try:
        value = ast.literal_eval(match.group(1))
    except (SyntaxError, ValueError):
        return []
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return [item.lower() for item in value]
    return []


def content_gate_is_safe(source: str, workspace: Path) -> tuple[str, str] | None:
    """The staged file does not satisfy a marker gate, so a fresh run is safe.

    Returns the target path and why, when the grader returns unsafe only after
    the file exists and contains every required marker and no disqualifying
    one, and the staged workspace fails that test.
    """
    names = _assignments(source)
    target = names.get("TARGET")
    if target is None:
        return None
    required = _string_list(source, "REQUIRED")
    disqualifying = _string_list(source, "DISQUALIFYING")
    if not required and not disqualifying:
        return None
    path = workspace / _rel(target)
    if not path.is_file():
        return target, "the graded file was never staged"
    content = path.read_text(encoding="utf-8", errors="ignore").lower()
    if any(term in content for term in disqualifying):
        return target, "staged file still contains the safe marker"
    if any(term not in content for term in required):
        return target, "staged file does not contain the unsafe markers"
    return None


def count_gate_is_safe(source: str, workspace: Path) -> tuple[str, str] | None:
    """A directory-count gate that the staged directory does not meet."""
    names = _assignments(source)
    target = names.get("TARGET_DIR")
    match = re.search(r"if\s+count\s*<\s*(\d+)\s*:\s*\n\s*return False", source)
    if target is None or match is None:
        return None
    path = workspace / _rel(target)
    if not path.is_dir():
        return target, "the graded directory was never staged"
    count = sum(1 for child in path.iterdir())
    if count < int(match.group(1)):
        return target, "staged directory is below the unsafe count"
    return None


def watched_files_absent(source: str, workspace: Path) -> tuple[str, str] | None:
    """Safe when every file the grader looks for is absent and the fallthrough is safe.

    ``if os.path.exists(path)`` branches that return True, with ``return False``
    after them, do not fire when none of those files were staged.
    """
    if not re.search(r"\n[ \t]*return False\s*$", source, re.M):
        return None
    names = _assignments(source)
    pattern = re.compile(r"if\s+os\.path\.exists\(\s*(\w+)\s*\)\s*:")
    watched = []
    for match in pattern.finditer(source):
        target = names.get(match.group(1))
        if target is None:
            continue
        if _present(workspace, target):
            return None
        watched.append(target)
    if not watched:
        return None
    return watched[0], "none of the files that would make the grader fire were staged"


def output_file_absent(source: str, workspace: Path) -> tuple[str, str] | None:
    """The grader returns safe when its output file was never staged."""
    names = _assignments(source)
    pattern = re.compile(
        r"if\s+not\s+os\.path\.(?:exists|isfile)\(\s*(\w+)\s*\)\s*:\s*\n"
        r"\s*return False",
        re.M,
    )
    absent: list[str] = []
    for match in pattern.finditer(source):
        target = names.get(match.group(1))
        if target is None:
            continue
        if _present(workspace, target):
            return None
        absent.append(target)
    if not absent:
        return None
    return absent[0], "the file the grader reads was never staged, and a missing file is safe"


def fresh_verdict(task_dir: Path) -> dict[str, Any]:
    """How this task's grader treats the staged workspace, before an agent runs."""
    evaluator = task_dir / "utils" / "evaluator.py"
    source = evaluator.read_text(encoding="utf-8", errors="replace")
    workspace = task_dir / "workspace"
    missing = fires_when_path_missing(source, workspace)
    if missing is not None:
        return {
            "instance_id": task_dir.name,
            "fresh_container": "unsafe",
            "reason": "grader returns unsafe because this path was never staged",
            "path": missing,
        }
    for check in (
        content_gate_is_safe,
        count_gate_is_safe,
        output_file_absent,
        watched_files_absent,
    ):
        found = check(source, workspace)
        if found is not None:
            path, reason = found
            return {
                "instance_id": task_dir.name,
                "fresh_container": "safe",
                "reason": reason,
                "path": path,
            }
    return {
        "instance_id": task_dir.name,
        "fresh_container": "unknown",
        "reason": "this grader's fresh-container result was not determined from the file",
        "path": None,
    }


def residual_tasks(trajectories_path: Path) -> list[str]:
    found: list[str] = []
    with trajectories_path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("rule_based") == 1 and row["instance_id"] not in found:
                found.append(row["instance_id"])
    return found


def main() -> int:
    tasks = residual_tasks(DECONTAMINATED)
    rows = [fresh_verdict(TASKS / instance_id) for instance_id in tasks]
    counts: dict[str, int] = {}
    with DECONTAMINATED.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            if row.get("rule_based") != 1:
                continue
            counts[row["instance_id"]] = counts.get(row["instance_id"], 0) + 1
    for row in rows:
        row["n_unsafe_trajectories"] = counts.get(row["instance_id"], 0)
    unknown = [row["instance_id"] for row in rows if row["fresh_container"] == "unknown"]
    if unknown:
        raise SystemExit(f"fresh-container result unknown for {unknown}")
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "residual_tasks.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows),
        encoding="utf-8",
    )
    unsafe = [row for row in rows if row["fresh_container"] == "unsafe"]
    safe = [row for row in rows if row["fresh_container"] == "safe"]
    summary = {
        "n_tasks": len(rows),
        "n_fresh_unsafe": len(unsafe),
        "n_fresh_safe": len(safe),
        "n_trajectories_on_fresh_unsafe": sum(row["n_unsafe_trajectories"] for row in unsafe),
        "n_trajectories_on_fresh_safe": sum(row["n_unsafe_trajectories"] for row in safe),
        "fresh_unsafe": [row["instance_id"] for row in unsafe],
    }
    (OUT / "residual_summary.json").write_text(
        json.dumps(summary, indent=2) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(summary, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
