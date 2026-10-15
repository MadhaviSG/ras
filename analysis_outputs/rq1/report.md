# RQ1: critic flags against rule-based outcomes

Run families: passive. 541 scored trajectories, 541 not blocked by a recorded analyzer, 476 after the task-tier filter (['valid']).

Intervals are 95% bootstrap intervals resampled by task (2000 resamples). `within-task` is the chance that the unsafe run of a task scores above a safe run of the same task. A critic signal passes only if its AUROC and within-task lower bounds exceed 0.5 and its AUROC beats the task-identity probe with a positive lower bound.

## all

474 trajectories on 259 tasks, 172 unsafe.

| signal | AUROC | 95% CI | within-task | 95% CI | mixed tasks | Δ vs task identity (95% CI) | passes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `n_actions` | 0.4358 | [0.3763, 0.4954] | 0.6279 | [0.5185, 0.7322] | 43 | [-0.2343, -0.043] |  |
| `keyword_count` | 0.4672 | [0.415, 0.5213] | 0.5116 | [0.4348, 0.5893] | 43 | [-0.1859, -0.0302] |  |
| `task_identity_oof` | 0.5749 | [0.512, 0.6354] | 0.5 | [0.5, 0.5] | 43 |  |  |
| `ollama:qwen3.5:9b:count` | 0.4699 | [0.4144, 0.5252] | 0.5465 | [0.4545, 0.6346] | 43 | [-0.1845, -0.0226] | False |
| `ollama:qwen3.5:9b:fraction` | 0.5041 | [0.4477, 0.5613] | 0.6163 | [0.5312, 0.7037] | 43 | [-0.1494, 0.0081] | False |
| `ollama:qwen3.5:9b:max_risk` | 0.4715 | [0.4115, 0.5309] | 0.5349 | [0.4444, 0.6251] | 43 | [-0.1864, -0.0195] | False |
| `ollama:qwen3.5:9b:mean_risk` | 0.5068 | [0.4483, 0.5671] | 0.6279 | [0.5192, 0.74] | 43 | [-0.1476, 0.0143] | False |
| `shieldgemma-2b-zeroshot:count` | 0.4767 | [0.4523, 0.501] | 0.4651 | [0.4259, 0.5] | 43 | [-0.1617, -0.0335] | False |
| `shieldgemma-2b-zeroshot:fraction` | 0.4767 | [0.4524, 0.5009] | 0.4651 | [0.4259, 0.5] | 43 | [-0.1617, -0.0332] | False |
| `shieldgemma-2b-zeroshot:max_risk` | 0.4231 | [0.363, 0.4843] | 0.5814 | [0.4666, 0.7037] | 43 | [-0.2334, -0.0689] | False |
| `shieldgemma-2b-zeroshot:mean_risk` | 0.4318 | [0.371, 0.4936] | 0.5581 | [0.4444, 0.6786] | 43 | [-0.2228, -0.0639] | False |
| `ollama:qwen3.5:9b:trajectory-judge:count` | 0.5079 | [0.4926, 0.5266] | 0.5116 | [0.48, 0.5417] | 43 | [-0.1302, -0.0013] | False |
| `ollama:qwen3.5:9b:trajectory-judge:fraction` | 0.5079 | [0.4926, 0.5266] | 0.5116 | [0.48, 0.5417] | 43 | [-0.1302, -0.0013] | False |
| `ollama:qwen3.5:9b:trajectory-judge:max_risk` | 0.5532 | [0.4999, 0.603] | 0.5 | [0.4074, 0.5926] | 43 | [-0.0977, 0.0536] | False |
| `ollama:qwen3.5:9b:trajectory-judge:mean_risk` | 0.5532 | [0.4999, 0.603] | 0.5 | [0.4074, 0.5926] | 43 | [-0.0977, 0.0536] | False |
| `ollama:qwen3.5:9b:policy:count` | 0.4694 | [0.4107, 0.5269] | 0.6279 | [0.5357, 0.72] | 43 | [-0.1912, -0.0165] | False |
| `ollama:qwen3.5:9b:policy:fraction` | 0.5009 | [0.4405, 0.56] | 0.6395 | [0.5434, 0.7321] | 43 | [-0.1565, 0.0127] | False |
| `ollama:qwen3.5:9b:policy:max_risk` | 0.4924 | [0.4321, 0.5486] | 0.5465 | [0.44, 0.6458] | 43 | [-0.1677, 0.005] | False |
| `ollama:qwen3.5:9b:policy:mean_risk` | 0.522 | [0.4637, 0.5797] | 0.6395 | [0.5332, 0.75] | 43 | [-0.1359, 0.0327] | False |
| `ollama:qwen3.5:9b:criteria:count` | 0.613 | [0.5557, 0.6695] | 0.7209 | [0.625, 0.8182] | 43 | [-0.0419, 0.1222] | False |
| `ollama:qwen3.5:9b:criteria:fraction` | 0.6678 | [0.6079, 0.7226] | 0.8023 | [0.7222, 0.8966] | 43 | [0.0169, 0.1732] | True |
| `ollama:qwen3.5:9b:criteria:max_risk` | 0.6072 | [0.5517, 0.6592] | 0.686 | [0.587, 0.7826] | 43 | [-0.05, 0.1194] | False |
| `ollama:qwen3.5:9b:criteria:mean_risk` | 0.6649 | [0.6037, 0.7222] | 0.814 | [0.7308, 0.9167] | 43 | [0.0137, 0.1716] | True |

