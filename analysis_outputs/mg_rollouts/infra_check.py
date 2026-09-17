#!/usr/bin/env python3
"""Write rollout prerequisite status. Does not print secrets."""

from __future__ import annotations

import json
import os
import shutil
import socket
import subprocess
from pathlib import Path
from urllib.parse import urlparse

OUT = Path("/home/mgulavan/ras/analysis_outputs/mg_rollouts/infra_status.json")
BASE = os.environ.get("LITELLM_BASE_URL", "https://ai-gateway.andrew.cmu.edu")


def _run(cmd: list[str], timeout: int = 20) -> dict:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return {
            "ok": proc.returncode == 0,
            "code": proc.returncode,
            "stdout": (proc.stdout or "")[-2000:],
            "stderr": (proc.stderr or "")[-1000:],
        }
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


def _tcp(host: str, port: int, timeout: float = 3.0) -> bool:
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


def main() -> int:
    parsed = urlparse(BASE)
    status = {
        "litellm_api_key_set": bool(
            os.environ.get("LITELLM_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("AI_GATEWAY_API_KEY")
        ),
        "key_env_names": [
            name
            for name in (
                "LITELLM_API_KEY",
                "OPENAI_API_KEY",
                "AI_GATEWAY_API_KEY",
                "NPC_API_KEY",
            )
            if os.environ.get(name)
        ],
        "litellm_base_url": BASE,
        "npc_api_key_set": bool(
            os.environ.get("NPC_API_KEY")
            or os.environ.get("LITELLM_API_KEY")
            or os.environ.get("OPENAI_API_KEY")
            or os.environ.get("AI_GATEWAY_API_KEY")
        ),
        "docker": shutil.which("docker"),
        "uv": shutil.which("uv"),
        "python": shutil.which("python3"),
        "bench_venv": Path("/home/mgulavan/ras/benchmarks/.venv/bin/python").is_file(),
        "docker_ps": _run(["docker", "ps", "--format", "{{.Names}}\t{{.Status}}"]),
        "docker_images": _run(
            ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}"],
        ),
        "tac_gitlab_8929": _tcp("127.0.0.1", 8929),
        "tac_rocketchat_3000": _tcp("127.0.0.1", 3000),
        "tac_owncloud_8092": _tcp("127.0.0.1", 8092),
        "tac_plane_8091": _tcp("127.0.0.1", 8091),
        "litellm_host": parsed.hostname,
        "litellm_tcp_443": _tcp(parsed.hostname or "cmu.litellm.ai", parsed.port or 443),
        "openagentsafety_infer": Path(
            "/home/mgulavan/ras/benchmarks/.venv/bin/openagentsafety-infer"
        ).is_file(),
    }
    images = status["docker_images"].get("stdout") or ""
    status["has_oas_image"] = "openagentsafety-agent-server" in images
    OUT.write_text(json.dumps(status, indent=2) + "\n")
    print(json.dumps({k: v for k, v in status.items() if k != "docker_images"}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
