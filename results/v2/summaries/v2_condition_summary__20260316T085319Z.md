# PoC v2 Summary

## Condition By Split

| condition | proxy_profile | split | strict_score | proxy_score | binary_admission_count | strict_confirmed_count | challenge_failure_count | disagreement_count | audited_precision |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_1b_v2 | baseline_proxy_v2 | calibration | 0.2778 | 0.7222 | 13 | 5 | 8 | 8 | 0.3846 |
| proxy_gaming_1b_v2 | baseline_proxy_v2 | calibration | 0.2778 | 0.5 | 9 | 3 | 6 | 8 | 0.3333 |
| proxy_gaming_1b_v2 | drifted_proxy_v3 | calibration | 0.2778 | 0.6111 | 11 | 5 | 6 | 6 | 0.4545 |
| real_model_change_4b_v2 | baseline_proxy_v2 | calibration | 0.1667 | 0.8889 | 16 | 3 | 13 | 13 | 0.1875 |
| real_model_change_4b_v2 | drifted_proxy_v3 | calibration | 0.1667 | 0.9444 | 17 | 3 | 14 | 14 | 0.1765 |
| ruler_drift_only_v2 | drifted_proxy_v3 | calibration | 0.2778 | 0.7778 | 14 | 5 | 9 | 9 | 0.3571 |
| baseline_1b_v2 | baseline_proxy_v2 | evaluation | 0.3333 | 0.8333 | 15 | 6 | 9 | 9 | 0.4 |
| proxy_gaming_1b_v2 | baseline_proxy_v2 | evaluation | 0.2222 | 0.5556 | 10 | 4 | 6 | 6 | 0.4 |
| proxy_gaming_1b_v2 | drifted_proxy_v3 | evaluation | 0.2222 | 0.6667 | 12 | 4 | 8 | 8 | 0.3333 |
| real_model_change_4b_v2 | baseline_proxy_v2 | evaluation | 0.2222 | 0.8889 | 16 | 4 | 12 | 12 | 0.25 |
| real_model_change_4b_v2 | drifted_proxy_v3 | evaluation | 0.2222 | 1.0 | 18 | 4 | 14 | 14 | 0.2222 |
| ruler_drift_only_v2 | drifted_proxy_v3 | evaluation | 0.3333 | 0.8333 | 15 | 6 | 9 | 9 | 0.4 |

## Ruler-Drift Flip Analysis

Flip analysis file: `results\v2\analysis\admission_flips__ruler_drift_only_v2__20260316T085319Z.jsonl`

| split | fail_to_pass_count | pass_to_fail_count | mean_score_difference | total_tasks |
| --- | ---: | ---: | ---: | ---: |
| calibration | 1 | 0 | 0.1031 | 18 |
| evaluation | 0 | 0 | 0.1037 | 18 |

| split | task_category | fail_to_pass_count | pass_to_fail_count |
| --- | --- | ---: | ---: |
| calibration | arithmetic_exact | 1 | 0 |
| calibration | passage_extraction | 0 | 0 |
| calibration | passage_nli | 0 | 0 |
| evaluation | arithmetic_exact | 0 | 0 |
| evaluation | passage_extraction | 0 | 0 |
| evaluation | passage_nli | 0 | 0 |

## Calibration Note

Drifted ruler was locked before held-out evaluation. Source manifest: `results\v2\evals\proxy__ruler_drift_only_v2__drifted_proxy_v3__20260316T085319Z.jsonl`
