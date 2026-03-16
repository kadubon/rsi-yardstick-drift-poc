# PoC v3 Summary

The local v3 run used task-conditioned prompt contracts, a conservative strict verifier, a broader family of drift-candidate proxy rulers, and calibration/held-out separation.

On this held-out split, `proxy_mean_item_score` drift was observed under `ruler_drift_only_v3`, but held-out same-output binary admission flips were not observed. Calibration produced `1` fail->pass flip; held-out evaluation produced `0`.

The 4B comparison became more interpretable than in v2. Held-out strict score rose from `0.2857` for `baseline_1b_v3` to `0.6190` for `real_model_change_4b_v3`, largely because the task-conditioned prompts removed the dominant v2 label-leakage failure mode. Arithmetic remained imperfect, so this should still be read as illustrative rather than definitive.

Primary artifacts:

- [../result_summary.md](../result_summary.md)
- [../results/v3/summaries/v3_condition_summary__20260316T093356Z.md](../results/v3/summaries/v3_condition_summary__20260316T093356Z.md)
- [../results/v3/summaries/v3_category_summary__20260316T093356Z.md](../results/v3/summaries/v3_category_summary__20260316T093356Z.md)
- [../results/v3/analysis/admission_flips__ruler_drift_only_v3__20260316T093356Z.jsonl](../results/v3/analysis/admission_flips__ruler_drift_only_v3__20260316T093356Z.jsonl)
- [../results/v3/figures/v3_condition_summary__20260316T093356Z.svg](../results/v3/figures/v3_condition_summary__20260316T093356Z.svg)
