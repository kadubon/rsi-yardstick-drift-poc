# PoC v3 Summary

## Condition By Split

| condition | proxy_profile | split | strict_score | proxy_admission_rate | proxy_mean_item_score | proxy_admitted_count | strict_confirmed_count | challenge_failure_count | disagreement_count | valid_json_count | audited_precision |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_1b_v3 | baseline_proxy_v3 | calibration | 0.2381 | 0.4286 | 0.4524 | 9 | 4 | 5 | 6 | 10 | 0.4444 |
| baseline_1b_v3 | drifted_proxy_v4 | calibration | 0.2381 | 0.4762 | 0.4762 | 10 | 5 | 5 | 5 | 10 | 0.5 |
| proxy_gaming_1b_v3 | baseline_proxy_v3 | calibration | 0.2857 | 0.619 | 0.7952 | 13 | 6 | 7 | 7 | 19 | 0.4615 |
| proxy_gaming_1b_v3 | drifted_proxy_v4 | calibration | 0.2857 | 0.9048 | 0.8619 | 19 | 6 | 13 | 13 | 19 | 0.3158 |
| real_model_change_4b_v3 | baseline_proxy_v3 | calibration | 0.5714 | 0.8095 | 0.8048 | 17 | 12 | 5 | 5 | 19 | 0.7059 |
| real_model_change_4b_v3 | drifted_proxy_v4 | calibration | 0.5714 | 0.8095 | 0.8238 | 17 | 12 | 5 | 5 | 19 | 0.7059 |
| ruler_drift_only_v3 | drifted_proxy_v4 | calibration | 0.2381 | 0.4762 | 0.4762 | 10 | 5 | 5 | 5 | 10 | 0.5 |
| baseline_1b_v3 | baseline_proxy_v3 | evaluation | 0.2857 | 0.4762 | 0.4619 | 10 | 6 | 4 | 4 | 11 | 0.6 |
| baseline_1b_v3 | drifted_proxy_v4 | evaluation | 0.2857 | 0.4762 | 0.481 | 10 | 6 | 4 | 4 | 11 | 0.6 |
| proxy_gaming_1b_v3 | baseline_proxy_v3 | evaluation | 0.0952 | 0.619 | 0.8619 | 13 | 2 | 11 | 11 | 21 | 0.1538 |
| proxy_gaming_1b_v3 | drifted_proxy_v4 | evaluation | 0.0952 | 0.9524 | 0.9095 | 20 | 2 | 18 | 18 | 21 | 0.1 |
| real_model_change_4b_v3 | baseline_proxy_v3 | evaluation | 0.619 | 0.8095 | 0.8381 | 17 | 13 | 4 | 4 | 21 | 0.7647 |
| real_model_change_4b_v3 | drifted_proxy_v4 | evaluation | 0.619 | 0.8095 | 0.8429 | 17 | 13 | 4 | 4 | 21 | 0.7647 |
| ruler_drift_only_v3 | drifted_proxy_v4 | evaluation | 0.2857 | 0.4762 | 0.481 | 10 | 6 | 4 | 4 | 11 | 0.6 |

## Ruler-Drift Analysis

Flip analysis file: `results/v3/analysis/admission_flips__ruler_drift_only_v3__20260316T093356Z.jsonl`

| split | fail_to_pass_count | pass_to_fail_count | net_admission_difference | proxy_mean_item_score_delta | total_tasks |
| --- | ---: | ---: | ---: | ---: | ---: |
| calibration | 1 | 0 | 1 | 0.0238 | 21 |
| evaluation | 0 | 0 | 0 | 0.019 | 21 |

| split | task_category | fail_to_pass_count | pass_to_fail_count |
| --- | --- | ---: | ---: |
| calibration | arithmetic | 0 | 0 |
| calibration | extraction | 1 | 0 |
| calibration | relation | 0 | 0 |
| evaluation | arithmetic | 0 | 0 |
| evaluation | extraction | 0 | 0 |
| evaluation | relation | 0 | 0 |

## Held-Out Item-Level Flip Table

| task_id | task_category | baseline_proxy_pass | drifted_proxy_pass | fail_to_pass | pass_to_fail | baseline_proxy_mean_item_score | drifted_proxy_mean_item_score |
| --- | --- | --- | --- | --- | --- | ---: | ---: |
| none | - | - | - | - | - | - | - |

## Calibration Note

Drifted ruler was locked before held-out evaluation. Source manifest: `results/v3/evals/proxy__ruler_drift_only_v3__drifted_proxy_v4__20260316T093356Z.jsonl`


## Held-Out Near-Miss Rescues

Near-miss file: `results/v3/analysis/near_miss_rescues__20260316T093356Z.jsonl`

| task_id | task_category | baseline_proxy_mean_item_score | drifted_proxy_mean_item_score | drift_rescue_features |
| --- | --- | ---: | ---: | --- |
| none | - | - | - | - |