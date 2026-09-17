# Published MG passive-rollout traces

Copies of the finished `output.jsonl` / `output.critic_attempt_1.jsonl` from
`benchmarks/results_mg_baseline_{claude,gpt,gemini}/` (that tree is gitignored).
GPT files are gzipped because they exceed GitHub’s 100MB blob limit.

`output.jsonl` is the SFT source: successful evaluator rows only.
`output.critic_attempt_1.jsonl` is the full critic log (includes empty eval /
failed conversations). Do not use `*_broken_npc_*`.

## Counts (recomputed from these files)

| Actor | critic lines | usable (`output.jsonl`) | safe (0) | unsafe (1) |
|---|---:|---:|---:|---:|
| Claude Sonnet 4.6 | 673 | 537 | 423 | 114 |
| GPT-5 mini | 673 | 490 | 383 | 107 |
| Gemini 2.5 Pro | 673 | 277 | 214 | 63 |
| **All** | | **1304** | **1020** | **284** |

These match `analysis_outputs/real_rollout_sft/counts.json` and the SFT reports
(`shieldgemma_sft_real`, `qwen_sft_real_bs1`).

## Check a report number

```bash
python3 - <<'PY'
import gzip, json
from pathlib import Path

def rows(path):
    opener = gzip.open if path.suffix == '.gz' else open
    with opener(path, 'rt', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                yield json.loads(line)

root = Path('analysis_outputs/mg_rollout_results')
for actor in ('claude', 'gpt', 'gemini'):
    p = next((root/actor).glob('output.jsonl*'))
    recs = list(rows(p))
    scores = [((r.get('test_result') or {}).get('final_score') or {}).get('result') for r in recs]
    print(actor, 'n', len(recs), 'safe', scores.count(0), 'unsafe', scores.count(1))
PY
```

Final LoRA weights (no trainer optimizer):

- `analysis_outputs/qwen_sft_real_bs1/hf/adapter/`
- `analysis_outputs/shieldgemma_sft_real/hf/adapter/`
