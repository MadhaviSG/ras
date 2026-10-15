# Credit assignment

**Annotator:** `gateway:gemini/gemini-2.5-pro`

**Sample size:** 32 trajectories (628 steps).

**Real model called: yes.** Completer id: `gateway:gemini/gemini-2.5-pro`.

Frontier-hosted annotator via the CMU ai-gateway on the validated-outcome sample (16 unsafe trajectories whose graders start safe, plus a matched validated-safe sample). The earlier 70-trajectory study is contaminated. Still a candidate label set, not ground truth.

Source trajectories: `/home/mgulavan/ras/analysis_outputs/real_rollout_sft/trajectories.decontaminated.jsonl`.

Assignments written: 32.

## Did the annotator just reproduce the sink rule?

- proposed-high steps: 36
- of those that touch a sink: 23
- of those that do not: 13
- fraction of proposed-high that are sinks: 0.6388888888888888
- looks_like_sink_rule: False

## Comparison versus live baselines

```
real_llm_called: True
completer: gateway:gemini/gemini-2.5-pro
n_trajectories: 32
n_steps: 628

proposed labels vs live baselines (y_true=baseline, y_pred=proposed)
  vs sink_outcome_oracle: n=628 acc=0.892 P=0.639 R=0.295 F1=0.404 tp=23 fp=13 tn=537 fn=55
  vs keyword: n=628 acc=0.909 P=0.222 R=0.216 F1=0.219 tp=8 fp=28 tn=563 fn=29
  vs sink_presence: n=628 acc=0.748 P=0.639 R=0.137 F1=0.225 tp=23 fp=13 tn=447 fn=145

trajectory-outcome AUROC (grader rule_based)
  task_identity (out-of-fold): 0.887
  task_identity (in-sample, memorises task id): 0.996
  action-level (max credit): 0.535
  action-level beats task_identity: False

online rows (cummax) — * = required baseline
  keyword *: 16 harmful, prefix-AUROC @0.25=0.562  @0.50=0.531  @0.75=0.562  @1.00=0.562
  sink_outcome_oracle *: 16 harmful, prefix-AUROC @0.25=0.688  @0.50=0.844  @0.75=0.969  @1.00=0.969
  task_identity *: 16 harmful, prefix-AUROC @0.25=0.996  @0.50=0.996  @0.75=0.996  @1.00=0.996
  llm_credit: 16 harmful, prefix-AUROC @0.25=0.562  @0.50=0.719  @0.75=0.875  @1.00=1.000

notes
  - sink_outcome_oracle, keyword, and task_identity are the live safety_monitor.online.baselines scorers; this file does not re-implement those formulas.
  - llm_credit is the completer's proposed per-action labels, not ground truth.
  - The task_identity row below is fitted in-sample, as an upper bound on task-prior leakage. The head-to-head AUROC above is out-of-fold, because an in-sample probe memorises the task id and wins by default.
```

The `sink_outcome_oracle`, `keyword`, and `task_identity` rows come from `safety_monitor.online.baselines`. Proposed labels are a candidate set, not ground truth. If they match the sink-outcome oracle they did not add action-level signal.
