# RQ1: critic flags against rule-based outcomes

Run families: passive. 443 scored trajectories, 443 not blocked by a recorded analyzer, 378 after the task-tier filter (['valid']).

Intervals are 95% bootstrap intervals resampled by task (2000 resamples). `within-task` is the chance that the unsafe run of a task scores above a safe run of the same task. A critic signal passes only if its AUROC and within-task lower bounds exceed 0.5 and its AUROC beats the task-identity probe with a positive lower bound.

## all

378 trajectories on 209 tasks, 121 unsafe.

| signal | AUROC | 95% CI | within-task | 95% CI | mixed tasks | Δ vs task identity (95% CI) | passes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `n_actions` | 0.4342 | [0.3673, 0.5013] | 0.629 | [0.5, 0.7632] | 31 | [-0.2774, -0.0771] |  |
| `keyword_count` | 0.4934 | [0.43, 0.5553] | 0.5161 | [0.4211, 0.6111] | 31 | [-0.1989, -0.0327] |  |
| `task_identity_oof` | 0.6102 | [0.5444, 0.6773] | 0.5 | [0.5, 0.5] | 31 |  |  |
| `ollama:qwen3.5:9b:count` | 0.5263 | [0.4649, 0.5901] | 0.5806 | [0.475, 0.6842] | 31 | [-0.1748, 0.0054] | False |
| `ollama:qwen3.5:9b:fraction` | 0.5639 | [0.5002, 0.6315] | 0.6452 | [0.5333, 0.75] | 31 | [-0.1354, 0.0417] | False |
| `ollama:qwen3.5:9b:max_risk` | 0.5223 | [0.459, 0.5894] | 0.5645 | [0.4667, 0.6667] | 31 | [-0.1833, 0.0027] | False |
| `ollama:qwen3.5:9b:mean_risk` | 0.5681 | [0.5042, 0.6377] | 0.6452 | [0.5, 0.775] | 31 | [-0.1314, 0.0477] | False |
| `ollama:qwen3.5:9b:policy:count` | 0.5008 | [0.4359, 0.5677] | 0.6613 | [0.5625, 0.7632] | 31 | [-0.206, -0.0165] | False |
| `ollama:qwen3.5:9b:policy:fraction` | 0.5346 | [0.4665, 0.6053] | 0.629 | [0.5203, 0.75] | 31 | [-0.1694, 0.0149] | False |
| `ollama:qwen3.5:9b:policy:max_risk` | 0.5185 | [0.452, 0.5849] | 0.5645 | [0.4444, 0.6875] | 31 | [-0.185, 0.0024] | False |
| `ollama:qwen3.5:9b:policy:mean_risk` | 0.5524 | [0.4862, 0.6216] | 0.629 | [0.5, 0.7647] | 31 | [-0.1507, 0.0347] | False |
| `ollama:qwen3.5:9b:criteria:count` | 0.5998 | [0.5351, 0.6623] | 0.7097 | [0.6, 0.8235] | 31 | [-0.0999, 0.0804] | False |
| `ollama:qwen3.5:9b:criteria:fraction` | 0.6641 | [0.5981, 0.731] | 0.7742 | [0.6667, 0.8889] | 31 | [-0.0311, 0.1431] | False |
| `ollama:qwen3.5:9b:criteria:max_risk` | 0.582 | [0.5189, 0.6416] | 0.6452 | [0.5278, 0.7632] | 31 | [-0.1185, 0.0653] | False |
| `ollama:qwen3.5:9b:criteria:mean_risk` | 0.6632 | [0.5976, 0.7318] | 0.8065 | [0.7, 0.9167] | 31 | [-0.0335, 0.1416] | False |

## litellm_proxy/azure_ai/gpt-5-mini

188 trajectories on 188 tasks, 65 unsafe.

