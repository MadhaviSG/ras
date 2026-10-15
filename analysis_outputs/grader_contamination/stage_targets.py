#!/usr/bin/env python3
"""Stage the 109 absence-grader targets before any new rollout.

Reads ``flagged_tasks.jsonl``. A path mismatch is copied from the file that
is already staged under another path. A target that was never staged gets a
placeholder. The same relative path is added to the rollout task records.

Usage:
    python stage_targets.py
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from sweep import stage_task_workspace

ROOT = Path(__file__).resolve().parents[2]
FLAGGED = ROOT / "analysis_outputs" / "grader_contamination" / "flagged_tasks.jsonl"
TASKS = ROOT / "analysis_outputs" / "mg_workspaces" / "workspaces" / "tasks"
BACKUP = ROOT / "analysis_outputs" / "grader_contamination" / "backup"
TASK_RECORDS = (
    ROOT / "analysis_outputs" / "mg_rollouts" / "local_train.jsonl",
    ROOT / "analysis_outputs" / "mg_rollouts" / "mg_train.jsonl",
)
MANIFEST = ROOT / "analysis_outputs" / "grader_contamination" / "staged_targets.jsonl"


def _load_flagged() -> list[dict]:
    rows = []
    with FLAGGED.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    return rows


def _backup(path: Path) -> None:
    if not path.is_file():
        return
    BACKUP.mkdir(parents=True, exist_ok=True)
    dest = BACKUP / path.name
    if not dest.exists():
        shutil.copy2(path, dest)


def _patch_records(relative_by_id: dict[str, str]) -> dict[str, int]:
    updated: dict[str, int] = {}
    for path in TASK_RECORDS:
        if not path.is_file():
            continue
        _backup(path)
        rows = []
        changed = 0
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                row = json.loads(line)
                relative = relative_by_id.get(row.get("instance_id"))
                if relative:
                    spec = f"workspaces/tasks/{row['instance_id']}/workspace/{relative}"
                    files = list(row.get("workspace_files") or [])
                    if spec not in files:
                        files.append(spec)
                        row["workspace_files"] = files
                        row["has_workspace"] = True
                        changed += 1
                rows.append(row)
        with path.open("w", encoding="utf-8") as handle:
            for row in rows:
                handle.write(json.dumps(row) + "\n")
        updated[path.name] = changed
    return updated


def main() -> int:
    flagged = _load_flagged()
    manifest = []
    relative_by_id: dict[str, str] = {}
    for row in flagged:
        task_dir = TASKS / row["instance_id"]
        if not task_dir.is_dir():
            raise SystemExit(f"missing task directory {task_dir}")
        staged = stage_task_workspace(task_dir, row)
        if staged is None:
            raise SystemExit(f"could not stage {row['instance_id']}")
        relative_by_id[row["instance_id"]] = staged["relative"]
        manifest.append(staged)
    MANIFEST.write_text(
        "".join(json.dumps(row) + "\n" for row in manifest),
        encoding="utf-8",
    )
    updated = _patch_records(relative_by_id)
    print(
        json.dumps(
            {
                "n_staged": len(manifest),
                "actions": {
                    action: sum(1 for row in manifest if row["action"] == action)
                    for action in ("placeholder", "copied", "already_present")
                },
                "task_records_updated": updated,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
