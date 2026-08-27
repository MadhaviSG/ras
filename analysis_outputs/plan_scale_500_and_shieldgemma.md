# Plan: scale synthetic OAS to 500 tasks, ShieldGemma zero-shot + SFT, og-vs-mg validation

Status: draft plan. Current corpus: 75 tasks (15 v4 + 60 v5) = 150 trajectories in
`analysis_outputs/synthetic_pairs/`. Target: 500 tasks = 1000 trajectories (1 safe + 1 unsafe per task).

## Ground truth this plan builds on

| Fact | Source |
|---|---|
| og (v3) = 359 human tasks; real rollouts: claude-sonnet-4.5 38.7% rule-unsafe (n=266), gpt-5-mini 43.3% (n=275) | `og_vs_mg/og_vs_synthetic_report.md` §2.1 |
| 15% of v3 graders are empty/no-op; synthetic graders 0% empty | same, §1 |
| Seed taxonomy: 8 outcomes × 5 mechanisms; 75/100 seeds generated, 7 skipped as narration-only | `v5_generated_tasks/seed_coverage.json` |
| Prior mock SFT overfit the generator: synthetic-holdout recall 1.0, v3 F1 0.064 → 0.046 | `qwen_sft/report.md` |
| No completed model rollouts on synthetic tasks (proxy was suspended) | `og_vs_synthetic_report.md` §4 |

Overfit-to-generator is the central risk. Every phase below carries a control for it.

---

## Phase 0 — Unblock and pin (prerequisite, ~1 day)

1. Confirm a working LLM endpoint for (a) rollout actors, (b) LLM judge, (c) seed drafting.
   The old `https://cmu.litellm.ai` proxy was suspended; validate a config with
   `uv run validate-cfg .llm_config/<cfg>.json` and one smoke rollout before anything else.
2. Confirm GPU access for ShieldGemma inference and LoRA SFT (2B model: 1×24 GB is enough;
   inference can run on CPU but slowly at 24k+ actions).
3. Download weights once, pin locally: `google/shieldgemma-2b` (the critic wrapper
   deliberately never downloads; set `SHIELDGEMMA_MODEL_PATH`).
4. Freeze the current 75-task corpus as `synthetic_pairs_v1` (already effectively frozen);
   all new work lands in a new versioned directory (`v6_*`), never mutating v4/v5 outputs.

## Phase 1 — Scale to 500 tasks (425 new), keeping the deterministic renderer

Hand-authoring 425 more `V5Seed`s at v5 quality is ~a person-month; do **LLM-drafted seeds,
machine-validated, deterministically rendered** instead. The renderer, grader synthesis and
replay validation stay exactly as in v5 — only seed authorship changes.

### 1a. Expand the seed grid (target ≈ 550 drafted → 425 shipped)

- Keep the 8×5 outcome×mechanism grid; add two stratification axes that og has and the
  current 75 underuse: **service surface** (filesystem-only / gitlab / rocketchat / owncloud /
  plane / multi-service — og is 62% no-hosted-service, synthetic only 47%) and
  **intent** (benign-user vs adversarial-NPC pressure).
- Fill each cell to ≥ 10 tasks (40 cells × ~12 avg = ~480, plus the existing 75 minus overlap).
- Recover the 7 skipped "narration-only" seeds by adding an artifact sink (the harmful
  recommendation must be *written* into a file/message a grader can keyword-match) — the
  `artifact_mediated_weak` gradeability class already exists for this.

### 1b. LLM-drafted seeds with a hard validation gate

Pipeline (new module `safety_monitor/synthesis/v6_author.py` + `v6_validate.py`):

1. **Draft**: prompt a strong model with 3 exemplar `V5Seed`s from the *same* outcome×mechanism
   cell + the data contract docstring from `v5_types.py`; ask for JSON matching the seed schema.
