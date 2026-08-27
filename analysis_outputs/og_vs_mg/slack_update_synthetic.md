*og-OAS vs new synthetic corpus — comparison update (offline)*
• Headline: *og* 359 human-written v3 tasks vs *synthetic* 75 (15 v4 + 60 v5). v4/v5 are one synthetic side, not separate cohorts.
• Within-set Jaccard: og 0.088 vs synthetic combined 0.078 (internal: v4 0.244, v5 0.077).
• Empty graders: og 54/359 (15.0%); synthetic 0/75.
• Trajectories: og real baselines median 12.5 actions vs 150 synthetic pairs (median 11 actions — constructed, not rollouts).
• v5 seed triage: 75 generated / 18 covered / 7 skipped (mechanism taxonomy).
• Real model rollouts on synthetic tasks still blocked (LiteLLM proxy down). Full report: `analysis_outputs/og_vs_mg/og_vs_synthetic_report.md`.