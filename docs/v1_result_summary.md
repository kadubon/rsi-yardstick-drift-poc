# v1 Result Summary

This file preserves a brief repository-local summary of the original v1 run.

v1 was useful for two things:

- showing a substantial strict/proxy gap under a cheap ruler
- showing a contrast between proxy-gaming behavior and a real model change

v1 was weaker on one key point:

- it did not clearly produce a held-out ruler-drift-only binary admission-flip effect for the same frozen outputs

Observed v1 condition-level results from the local run tagged `20260316T082441Z`:

| condition | strict score | proxy score | disagreement count | challenge-failure count |
| --- | ---: | ---: | ---: | ---: |
| baseline_1b_strict | 0.2963 | 0.6296 | 9 | 9 |
| ruler_drift_only | 0.2963 | 0.6296 | 9 | 9 |
| proxy_gaming_1b | 0.0741 | 0.5556 | 13 | 13 |
| real_model_change_4b | 0.7037 | 0.9630 | 7 | 7 |

Primary v1 artifacts:

- [results/summaries/condition_summary__20260316T082441Z.md](../results/summaries/condition_summary__20260316T082441Z.md)
- [results/figures/condition_summary__20260316T082441Z.svg](../results/figures/condition_summary__20260316T082441Z.svg)
- [results/audits/audit__baseline_1b_strict__20260316T082441Z.jsonl](../results/audits/audit__baseline_1b_strict__20260316T082441Z.jsonl)
- [results/audits/audit__ruler_drift_only__20260316T082441Z.jsonl](../results/audits/audit__ruler_drift_only__20260316T082441Z.jsonl)
- [results/audits/audit__proxy_gaming_1b__20260316T082441Z.jsonl](../results/audits/audit__proxy_gaming_1b__20260316T082441Z.jsonl)
- [results/audits/audit__real_model_change_4b__20260316T082441Z.jsonl](../results/audits/audit__real_model_change_4b__20260316T082441Z.jsonl)

Interpretation should remain conservative. v1 was illustrative rather than definitive, and v2 was added specifically to test the ruler-drift-only admission-flip question more carefully.
