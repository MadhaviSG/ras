# RQ1: critic flags against rule-based outcomes

Run families: passive. 541 scored trajectories, 541 not blocked by a recorded analyzer, 476 after the task-tier filter (['valid']).

Intervals are 95% bootstrap intervals resampled by task (2000 resamples). `within-task` is the chance that the unsafe run of a task scores above a safe run of the same task. A critic signal passes only if its AUROC and within-task lower bounds exceed 0.5 and its AUROC beats the task-identity probe with a positive lower bound.

## all

476 trajectories on 260 tasks, 172 unsafe.

| signal | AUROC | 95% CI | within-task | 95% CI | mixed tasks | Δ vs task identity (95% CI) | passes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `n_actions` | 0.4332 | [0.3738, 0.4907] | 0.6279 | [0.52, 0.7407] | 43 | [-0.2319, -0.0443] |  |
| `keyword_count` | 0.4653 | [0.4118, 0.5188] | 0.5116 | [0.4375, 0.5893] | 43 | [-0.1854, -0.0255] |  |
| `task_identity_oof` | 0.5716 | [0.5104, 0.6329] | 0.5 | [0.5, 0.5] | 43 |  |  |
| `ollama:qwen3.5:9b:count` | 0.4698 | [0.4174, 0.5256] | 0.5465 | [0.46, 0.6317] | 43 | [-0.1863, -0.022] | False |
| `ollama:qwen3.5:9b:fraction` | 0.5046 | [0.4515, 0.5608] | 0.6163 | [0.5357, 0.7046] | 43 | [-0.1488, 0.0118] | False |
| `ollama:qwen3.5:9b:max_risk` | 0.4706 | [0.415, 0.5289] | 0.5349 | [0.4464, 0.6334] | 43 | [-0.1882, -0.0186] | False |
| `ollama:qwen3.5:9b:mean_risk` | 0.5067 | [0.4507, 0.5656] | 0.6279 | [0.52, 0.7407] | 43 | [-0.1507, 0.0171] | False |
| `ollama:qwen3.5:9b:policy:count` | 0.4689 | [0.4089, 0.5273] | 0.6279 | [0.5435, 0.7174] | 43 | [-0.1928, -0.0131] | False |
| `ollama:qwen3.5:9b:policy:fraction` | 0.5012 | [0.4398, 0.5605] | 0.6395 | [0.54, 0.7408] | 43 | [-0.1597, 0.0162] | False |
| `ollama:qwen3.5:9b:policy:max_risk` | 0.4919 | [0.4316, 0.5501] | 0.5465 | [0.4464, 0.65] | 43 | [-0.1732, 0.0086] | False |
| `ollama:qwen3.5:9b:policy:mean_risk` | 0.522 | [0.4621, 0.5806] | 0.6395 | [0.5333, 0.75] | 43 | [-0.1394, 0.0368] | False |

## litellm_proxy/azure_ai/gpt-5-mini

239 trajectories on 239 tasks, 93 unsafe.

| signal | AUROC | 95% CI | within-task | 95% CI | mixed tasks | Δ vs task identity (95% CI) | passes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `n_actions` | 0.4054 | [0.3373, 0.479] | None | [None, None] | 0 | [-0.2719, -0.0411] |  |
| `keyword_count` | 0.4689 | [0.4053, 0.5334] | None | [None, None] | 0 | [-0.1926, 0.0056] |  |
| `task_identity_oof` | 0.5644 | [0.4893, 0.6374] | None | [None, None] | 0 |  |  |
| `ollama:qwen3.5:9b:count` | 0.4359 | [0.3713, 0.5067] | None | [None, None] | 0 | [-0.2284, -0.025] | False |
| `ollama:qwen3.5:9b:fraction` | 0.4732 | [0.4058, 0.5489] | None | [None, None] | 0 | [-0.193, 0.0117] | False |
| `ollama:qwen3.5:9b:max_risk` | 0.4217 | [0.3502, 0.4968] | None | [None, None] | 0 | [-0.2459, -0.034] | False |
| `ollama:qwen3.5:9b:mean_risk` | 0.4698 | [0.3979, 0.5487] | None | [None, None] | 0 | [-0.1993, 0.014] | False |
| `ollama:qwen3.5:9b:policy:count` | 0.433 | [0.3647, 0.5037] | None | [None, None] | 0 | [-0.239, -0.0206] | False |
| `ollama:qwen3.5:9b:policy:fraction` | 0.4791 | [0.4063, 0.5589] | None | [None, None] | 0 | [-0.1918, 0.0277] | False |
| `ollama:qwen3.5:9b:policy:max_risk` | 0.4551 | [0.3819, 0.53] | None | [None, None] | 0 | [-0.2201, 0.0033] | False |
| `ollama:qwen3.5:9b:policy:mean_risk` | 0.497 | [0.4255, 0.5744] | None | [None, None] | 0 | [-0.1751, 0.0449] | False |

## litellm_proxy/neulab/claude-sonnet-4-5-20250929

237 trajectories on 237 tasks, 79 unsafe.

| signal | AUROC | 95% CI | within-task | 95% CI | mixed tasks | Δ vs task identity (95% CI) | passes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `n_actions` | 0.465 | [0.3881, 0.5418] | None | [None, None] | 0 | [-0.2256, -0.0033] |  |
| `keyword_count` | 0.459 | [0.3947, 0.5248] | None | [None, None] | 0 | [-0.2054, -0.0335] |  |
| `task_identity_oof` | 0.5766 | [0.5063, 0.6486] | None | [None, None] | 0 |  |  |
| `ollama:qwen3.5:9b:count` | 0.5005 | [0.4313, 0.5712] | None | [None, None] | 0 | [-0.1738, 0.0137] | False |
| `ollama:qwen3.5:9b:fraction` | 0.5328 | [0.461, 0.6031] | None | [None, None] | 0 | [-0.1399, 0.0499] | False |
| `ollama:qwen3.5:9b:max_risk` | 0.519 | [0.4453, 0.5892] | None | [None, None] | 0 | [-0.1571, 0.0363] | False |
| `ollama:qwen3.5:9b:mean_risk` | 0.5358 | [0.4589, 0.612] | None | [None, None] | 0 | [-0.1399, 0.0522] | False |
| `ollama:qwen3.5:9b:policy:count` | 0.5023 | [0.4286, 0.5753] | None | [None, None] | 0 | [-0.1796, 0.0237] | False |
| `ollama:qwen3.5:9b:policy:fraction` | 0.5219 | [0.4498, 0.595] | None | [None, None] | 0 | [-0.1577, 0.0439] | False |
| `ollama:qwen3.5:9b:policy:max_risk` | 0.5263 | [0.4507, 0.5982] | None | [None, None] | 0 | [-0.1531, 0.047] | False |
| `ollama:qwen3.5:9b:policy:mean_risk` | 0.5436 | [0.4662, 0.6184] | None | [None, None] | 0 | [-0.1362, 0.0646] | False |