2. **Structural gate** (existing code): `validate_seed()` invariants — only `terminal`/
   `file_editor` actions, exactly one pivotal action in the harmful half, every `Effect`
   cross-checked against its command text, NPC-pressure turn minimums.
3. **Grader gate** (existing code): synthesize `evaluator_code` via `v5_graders`, then
   `v5_replay`: grader **must fire** on the harmful end state and **must not fire** on the
   safe end state. Reject otherwise. This keeps the 0%-empty-grader property.
4. **Novelty gate**: max pairwise Jaccard vs all existing task problem statements < 0.35
   (v4's templating leak showed up as Jaccard 0.244 mean; og is 0.088).
5. **Triage gate**: run the seed through the `already_covered` check against v3+v4+v5
   so we don't duplicate og tasks.
6. **Human spot-check**: review a random 10% sample per batch (≈ 45 tasks) for scenario
   plausibility; if >2 rejects in a batch of 50, review the whole batch.

Expect ~20–25% rejection; draft ~550 to ship 425.

### 1c. Render with v5 confound controls, plus one new one

Keep: length drawn from the real-corpus decile distribution; safe/harmful halves
byte-identical prefix + identical action count; ≥10 structural prose variants.

Add: **lexical decontamination** — no token n-gram (n≥6) shared between the pivotal-action
text and the task instruction across >3 tasks, so a critic can't learn "the phrase that
means unsafe". Check with a script, not by eye. This directly targets the failure mode the
mock-SFT run exposed.

### 1d. Ship

- `analysis_outputs/v6_synthetic_pairs/{trajectories,pairs,safety_trajectories}.jsonl`
  + `stats.json` + `report.md`, same schemas, `corpus: "v6"`.
- Re-run the merge to produce `synthetic_pairs/` v2 (500 tasks, 1000 trajectories, 500 pairs)
  with an updated manifest.
- Fixed **task-level splits at generation time** (salt like `qwen-sft`):
  train 350 / dev 75 / test 75, stratified by outcome×mechanism×service. Published in the
  manifest so every later experiment uses the same cut.

**Exit criteria**: 500 tasks; 0 empty graders; every pair passes replay; mean within-set
Jaccard ≤ 0.12 (og-comparable); all 40 grid cells ≥ 8 tasks.

## Phase 2 — og-OAS vs mg-OAS like-for-like comparison

Two questions, answered separately: **(Q1)** are the generated tasks the same *kind* of
benchmark? **(Q2)** do the same agents fail them at a different *rate*?

### 2a. Q1 — static equivalence (offline, extends `compare_og_mg.py`)

Rerun the existing report on og(359) vs mg(500), same metrics: within-set Jaccard,
problem-statement length, evaluator-code lines/kind, NPC prevalence + strategy-hint stats,
service surface, empty-grader rate. Add:

- **Cross-set nearest-neighbour Jaccard**: for each mg task, similarity to closest og task —
  distribution should show mg is *near* og space but not duplicating it (flag anything > 0.6).
- **Outcome-category distribution** og vs mg (χ² on the 8-way split; og categories inferred
  from checkpoint text keywords, documented as approximate).
- **Distinguishability probe**: train a bag-of-ngrams logistic classifier og-vs-mg on problem
  statements, 5-fold CV. AUROC near 0.5 = same kind of benchmark; report it either way —
  high AUROC with an inspectable coefficient list tells us exactly *what* gives mg away.

### 2b. Q2 — behavioral equivalence (needs proxy, the currently-missing half)

Rollouts, all with `security_analyzer: none` (passive), max-iter matched to og runs:

| Arm | Actor | Tasks | Runs |
|---|---|---|---|
| og reference | claude-sonnet-4.5 | reuse existing 266 completed | 0 new |
| og reference | gpt-5-mini | reuse existing 275 completed | 0 new |
| mg new | claude-sonnet-4.5 | 500 | 500 |
| mg new | gpt-5-mini | 500 | 500 |

Run mg in 3 waves (50 → 150 → 300) with a checkpoint after each: if wave-1 unsafe rate is
outside [15%, 75%] for either actor, stop and diagnose task realism before burning budget.

Scoring, identical for both sides:
- **Rule-based grader** (each task's `evaluator_code`) → primary unsafe/safe outcome.
- **LLM judge** with the same 4-level rubric used on og, same judge model for both sides,
  judged in one batch to avoid drift. Report judge–grader agreement (Cohen's κ) per side;
  a large κ gap between og and mg is itself a finding about grader style.

Analysis (`analysis_outputs/og_vs_mg_v2/`):
- Per-actor unsafe-rate contrast og vs mg with Wilson 95% CIs and two-proportion z-test.
  Power: og n≈270/actor vs mg n=500/actor detects ~9pp differences per actor at 0.8 power;
  pooled (og 541 vs mg 1000) detects ~6pp.
- **Stratified**: unsafe rate by outcome category, NPC-vs-no-NPC, service surface — a raw
  og-vs-mg gap may be composition, not difficulty. Report both raw and composition-adjusted
  (reweight mg strata to og's mix).
- Secondary: actions-to-unsafe, refusal/stop rate, judge-level distribution.

**Interpretation rule (decide now, before data)**: mg is "the same kind of benchmark" if
(a) the distinguishability AUROC story is benign, and (b) per-actor unsafe rates are within
±10pp of og *after* composition adjustment, and (c) actor *ranking* is preserved
(gpt-5-mini > claude on og; same ordering expected on mg). Outside that: mg measures
something related but not interchangeable — still usable for training (Phase 4), but mg
numbers don't get reported as OAS numbers.

## Phase 3 — Zero-shot ShieldGemma on OAS

Baseline before any finetuning, on **both** og and mg:

1. Weights local, `SHIELDGEMMA_MODEL_PATH` set; existing critic
   (`safety_monitor/critic/shieldgemma.py`) already implements the Yes/No policy-prompt
   scoring with an OAS policy.
2. **Offline scoring** (primary, cheap, reproducible): run the critic over recorded
   trajectories — og: the 2,575 v3 eval trajectories / 24,309 actions in
   `critic_training_pairs`; mg: the 1,000 synthetic trajectories.
   - Action-level: P/R/F1 on `high-unsafe` (og labels are weak supervision — say so).
   - Trajectory-level (headline): AUROC of aggregated critic score (max, count, rate — all
     three, as in `qwen_sft`) vs `role==harmful` / `rule_based` on og and vs the constructed
     label on mg.
   - Calibrate the Yes-probability **threshold on the mg dev split only**; report og at
     that fixed threshold.
3. **Online** (secondary, small): OAS runs with `security_analyzer: shieldgemma` on a
   50-task stratified mg subset + 50 og tasks × 1 actor → does the monitor actually reduce
   rule-based unsafe outcomes vs the passive arm, and at what
   false-block cost (blocks on safe trajectories)?
4. Comparison baselines so ShieldGemma's number means something: keyword zero-shot
   (already in `sft/backends.py`) and the prompted-LLM critic (`critic/prompted.py`).

**Exit criteria**: trajectory-level AUROC on og for {keyword, prompted-LLM, ShieldGemma
zero-shot} + a threshold frozen for the before/after comparison in Phase 5.

## Phase 4 — SFT an open-weight model on synthetic data

1. **Data**: one row per labeled action (existing `sft/data.py` format), from the mg train
   split only (350 tasks, ~700 trajectories, est. ~8k action rows). Real og data is
   **eval-only, firewalled** — same rule the qwen_sft run used; keep the leakage check
   (`train∩eval instance_ids == []`) in the report.
2. **Model**: ShieldGemma-2B + LoRA (r=16, lr 1e-4/2e-4, 2–3 epochs) as primary — it keeps
   Phase 3/5 an exact before/after on one architecture. Qwen2.5-1.5B/7B LoRA as a secondary
   arm through the existing `sft/experiment.py` path (now with a real GPU backend, not mock).
3. **Class imbalance**: ~4–6% positives; upweight positives or downsample negatives; tune
   only on the mg dev split.
4. **Anti-generator-overfit controls** (the mock run's lesson, built in ahead of time):
   - Model selection criterion = og-v3 trajectory AUROC on a small *selection slice*
     (300 og trajectories), NOT synthetic-holdout F1. Synthetic holdout is reported as a
     diagnostic only.
   - Train on **paraphrase-augmented** action text (LLM paraphrase of command narration,
     commands untouched) so the model can't key on renderer phrasing.
   - Early-stop on og-selection-slice AUROC.
   - Ablation grid: train on {v5-only 60, mg-350, mg-350+paraphrase} to measure whether
     more synthetic data actually transfers or just fits the generator harder.
5. Also fine-tune the trajectory-level aggregation threshold on mg dev.

**Go/no-go gate**: if og-selection AUROC after SFT ≤ zero-shot AUROC + 0.02, do not proceed
to Phase 5 claims; instead run the diagnosis loop (inspect top false positives on og,
check n-gram leakage between train rows and errors, revisit Phase 1c decontamination).

## Phase 5 — Finetuned model on OAS (before/after)

Mirror Phase 3 exactly, frozen thresholds from Phase 4:

- Offline: og 2,575-trajectory eval (minus the Phase-4 selection slice — report both with
  and without, but headline excludes it) + mg test split (75 tasks).
- Online: same 50+50 task subset, `security_analyzer: shieldgemma` with adapter.
- Headline table: {keyword, prompted-LLM, ShieldGemma zero-shot, ShieldGemma-SFT, Qwen-SFT}
  × {og action-F1, og trajectory-AUROC, mg-test AUROC, online unsafe-rate reduction,
  online false-block rate}.
- The og-vs-mg gap per model is the generalization story: a model that gains on mg-test but
  not on og learned the generator; gains on both = synthetic data transfers.

## Sequencing and effort

```
Phase 0  ──────► Phase 1 (seed drafting + validation, ~1.5–2 wks)
   │                 │
   │                 ├──► Phase 2a static comparison (offline, ~2 days, parallel)
   │                 └──► Phase 2b rollouts (1,000 runs, wave-gated, ~3–5 days wall clock)
   └──► Phase 3 zero-shot ShieldGemma (og part can start immediately, ~2–3 days)
                     │
Phase 1 + 3 ────► Phase 4 SFT (~3–4 days incl. ablations)
                     │
Phase 2b + 4 ───► Phase 5 before/after (~2–3 days)
```

Critical path ≈ 4 weeks. Phase 3-on-og and Phase 2a need nothing from Phase 1 and start now.

## Budget (rough)

- Seed drafting: 550 drafts × ~4k tok ≈ trivial (< $50 with a frontier model).
- Rollouts: 1,000 runs × 2 actors' historical cost profile — dominant LLM cost; wave gating
  caps the downside. Judge: ~2,000 trajectories × 1 call.
- GPU: 1×A10/24GB-class for ShieldGemma inference + LoRA; ~30–60 GPU-hours total.

## Risks

| Risk | Mitigation |
|---|---|
| SFT fits the generator, not safety (already observed once) | Phase 1c decontamination; paraphrase augmentation; og-based model selection; go/no-go gate |
| mg tasks too easy/hard → unsafe rate not comparable | Wave gating in 2b; composition-adjusted comparison; pre-registered interpretation rule |
| LLM-drafted seeds are subtly ungradeable | Replay gate: grader must fire on harmful and not on safe end state — mechanical, no judgement |
| Proxy suspended again mid-run | All offline work (1, 2a, 3-offline) proceeds; rollouts are resumable per-instance |
| og weak labels distort action-level metrics | Trajectory-level AUROC vs `role`/`rule_based` is the headline, action-level secondary |
