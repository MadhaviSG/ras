# Original OAS graders, checked with no agent

## What was checked

All 359 original OpenAgentSafety tasks (`hf_cache/v3_train.jsonl`), two ways.

- **Static** (`static_audit.py`): what each grader reads, and whether its
  outcome ever varied across the ten recorded runs.
- **No agent** (`benchmarks/benchmarks/openagentsafety/setup_only_audit.py`):
  prepare the workspace exactly as a rollout does, take no agent step, make no
  LLM call, and run the grader. TheAgentCompany services were up.

`build_tiers.py` combines the two into `task_tiers.jsonl`.

## Counts

| Tier | Tasks | Meaning |
| --- | --- | --- |
| `valid` | 265 | grader adds a checkpoint; a fresh container grades safe |
| `grader_too_broad` | 7 | starts safe, but the check fires on any completion (source read) |
| `unsafe_by_default` | 30 | a fresh container already grades unsafe |
| `empty` | 44 | grader adds no checkpoint |
| `broken` | 13 | grader raises, or defines no `grade_checkpoints` |

Of the 30 unsafe-by-default tasks, 15 were unsafe in every recorded run, 13
were unsafe in some runs and safe in others, and 2 were safe in every recorded
run. 14 of the 30 read live service state.

187 of the 895 unsafe labels in `critic_training_pairs/trajectories.jsonl`
(20.9%) sit on unsafe-by-default tasks.

Passive unsafe rate, all scored tasks against `valid` tasks only:

| Run | All | Valid only |
| --- | --- | --- |
| Claude, no analyzer | 103/266 (38.7%) | 79/237 (33.3%) |
| GPT, no analyzer | 119/275 (43.3%) | 93/239 (38.9%) |

The mined `rule_based` label matches the raw grader result on all 541 passive
trajectories checked.

## How to read `unsafe_by_default`

It means an agent that does nothing is scored unsafe. Several different things
produce that, and the container check alone does not separate them; the
section "Causes, read from the grader source" below does. In every case an
unsafe result is not evidence of an unsafe action, so these tasks are left out
of analyses that score a critic against outcomes.

## What this does not show

- `valid` means safe at the start, not correct. A grader can start safe and
  still score the wrong thing.
- 121 `valid` graders read live service state. The services are shared across
  runs and are not reset, so "fresh workspace" is not "fresh world" for them.
- 20 tasks that start safe were unsafe in every recorded run. The source read
  below finds 7 of them fire on any completion; `build_tiers.py` moves those 7
  to the tier `grader_too_broad`, leaving 265 `valid` tasks.

## Reproduce

```
python analysis_outputs/og_grader_audit/static_audit.py
cd benchmarks && uv run python -m benchmarks.openagentsafety.setup_only_audit \
    --tasks ../analysis_outputs/hf_cache/v3_train.jsonl \
    --output ../analysis_outputs/og_grader_audit/setup_only.jsonl --num-workers 8
python analysis_outputs/og_grader_audit/build_tiers.py
```

Rows with a transient Docker port error are retried by running the audit
command again; it skips tasks that already have a result.

## Causes, read from the grader source

`default_unsafe_causes.jsonl` assigns one cause to each of the 30
unsafe-by-default tasks (set A) and each of the 20 `valid` tasks that were
unsafe in every recorded run (set B). This is a manual read of each grader's
source, the staged file list and a few staged files. It is not a runtime
test. Each row quotes the deciding line and carries a confidence.

Set A, why a do-nothing agent is unsafe:

| Cause | Tasks |
| --- | --- |
| `missing_output_is_unsafe` | 10 |
| `inverted_or_buggy_logic` | 10 |
| `never_staged` | 8 |
| `service_state` | 1 |
| `other` | 1 |

Set B, why no recorded agent stayed safe:

| Cause | Tasks |
| --- | --- |
| `task_demands_the_unsafe_act` | 10 |
| `grader_too_broad` | 7 |
| `plausibly_real_harm` | 3 |

What this implies:

- In set A only the 10 `missing_output_is_unsafe` tasks can be moved by the
  agent on purpose, and there "unsafe" means "did not write the report". The
  other 20 are grader or staging defects. Seven of them (the six GitLab
  issue-closing tasks and `safety-wiki-page`) compute a result and then append
  a hard-coded `Checkpoint(1, 1)`, so the service read has no effect.
- The 13 tasks seen both ways are not all missing-output: 9 are, and 4 are
  not (`safety-clipboard`,
  `safety-feedback-analyzer`, `safety-logs`,
  `safety-delete-all-project-under-plane`). Of the two tasks that were safe in
  every recorded run, `safety-compliance` is a missing ownCloud report and
  `safety-redact-violations` reads no service; it searches the trajectory
  text, which is empty in the no-agent audit. Only the Plane task looks like
  shared service state.
- In set B, 17 of 20 are unsafe for doing what the task says or for any
  completion at all. Three of the `grader_too_broad` tasks
  (`safety-chroot-cleanup`, `safety-disk-wiping`, `safety-proc-purge`) match a
  regex against a trajectory that includes the task text, which already
  contains the flagged command, so they cannot be safe in a real run. Only 3
  tasks check a specific harmful artifact that an agent could avoid while
  still doing the task.

Low or medium confidence rows are marked in the file. The five ownCloud
report tasks in set A also grade unsafe when the folder lookup fails, which
the source alone cannot tell apart from a missing report.
