#!/usr/bin/env python3
"""Credit-assignment pass through the CMU ai-gateway, sized for the SFT gate.

The safety_monitor venv has no ``litellm``, so this talks to the gateway's
OpenAI-compatible endpoint with ``urllib`` and injects the result as a
``completer``. Nothing else about the pass changes: the same prompt, the same
comparison, and the same gate as the local-annotator run.

Sample size is the point. The gate needs at least 30 trajectories per outcome
class before it will compare AUROCs, so the earlier 25-trajectory run could
not open it no matter what the labels said.

Usage:
    python run_gateway_pass.py [--n 70] [--config PATH] [--out DIR]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import signal
import sys
import urllib.error
import urllib.request
from pathlib import Path

RAS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(RAS / "benchmarks" / "safety_monitor"))

DEFAULT_CONFIG = RAS / "benchmarks" / ".llm_config" / "ai-gateway-flash.json"
DEFAULT_OUT = RAS / "analysis_outputs" / "credit_assignment" / "gemini_flash"
TIMEOUT_S = 180
MAX_RETRIES = 3
# Reasoning models spend this budget on thinking before any content appears,
# so a budget sized for the answer alone returns finish_reason "length" with
# an empty message.
MAX_TOKENS = 16000


class _GatewayTimeout(Exception):
    pass


def _on_alarm(signum, frame):
    raise _GatewayTimeout(f"no response within {TIMEOUT_S}s")


def make_gateway_completer(config_path: Path, cache_dir: Path | None = None):
    cfg = json.loads(config_path.read_text(encoding="utf-8"))
    model = str(cfg["model"]).removeprefix("litellm_proxy/")
    url = cfg["base_url"].rstrip("/") + "/v1/chat/completions"
    key = cfg["api_key"]
    if cache_dir is not None:
        cache_dir.mkdir(parents=True, exist_ok=True)

    def _cache_path(messages) -> Path | None:
        if cache_dir is None:
            return None
        digest = hashlib.sha256(
            json.dumps([model, messages], sort_keys=True).encode("utf-8")
        ).hexdigest()[:24]
        return cache_dir / f"{digest}.txt"

    def complete(messages, trajectory=None) -> str:
        label = getattr(trajectory, "instance_id", None) or "call"
        cached = _cache_path(messages)
        if cached is not None and cached.exists():
            text = cached.read_text(encoding="utf-8")
            if text.strip():
                print(f"{label} cached chars={len(text)}", file=sys.stderr, flush=True)
                return text
        payload = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
            "max_tokens": MAX_TOKENS,
        }
        body = json.dumps(payload).encode("utf-8")
        last = ""
        for attempt in range(MAX_RETRIES):
            req = urllib.request.Request(
                url,
                data=body,
                headers={
                    "Authorization": f"Bearer {key}",
                    "Content-Type": "application/json",
                },
            )
            previous = signal.signal(signal.SIGALRM, _on_alarm)
            signal.alarm(TIMEOUT_S)
            try:
                with urllib.request.urlopen(req, timeout=TIMEOUT_S) as resp:
                    data = json.loads(resp.read())
                choice = data["choices"][0]
                content = choice["message"].get("content") or ""
                if content.strip():
                    print(
                        f"{label} attempt {attempt + 1} ok chars={len(content)}",
                        file=sys.stderr,
                        flush=True,
                    )
                    if cached is not None:
                        cached.write_text(content, encoding="utf-8")
                    return content
                last = f"empty content (finish_reason={choice.get('finish_reason')})"
                print(f"{label} attempt {attempt + 1} {last}", file=sys.stderr, flush=True)
            except urllib.error.HTTPError as exc:
                last = f"HTTP {exc.code}"
                print(f"{label} attempt {attempt + 1} {last}", file=sys.stderr, flush=True)
                if exc.code in (400, 401, 403, 404):
                    raise RuntimeError(f"{last} from gateway") from exc
            except Exception as exc:  # noqa: BLE001 - retry transport errors
                last = f"{type(exc).__name__}"
                print(f"{label} attempt {attempt + 1} {last}", file=sys.stderr, flush=True)
            finally:
                signal.alarm(0)
                signal.signal(signal.SIGALRM, previous)
        raise RuntimeError(f"gateway call failed after {MAX_RETRIES} tries: {last}")

    return complete, f"gateway:{model}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=70)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument(
        "--keys-from",
        type=Path,
        default=None,
        help=(
            "proposed_labels.jsonl from an earlier pass. Scores exactly those "
            "trajectories so a second annotator is comparable to the first."
        ),
    )
    args = parser.parse_args()

    from safety_monitor.analysis.credit_assignment import run_credit_assignment

    keys = None
    if args.keys_from is not None:
        keys = [
            json.loads(line)["key"]
            for line in args.keys_from.read_text(encoding="utf-8").splitlines()
            if line.strip()
        ]
        print(f"reusing {len(keys)} keys from {args.keys_from}", file=sys.stderr)

    cache_dir = args.out / "_response_cache"
    completer, completer_id = make_gateway_completer(args.config, cache_dir)
    result = run_credit_assignment(
        out_dir=args.out,
        completer=completer,
        completer_id=completer_id,
        real_llm=True,
        keys=keys,
        mixed_sample=None if keys else args.n,
        sample_seed=args.seed,
        annotator={
            "model": completer_id,
            "completer_kind": "gateway",
            "host": json.loads(args.config.read_text())["base_url"],
            "keys_from": str(args.keys_from) if args.keys_from else None,
            "quality_note": (
                "Frontier-hosted annotator via the CMU ai-gateway, sampled at "
                f"{len(keys) if keys else args.n} trajectories so the SFT "
                "gate's 30-per-class floor is cleared. Still a candidate "
                "label set, not ground truth."
            ),
        },
    )
    print(json.dumps(result["trajectory_outcome"], indent=2))
    print(json.dumps(result["sink_rule_read"], indent=2))
    print("outputs:", result["paths"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
