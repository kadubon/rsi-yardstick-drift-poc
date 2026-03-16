# RSI Yardstick Drift PoC
This repository contains lightweight v1, v2, and v3 experiments on whether unchanged local-model outputs can look better under changed proxy rulers, and whether delayed strict audit separates that from genuine improvement.
In the current local v3 run, held-out proxy score drift was observed, but held-out same-output binary admission flips were not observed.
The v3 prompt-contract fix made the 4B comparison more interpretable than v2, but this repository still does not claim a definitive ruler-drift-only admission effect.

K. Takahashi, *Recursive Self-Improvement Stability under Endogenous Yardstick Drift* (2026), DOI: [10.5281/zenodo.19044634](https://doi.org/10.5281/zenodo.19044634)

The paper's core claim is not that larger models always win. The core claim is that apparent improvement can arise from ruler drift rather than solver improvement, and that replayable delayed audit can help separate those cases.

## Repository Status

The repository now contains three additive paths:

- `v1`: the original lightweight PoC
- `v2`: a calibration-and-held-out extension added because v1 did not clearly show ruler-drift-only causing more binary admissions on the same frozen outputs
- `v3`: a task-conditioned prompt-contract and broader proxy-drift extension added because v2 still did not produce held-out same-output admission flips

v1 and v2 artifacts remain intact. v3 lives under `data/v3/`, `prompts/v3/`, `scripts/v3/`, and `results/v3/`.

## What v1 Showed

v1 was useful for illustrating:

- strict/proxy divergence
- proxy-gaming behavior under a cheap ruler
- a model-change comparison that looked more favorable than proxy gaming

That was enough to make the general proxy-gaming versus genuine-improvement distinction plausible in a small PoC.

## What v2 Improved

v2 added three methodological corrections:

1. a calibration split
2. a locked drifted proxy ruler selected on calibration only
3. a held-out evaluation split for the actual ruler-drift test

v2 therefore made it possible to separate:

- calibration success
- held-out generalization
- score drift
- binary admission drift

## What v2 Still Failed To Show

v2 still did **not** show the main held-out ruler-drift-only effect clearly:

- the same frozen outputs receiving more binary proxy admissions under the drifted ruler on held-out items

The v2 run produced calibration flips and held-out score drift, but held-out fail->pass admission flips remained `0`.

## What v3 Changes

v3 was added because the v2 failure looked structural rather than accidental. The main v3 changes are:

1. task-conditioned prompt contracts instead of a single shared prompt
2. conservative strict-verifier alignment without weakening the main strict metric
3. a broader, explicit family of deterministic drift candidates
4. a more structured calibration objective that rewards fail->pass flips, low pass->fail counts, category coverage, and rescue diversity
5. explicit separation of `proxy_admission_rate` from `proxy_mean_item_score`

## Research Question

Can a text-only system look better because the ruler drifts, rather than because the solver becomes more correct?

This repository operationalizes that question with:

- a strict replayable metric intended to track conservative correctness
- one baseline cheap proxy ruler
- one calibration-locked drifted cheap proxy ruler
- a delayed strict audit layer

## Why Task-Conditioned Prompt Contracts Matter

The shared v2 prompt leaked relation-task label instructions into arithmetic and extraction behavior. In the local v2 run, the 4B model often answered arithmetic items with relation labels like `entails`.

v3 therefore separates solver contracts by category:

- arithmetic: `final_answer` must be only the exact scalar or symbolic answer
- extraction: `final_answer` must be only the exact extracted span
- relation: `final_answer` must be exactly one of `entails`, `contradicts`, or `insufficient`

This does not guarantee perfect behavior, but it removes a clear prompt/verifier confound from v2.

## What Counts As Ruler Drift Here

In this PoC, ruler drift means that the solver outputs are held fixed while the cheap proxy ruler changes.

In v3, `ruler_drift_only_v3` is exactly:

- the same frozen outputs from `baseline_1b_v3`
- no new generation
- strict evaluation unchanged
- proxy evaluation switched from `baseline_proxy_v3` to calibration-locked `drifted_proxy_v4`

## What Counts As Genuine Improvement Here

In this PoC, genuine improvement means better performance under the strict replayable verifier when the solver actually changes, rather than when only the ruler changes.

`real_model_change_4b_v3` is the corresponding comparison condition:

- solver changes from `gemma3:1b` to `gemma3:4b`
- the same category-conditioned neutral prompts are kept
- the strict verifier stays fixed

## Metrics

### Strict replayable metric

The main reported strict metric remains conservative and deterministic. It checks:

- JSON object parseability
- required string-field schema
- exact final-answer match
- evidence-span presence in `support` when evidence spans are defined

The main reported strict metric is not silently weakened in v3.

### Proxy rulers

v3 uses two deterministic cheap rulers:

1. `baseline_proxy_v3`
   A compact-answer, compact-support cheap ruler.
2. `drifted_proxy_v4`
   A calibration-locked, slightly more permissive cheap ruler selected from an explicit candidate family.

These proxy rulers are illustrative, not canonical.

### Naming distinction

v3 uses the following terminology consistently:

- `proxy_admission_rate`: fraction of items admitted by a proxy ruler
- `proxy_mean_item_score`: average normalized proxy feature score across items

This matters because score drift can occur even when binary admissions do not change.

## Delayed Audit

The delayed audit layer asks:

1. which items would be admitted by the proxy ruler?
2. among those, which survive the strict verifier?

For each condition and split, v3 reports:

- `strict_score`
- `proxy_admission_rate`
- `proxy_mean_item_score`
- `proxy_admitted_count`
- `strict_confirmed_count`
- `challenge_failure_count`
- `disagreement_count`
- `valid_json_count`
- per-category breakdown

Here, a challenge failure means an item that passed proxy admission but failed strict verification.

## Dataset

### v1

`data/tasks.jsonl` contains the original 27 deterministic tasks.

### v2

`data/v2/tasks_v2.jsonl` contains 36 deterministic tasks with calibration and evaluation splits in `data/v2/task_splits_v2.json`.

### v3

`data/v3/tasks_v3.jsonl` contains 42 deterministic tasks across:

- arithmetic exact-answer tasks
- structured extraction tasks
- relation / NLI tasks

`data/v3/task_splits_v3.json` fixes:

- a calibration split
- a held-out evaluation split

## Conditions

### v1 conditions

- `baseline_1b_strict`
- `ruler_drift_only`
- `proxy_gaming_1b`
- `real_model_change_4b`

### v2 conditions

- `baseline_1b_v2`
- `ruler_drift_only_v2`
- `proxy_gaming_1b_v2`
- `real_model_change_4b_v2`

### v3 conditions

- `baseline_1b_v3`
- `ruler_drift_only_v3`
- `proxy_gaming_1b_v3`
- `real_model_change_4b_v3`

For v3:

- `baseline_1b_v3` is evaluated under both proxy rulers
- `ruler_drift_only_v3` reuses the exact baseline outputs and evaluates them under the locked drifted proxy
- `proxy_gaming_1b_v3` is evaluated under both proxy rulers
- `real_model_change_4b_v3` is evaluated under both proxy rulers

## Prompt And Model Setup

The repository uses Ollama locally with these exact tags:

- `gemma3:1b`
- `gemma3:4b`

Text-only evaluation is used throughout. The default decoding settings are:

- `temperature = 0`
- `top_p = 1`
- `num_predict = 96`
- `seed = 7`
- `keep_alive = 0s`

## How To Run v3

### 1. Baseline 1B run

```powershell
python scripts/v3/run_solvers_v3.py --preset baseline_1b_v3 --experiment-tag YOUR_TAG
```

### 2. Calibrate the drifted proxy on calibration only

```powershell
python scripts/v3/calibrate_proxy_ruler_v3.py --baseline-raw results/v3/raw/baseline_1b_v3__YOUR_TAG.jsonl --experiment-tag YOUR_TAG
```

This writes:

- a locked drifted proxy profile
- a calibration search log

### 3. Run the other solver conditions

```powershell
python scripts/v3/run_solvers_v3.py --preset proxy_gaming_1b_v3 --experiment-tag YOUR_TAG
python scripts/v3/run_solvers_v3.py --preset real_model_change_4b_v3 --experiment-tag YOUR_TAG
```

### 4. Evaluate strict and proxy metrics

Use:

- `scripts/v3/eval_strict_v3.py`
- `scripts/v3/eval_proxy_v3.py`

### 5. Run audits and ruler-drift analyses

Use:

- `scripts/v3/run_audit_v3.py`
- `scripts/v3/analyze_flips_v3.py`
- `scripts/v3/near_miss_analysis_v3.py`

### 6. Summarize and plot

Use:

- `scripts/v3/summarize_v3.py`
- `scripts/v3/plot_v3.py`

All v3 outputs are timestamped and written under `results/v3/`. Raw outputs are never overwritten silently.

## Current Local Summaries

Current root summary:

- [result_summary.md](result_summary.md)

Version-specific summaries:

- [docs/v1_result_summary.md](docs/v1_result_summary.md)
- [docs/v2_summary.md](docs/v2_summary.md)
- [docs/v3_summary.md](docs/v3_summary.md)
- [docs/v3_methodology.md](docs/v3_methodology.md)

Current v3 run artifacts:

- [results/v3/summaries/v3_condition_summary__20260316T093356Z.md](results/v3/summaries/v3_condition_summary__20260316T093356Z.md)
- [results/v3/summaries/v3_category_summary__20260316T093356Z.md](results/v3/summaries/v3_category_summary__20260316T093356Z.md)
- [results/v3/analysis/admission_flips__ruler_drift_only_v3__20260316T093356Z.jsonl](results/v3/analysis/admission_flips__ruler_drift_only_v3__20260316T093356Z.jsonl)
- [results/v3/figures/v3_condition_summary__20260316T093356Z.svg](results/v3/figures/v3_condition_summary__20260316T093356Z.svg)

## Scientific Honesty

This repository is illustrative rather than definitive.

It does **not** claim to:

- prove the paper by experiment
- solve recursive self-improvement safety
- establish a canonical proxy ruler

The correct reading is:

- if a pattern appears, it may support the paper's distinction between apparent improvement and genuine improvement
- if a pattern does **not** appear on the held-out split, that negative result should be reported plainly

## Limitations

- This is still a lightweight PoC.
- It is not a full recursive self-improvement loop.
- The dataset is small and handcrafted.
- Results remain model-specific and local-environment-sensitive.
- Prompt/verifier contracts remain an important design variable.
- Proxy rulers are illustrative, not canonical.
- The local v3 run still did not produce held-out same-output admission flips.

## Security And File Hygiene

- Human-facing documentation uses relative repository paths only.
- Raw outputs are saved in versioned JSONL files.
- Summaries are saved in CSV and Markdown.
- Results log model tags, timestamps, prompts, decoding settings, and task ids.
- The scripts avoid silent overwrites.
- The committed result artifacts use relative repository paths rather than local absolute paths.
