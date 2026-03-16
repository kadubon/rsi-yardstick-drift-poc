# Result Summary

## Scope

This report summarizes the local PoC v3 run for:

K. Takahashi, *Recursive Self-Improvement Stability under Endogenous Yardstick Drift* (2026), DOI: [10.5281/zenodo.19044634](https://doi.org/10.5281/zenodo.19044634)

This run is illustrative rather than definitive. It is a lightweight local experiment on a small handcrafted task set. It does not prove the paper.

Experiment tag: `20260316T093356Z`

Models:

- `gemma3:1b`
- `gemma3:4b`

Decoding settings:

- `temperature = 0`
- `top_p = 1`
- `num_predict = 96`
- `seed = 7`

## Why v3 Was Added

v1 was useful for showing proxy-gaming versus solver-change contrasts.

v2 improved the methodology by separating calibration from held-out evaluation, but it still did **not** produce held-out same-output binary admission flips under ruler drift only. The v2 failure also exposed a prompt-contract confound: one shared neutral prompt let relation-label instructions leak into arithmetic and extraction behavior, especially for the 4B leg.

v3 therefore added:

- task-conditioned prompt contracts
- the same conservative strict verifier
- a broader deterministic drift-candidate family
- a clearer calibration objective
- explicit separation of `proxy_admission_rate` from `proxy_mean_item_score`

## Methodology

v3 used:

- `data/v3/tasks_v3.jsonl`
- `data/v3/task_splits_v3.json`
- `data/v3/baseline_proxy_v3.json`
- `data/v3/drift_candidate_axes_v3.json`

Category-conditioned prompt contracts were used for:

- arithmetic
- extraction
- relation / NLI

The strict metric remained conservative:

- JSON object parseability
- required string-field schema
- exact final-answer match
- evidence-span presence in `support` when evidence spans were defined

Calibration used only `baseline_1b_v3` outputs from the calibration split. Candidate drifted rulers were scored by a transparent objective that rewarded:

- calibration fail->pass flips
- low pass->fail counts
- lower calibration admission inflation
- category coverage
- rescue diversity across proxy features

The held-out split was not used for candidate selection.

## Calibration Outcome

Calibration locked `drifted_proxy_v4`.

Observed calibration result:

- baseline proxy admission rate: `0.4286`
- drifted proxy admission rate: `0.4762`
- calibration fail->pass flips: `1`
- calibration pass->fail flips: `0`
- calibration proxy mean-item-score delta: `0.0238`

The calibration flip came from one extraction item.

## Held-Out Ruler-Drift Test

The main v3 target was the held-out comparison between:

- `baseline_1b_v3` under `baseline_proxy_v3`
- the exact same frozen outputs under `drifted_proxy_v4`

Held-out observed result:

- baseline strict score: `0.2857`
- baseline proxy admission rate: `0.4762`
- baseline proxy mean item score: `0.4619`
- ruler-drift-only strict score: `0.2857`
- drifted proxy admission rate: `0.4762`
- drifted proxy mean item score: `0.4810`
- held-out fail->pass flips: `0`
- held-out pass->fail flips: `0`

This means:

- held-out proxy score drift was observed
- held-out binary admission drift was **not** observed

So, on this held-out split, v3 still does **not** support the stronger claim that the same frozen outputs were more-admitted in binary terms under the drifted ruler.

## Condition-Level Results By Split

### Calibration split

| condition | proxy ruler | strict_score | proxy_admission_rate | proxy_mean_item_score | proxy_admitted_count | strict_confirmed_count | challenge_failure_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_1b_v3 | baseline_proxy_v3 | 0.2381 | 0.4286 | 0.4524 | 9 | 4 | 5 |
| baseline_1b_v3 | drifted_proxy_v4 | 0.2381 | 0.4762 | 0.4762 | 10 | 5 | 5 |
| ruler_drift_only_v3 | drifted_proxy_v4 | 0.2381 | 0.4762 | 0.4762 | 10 | 5 | 5 |
| proxy_gaming_1b_v3 | baseline_proxy_v3 | 0.2857 | 0.6190 | 0.7952 | 13 | 6 | 7 |
| proxy_gaming_1b_v3 | drifted_proxy_v4 | 0.2857 | 0.9048 | 0.8619 | 19 | 6 | 13 |
| real_model_change_4b_v3 | baseline_proxy_v3 | 0.5714 | 0.8095 | 0.8048 | 17 | 12 | 5 |
| real_model_change_4b_v3 | drifted_proxy_v4 | 0.5714 | 0.8095 | 0.8238 | 17 | 12 | 5 |

### Held-out evaluation split

| condition | proxy ruler | strict_score | proxy_admission_rate | proxy_mean_item_score | proxy_admitted_count | strict_confirmed_count | challenge_failure_count |
| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_1b_v3 | baseline_proxy_v3 | 0.2857 | 0.4762 | 0.4619 | 10 | 6 | 4 |
| baseline_1b_v3 | drifted_proxy_v4 | 0.2857 | 0.4762 | 0.4810 | 10 | 6 | 4 |
| ruler_drift_only_v3 | drifted_proxy_v4 | 0.2857 | 0.4762 | 0.4810 | 10 | 6 | 4 |
| proxy_gaming_1b_v3 | baseline_proxy_v3 | 0.0952 | 0.6190 | 0.8619 | 13 | 2 | 11 |
| proxy_gaming_1b_v3 | drifted_proxy_v4 | 0.0952 | 0.9524 | 0.9095 | 20 | 2 | 18 |
| real_model_change_4b_v3 | baseline_proxy_v3 | 0.6190 | 0.8095 | 0.8381 | 17 | 13 | 4 |
| real_model_change_4b_v3 | drifted_proxy_v4 | 0.6190 | 0.8095 | 0.8429 | 17 | 13 | 4 |

## Main Observations

### 1. The intended held-out admission-flip effect was still not observed

This remains the most important scientific result.

Calibration found one fail->pass flip, but held-out evaluation found:

- fail->pass flips: `0`
- pass->fail flips: `0`

Therefore, the local v3 run still does **not** support the stronger held-out claim that the drifted ruler more-admitted the same frozen outputs in binary terms.

### 2. Score drift and admission drift remain meaningfully different

Held-out `proxy_mean_item_score` did increase under the drifted ruler by `0.0190`, even though held-out binary admissions did not change.

This is a useful negative result: score drift can be present without admission drift.

### 3. Proxy gaming remained visible

On the held-out split:

- `proxy_gaming_1b_v3` strict score was `0.0952`
- baseline proxy admission rate was `0.6190`
- drifted proxy admission rate was `0.9524`
- challenge failures rose to `11` under the baseline proxy and `18` under the drifted proxy

So the subtler v3 gaming prompt still created substantial cheap-ruler gains without needing overt JSON sabotage.

### 4. The 4B model-change leg became more interpretable than v2

This is the main positive methodological change from v3.

In v2, the 4B comparison was hard to interpret because the shared prompt often induced relation labels on non-relation tasks. In v3, that specific cross-category failure mode did not dominate the run.

Observed held-out comparison:

- `baseline_1b_v3` strict score: `0.2857`
- `real_model_change_4b_v3` strict score: `0.6190`

Per-category held-out strict scores for `real_model_change_4b_v3` were:

- arithmetic: `0.1429`
- extraction: `0.8571`
- relation: `0.8571`

So the 4B leg became more interpretable, even though arithmetic remained noisy because some outputs used non-string JSON scalars, some arithmetic answers were simply wrong, and one arithmetic item was truncated.

### 5. The main negative result still survives the methodological cleanup

Even after:

- task-conditioned prompt contracts
- broader proxy-drift candidates
- a clearer calibration objective

the held-out same-output admission-flip effect still did not appear in this local run.

That suggests the limitation is not resolved merely by modest prompt and proxy redesign.

## Overall Interpretation

The scientifically conservative reading is:

- v3 improved the internal validity of the PoC relative to v2
- v3 made the 4B model-change leg meaningfully easier to interpret
- v3 again separated proxy score drift from binary admission drift
- v3 still did **not** observe held-out same-output admission flips under ruler drift only

So, in this lightweight PoC, the held-out evidence remains mixed:

- it supports the importance of distinguishing proxy-score movement from admission changes
- it supports the usefulness of delayed audit for separating proxy admissions from strict confirmation
- it does not support the stronger held-out claim that the drifted ruler increased binary admissions for the same frozen outputs

## Explicit Answers To The Main v3 Questions

Was the held-out ruler-drift-only binary admission-flip effect actually observed?

**No.**

On the held-out evaluation split for this local v3 run:

- same-output proxy score drift was observed
- same-output binary admission drift was not observed

Did the 4B genuine-improvement leg become more interpretable after the prompt-contract fix?

**Yes, relative to v2.**

The v3 task-conditioned prompts removed the dominant v2 label-leakage failure mode, and the 4B held-out strict score increased substantially above the baseline 1B held-out strict score. That makes the model-change leg more interpretable in this lightweight PoC, even though arithmetic behavior remained imperfect.

## Limitations

- This is still a lightweight PoC.
- It is not a full recursive self-improvement loop.
- The dataset is small and handcrafted.
- Results are model-specific and local-environment-sensitive.
- Prompt/verifier contracts remain an important design variable.
- Proxy rulers are illustrative, not canonical.
- Calibration succeeded on the calibration split but did not generalize to held-out admission flips.

## Output Artifacts

Version summaries:

- [docs/v1_result_summary.md](docs/v1_result_summary.md)
- [docs/v2_summary.md](docs/v2_summary.md)
- [docs/v3_summary.md](docs/v3_summary.md)
- [docs/v3_methodology.md](docs/v3_methodology.md)

v3 summaries:

- [results/v3/summaries/v3_condition_summary__20260316T093356Z.csv](results/v3/summaries/v3_condition_summary__20260316T093356Z.csv)
- [results/v3/summaries/v3_condition_summary__20260316T093356Z.md](results/v3/summaries/v3_condition_summary__20260316T093356Z.md)
- [results/v3/summaries/v3_category_summary__20260316T093356Z.csv](results/v3/summaries/v3_category_summary__20260316T093356Z.csv)
- [results/v3/summaries/v3_category_summary__20260316T093356Z.md](results/v3/summaries/v3_category_summary__20260316T093356Z.md)
- [results/v3/figures/v3_condition_summary__20260316T093356Z.svg](results/v3/figures/v3_condition_summary__20260316T093356Z.svg)

Calibration and analysis artifacts:

- [results/v3/calibration/locked_drifted_proxy_v4__20260316T093356Z.json](results/v3/calibration/locked_drifted_proxy_v4__20260316T093356Z.json)
- [results/v3/calibration/calibration_search__20260316T093356Z.jsonl](results/v3/calibration/calibration_search__20260316T093356Z.jsonl)
- [results/v3/analysis/admission_flips__ruler_drift_only_v3__20260316T093356Z.jsonl](results/v3/analysis/admission_flips__ruler_drift_only_v3__20260316T093356Z.jsonl)
- [results/v3/analysis/near_miss_rescues__20260316T093356Z.jsonl](results/v3/analysis/near_miss_rescues__20260316T093356Z.jsonl)

## Closing Framing

This PoC series does not establish the full ruler-drift-only admission effect on held-out data.

What it does establish is that proxy-score movement, proxy-gaming, strict-confirmed improvement, and held-out binary admission drift are different phenomena and must be separated experimentally.
