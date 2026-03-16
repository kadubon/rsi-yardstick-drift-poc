# v2 Summary

v2 was added because v1 did not clearly show held-out ruler-drift-only binary admission flips for the same frozen outputs.

Methodological changes in v2:

- explicit calibration split
- explicit held-out evaluation split
- locked drifted proxy ruler selected on calibration only
- item-level same-output flip analysis
- separate reporting of score drift versus binary admission drift

Current local run tag: `20260316T085319Z`

Primary v2 artifacts:

- [../result_summary.md](../result_summary.md)
- [../results/v2/summaries/v2_condition_summary__20260316T085319Z.md](../results/v2/summaries/v2_condition_summary__20260316T085319Z.md)
- [../results/v2/analysis/admission_flips__ruler_drift_only_v2__20260316T085319Z.jsonl](../results/v2/analysis/admission_flips__ruler_drift_only_v2__20260316T085319Z.jsonl)
- [../results/v2/figures/v2_condition_summary__20260316T085319Z.svg](../results/v2/figures/v2_condition_summary__20260316T085319Z.svg)

The scientifically important bottom line for this run is simple:

- calibration produced a nonzero fail-to-pass flip on the calibration split
- held-out evaluation showed score drift but **no held-out fail-to-pass admission flips**

So this v2 run does not support the stronger claim that the locked drifted ruler more-admitted the same frozen outputs on the held-out split. That negative result is preserved in the root summary rather than hidden.