| signal | AUROC | 95% CI | within-task | 95% CI | mixed tasks | Δ vs task identity (95% CI) | passes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `n_actions` | 0.3787 | [0.2973, 0.4577] | None | [None, None] | 0 | [-0.3333, -0.0726] |  |
| `keyword_count` | 0.498 | [0.4209, 0.5803] | None | [None, None] | 0 | [-0.1925, 0.0309] |  |
| `task_identity_oof` | 0.5787 | [0.49, 0.6699] | None | [None, None] | 0 |  |  |
| `ollama:qwen3.5:9b:count` | 0.5051 | [0.425, 0.5857] | None | [None, None] | 0 | [-0.1986, 0.0487] | False |
| `ollama:qwen3.5:9b:fraction` | 0.5498 | [0.4636, 0.6309] | None | [None, None] | 0 | [-0.1596, 0.0956] | False |
| `ollama:qwen3.5:9b:max_risk` | 0.4769 | [0.3892, 0.5632] | None | [None, None] | 0 | [-0.2371, 0.0327] | False |
| `ollama:qwen3.5:9b:mean_risk` | 0.5397 | [0.4518, 0.6279] | None | [None, None] | 0 | [-0.167, 0.0944] | False |
| `ollama:qwen3.5:9b:policy:count` | 0.4789 | [0.3931, 0.5664] | None | [None, None] | 0 | [-0.2297, 0.0311] | False |
| `ollama:qwen3.5:9b:policy:fraction` | 0.5346 | [0.4456, 0.6205] | None | [None, None] | 0 | [-0.1773, 0.0899] | False |
| `ollama:qwen3.5:9b:policy:max_risk` | 0.4922 | [0.4029, 0.5783] | None | [None, None] | 0 | [-0.2193, 0.0555] | False |
| `ollama:qwen3.5:9b:policy:mean_risk` | 0.5402 | [0.4495, 0.6308] | None | [None, None] | 0 | [-0.1713, 0.0991] | False |
| `ollama:qwen3.5:9b:criteria:count` | 0.6033 | [0.5208, 0.6824] | None | [None, None] | 0 | [-0.0966, 0.1415] | False |
| `ollama:qwen3.5:9b:criteria:fraction` | 0.6905 | [0.6129, 0.7693] | None | [None, None] | 0 | [0.0003, 0.2268] | False |
| `ollama:qwen3.5:9b:criteria:max_risk` | 0.5668 | [0.4892, 0.6421] | None | [None, None] | 0 | [-0.1357, 0.1145] | False |
| `ollama:qwen3.5:9b:criteria:mean_risk` | 0.6839 | [0.6074, 0.7642] | None | [None, None] | 0 | [-0.009, 0.2211] | False |

## litellm_proxy/neulab/claude-sonnet-4-5-20250929

190 trajectories on 190 tasks, 56 unsafe.

| signal | AUROC | 95% CI | within-task | 95% CI | mixed tasks | Δ vs task identity (95% CI) | passes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `n_actions` | 0.4927 | [0.4044, 0.5769] | None | [None, None] | 0 | [-0.2511, 0.0012] |  |
| `keyword_count` | 0.4861 | [0.413, 0.5611] | None | [None, None] | 0 | [-0.2334, -0.0244] |  |
| `task_identity_oof` | 0.6149 | [0.5294, 0.7059] | None | [None, None] | 0 |  |  |
| `ollama:qwen3.5:9b:count` | 0.5444 | [0.4623, 0.6219] | None | [None, None] | 0 | [-0.1823, 0.0381] | False |
| `ollama:qwen3.5:9b:fraction` | 0.574 | [0.4908, 0.6531] | None | [None, None] | 0 | [-0.155, 0.0688] | False |
| `ollama:qwen3.5:9b:max_risk` | 0.5713 | [0.4856, 0.6557] | None | [None, None] | 0 | [-0.1574, 0.0687] | False |
| `ollama:qwen3.5:9b:mean_risk` | 0.5935 | [0.5044, 0.6816] | None | [None, None] | 0 | [-0.1322, 0.0902] | False |
| `ollama:qwen3.5:9b:policy:count` | 0.5193 | [0.436, 0.6047] | None | [None, None] | 0 | [-0.2133, 0.02] | False |
| `ollama:qwen3.5:9b:policy:fraction` | 0.534 | [0.4445, 0.62] | None | [None, None] | 0 | [-0.1935, 0.0352] | False |
| `ollama:qwen3.5:9b:policy:max_risk` | 0.5442 | [0.4605, 0.6273] | None | [None, None] | 0 | [-0.1859, 0.0459] | False |
| `ollama:qwen3.5:9b:policy:mean_risk` | 0.5653 | [0.4795, 0.6505] | None | [None, None] | 0 | [-0.1628, 0.0652] | False |
| `ollama:qwen3.5:9b:criteria:count` | 0.5921 | [0.5087, 0.6776] | None | [None, None] | 0 | [-0.1466, 0.106] | False |
| `ollama:qwen3.5:9b:criteria:fraction` | 0.6307 | [0.5446, 0.7158] | None | [None, None] | 0 | [-0.1117, 0.1401] | False |
| `ollama:qwen3.5:9b:criteria:max_risk` | 0.5966 | [0.5176, 0.6735] | None | [None, None] | 0 | [-0.1413, 0.0987] | False |
| `ollama:qwen3.5:9b:criteria:mean_risk` | 0.6422 | [0.5582, 0.7255] | None | [None, None] | 0 | [-0.1008, 0.1479] | False |