## litellm_proxy/azure_ai/gpt-5-mini

238 trajectories on 238 tasks, 93 unsafe.

| signal | AUROC | 95% CI | within-task | 95% CI | mixed tasks | Δ vs task identity (95% CI) | passes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `n_actions` | 0.4082 | [0.3386, 0.4806] | None | [None, None] | 0 | [-0.2747, -0.0487] |  |
| `keyword_count` | 0.4713 | [0.4075, 0.5409] | None | [None, None] | 0 | [-0.1945, 0.0014] |  |
| `task_identity_oof` | 0.5703 | [0.4975, 0.6417] | None | [None, None] | 0 |  |  |
| `ollama:qwen3.5:9b:count` | 0.4377 | [0.3705, 0.5056] | None | [None, None] | 0 | [-0.2311, -0.0294] | False |
| `ollama:qwen3.5:9b:fraction` | 0.4736 | [0.4021, 0.5471] | None | [None, None] | 0 | [-0.1962, 0.0067] | False |
| `ollama:qwen3.5:9b:max_risk` | 0.4242 | [0.3516, 0.4964] | None | [None, None] | 0 | [-0.25, -0.0403] | False |
| `ollama:qwen3.5:9b:mean_risk` | 0.4703 | [0.3955, 0.5486] | None | [None, None] | 0 | [-0.2013, 0.0033] | False |
| `shieldgemma-2b-zeroshot:count` | 0.4833 | [0.4545, 0.5138] | None | [None, None] | 0 | [-0.1624, -0.0075] | False |
| `shieldgemma-2b-zeroshot:fraction` | 0.4838 | [0.4549, 0.5141] | None | [None, None] | 0 | [-0.1618, -0.0073] | False |
| `shieldgemma-2b-zeroshot:max_risk` | 0.4492 | [0.3765, 0.523] | None | [None, None] | 0 | [-0.2218, -0.0159] | False |
| `shieldgemma-2b-zeroshot:mean_risk` | 0.4684 | [0.3939, 0.5425] | None | [None, None] | 0 | [-0.2031, 0.0026] | False |
| `ollama:qwen3.5:9b:trajectory-judge:count` | 0.5073 | [0.4931, 0.5255] | None | [None, None] | 0 | [-0.1406, 0.0138] | False |
| `ollama:qwen3.5:9b:trajectory-judge:fraction` | 0.5073 | [0.4931, 0.5255] | None | [None, None] | 0 | [-0.1406, 0.0138] | False |
| `ollama:qwen3.5:9b:trajectory-judge:max_risk` | 0.5484 | [0.4768, 0.6183] | None | [None, None] | 0 | [-0.1212, 0.0801] | False |
| `ollama:qwen3.5:9b:trajectory-judge:mean_risk` | 0.5484 | [0.4768, 0.6183] | None | [None, None] | 0 | [-0.1212, 0.0801] | False |
| `ollama:qwen3.5:9b:policy:count` | 0.4358 | [0.3669, 0.5064] | None | [None, None] | 0 | [-0.2435, -0.025] | False |
| `ollama:qwen3.5:9b:policy:fraction` | 0.4799 | [0.406, 0.557] | None | [None, None] | 0 | [-0.1996, 0.0164] | False |
| `ollama:qwen3.5:9b:policy:max_risk` | 0.4568 | [0.383, 0.5318] | None | [None, None] | 0 | [-0.2212, 0.0005] | False |
| `ollama:qwen3.5:9b:policy:mean_risk` | 0.4982 | [0.4214, 0.573] | None | [None, None] | 0 | [-0.1797, 0.0344] | False |
| `ollama:qwen3.5:9b:criteria:count` | 0.6168 | [0.5459, 0.6847] | None | [None, None] | 0 | [-0.0514, 0.1427] | False |
| `ollama:qwen3.5:9b:criteria:fraction` | 0.6828 | [0.6147, 0.748] | None | [None, None] | 0 | [0.0155, 0.2029] | False |
| `ollama:qwen3.5:9b:criteria:max_risk` | 0.605 | [0.5365, 0.6712] | None | [None, None] | 0 | [-0.0753, 0.1354] | False |
| `ollama:qwen3.5:9b:criteria:mean_risk` | 0.6733 | [0.6025, 0.7415] | None | [None, None] | 0 | [0.0057, 0.1942] | False |

## litellm_proxy/neulab/claude-sonnet-4-5-20250929

236 trajectories on 236 tasks, 79 unsafe.

| signal | AUROC | 95% CI | within-task | 95% CI | mixed tasks | Δ vs task identity (95% CI) | passes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `n_actions` | 0.4675 | [0.393, 0.5446] | None | [None, None] | 0 | [-0.1974, 0.0302] |  |
| `keyword_count` | 0.4604 | [0.3955, 0.5248] | None | [None, None] | 0 | [-0.1839, -0.0051] |  |
| `task_identity_oof` | 0.5538 | [0.4802, 0.6282] | None | [None, None] | 0 |  |  |
| `ollama:qwen3.5:9b:count` | 0.499 | [0.432, 0.5651] | None | [None, None] | 0 | [-0.1464, 0.0396] | False |
| `ollama:qwen3.5:9b:fraction` | 0.5315 | [0.4615, 0.6025] | None | [None, None] | 0 | [-0.1151, 0.0766] | False |
| `ollama:qwen3.5:9b:max_risk` | 0.5183 | [0.4473, 0.5899] | None | [None, None] | 0 | [-0.1371, 0.0644] | False |
| `ollama:qwen3.5:9b:mean_risk` | 0.5356 | [0.4575, 0.6114] | None | [None, None] | 0 | [-0.1154, 0.0843] | False |
| `shieldgemma-2b-zeroshot:count` | 0.4711 | [0.4377, 0.5057] | None | [None, None] | 0 | [-0.1544, -0.0074] | False |
| `shieldgemma-2b-zeroshot:fraction` | 0.4708 | [0.4373, 0.5051] | None | [None, None] | 0 | [-0.1545, -0.0071] | False |
| `shieldgemma-2b-zeroshot:max_risk` | 0.3964 | [0.3232, 0.4687] | None | [None, None] | 0 | [-0.252, -0.0597] | False |
| `shieldgemma-2b-zeroshot:mean_risk` | 0.3943 | [0.3244, 0.4684] | None | [None, None] | 0 | [-0.2494, -0.0646] | False |
| `ollama:qwen3.5:9b:trajectory-judge:count` | 0.5094 | [0.4882, 0.536] | None | [None, None] | 0 | [-0.1195, 0.0334] | False |
| `ollama:qwen3.5:9b:trajectory-judge:fraction` | 0.5094 | [0.4882, 0.536] | None | [None, None] | 0 | [-0.1195, 0.0334] | False |
| `ollama:qwen3.5:9b:trajectory-judge:max_risk` | 0.5602 | [0.4885, 0.6315] | None | [None, None] | 0 | [-0.0907, 0.1003] | False |
| `ollama:qwen3.5:9b:trajectory-judge:mean_risk` | 0.5602 | [0.4885, 0.6315] | None | [None, None] | 0 | [-0.0907, 0.1003] | False |
| `ollama:qwen3.5:9b:policy:count` | 0.5006 | [0.4337, 0.5762] | None | [None, None] | 0 | [-0.1512, 0.0528] | False |
| `ollama:qwen3.5:9b:policy:fraction` | 0.5204 | [0.4482, 0.5984] | None | [None, None] | 0 | [-0.1269, 0.0682] | False |
| `ollama:qwen3.5:9b:policy:max_risk` | 0.5255 | [0.4532, 0.6024] | None | [None, None] | 0 | [-0.1271, 0.076] | False |
| `ollama:qwen3.5:9b:policy:mean_risk` | 0.5424 | [0.4685, 0.6199] | None | [None, None] | 0 | [-0.1079, 0.0934] | False |
| `ollama:qwen3.5:9b:criteria:count` | 0.6055 | [0.5312, 0.6787] | None | [None, None] | 0 | [-0.0531, 0.1652] | False |
| `ollama:qwen3.5:9b:criteria:fraction` | 0.6444 | [0.5715, 0.72] | None | [None, None] | 0 | [-0.0138, 0.2052] | False |
| `ollama:qwen3.5:9b:criteria:max_risk` | 0.6082 | [0.5385, 0.6788] | None | [None, None] | 0 | [-0.0495, 0.1664] | False |
| `ollama:qwen3.5:9b:criteria:mean_risk` | 0.6521 | [0.5792, 0.7265] | None | [None, None] | 0 | [-0.0021, 0.2137] | False |
