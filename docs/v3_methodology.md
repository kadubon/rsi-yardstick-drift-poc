# PoC v3 Methodology Note

## Why v3 Was Added

v2 added calibration and held-out separation, which was methodologically important. However, the local v2 run still failed to produce held-out same-output binary admission flips under ruler drift only.

The v2 run also exposed a prompt-scope confound: one shared prompt let relation-task label instructions leak into arithmetic and extraction behavior, especially for the 4B leg.

## What v3 Changes

v3 changes four things directly:

1. task-conditioned prompt contracts
2. a broader deterministic drift-candidate family
3. a more structured calibration objective
4. explicit reporting of `proxy_admission_rate` versus `proxy_mean_item_score`

## Task-Conditioned Prompt Contracts

v3 separates prompt templates by category:

- arithmetic
- extraction
- relation

This does not weaken the strict verifier. Instead, it aligns solver instructions with the verifier so that failure modes are less confounded by cross-category instruction leakage.

## Strict Verifier

The main reported strict metric remains conservative:

- JSON object parseability
- required string-field schema
- exact final-answer match
- evidence-span presence when evidence spans are defined

No relaxed strict metric replaces the main reported one in v3.

## Proxy Rulers

`baseline_proxy_v3` is a cheap deterministic ruler with compact-answer and compact-support preferences.

`drifted_proxy_v4` is selected from an explicit candidate family that varies along interpretable axes such as:

- answer-length relaxation
- quoted or mildly prefixed answer tolerance
- support-length relaxation
- grounding-cue relaxation
- mild confidence weighting
- minimal-format weighting

The candidate axes are stored in:

- [../data/v3/drift_candidate_axes_v3.json](../data/v3/drift_candidate_axes_v3.json)

## Calibration Objective

Calibration uses only `baseline_1b_v3` outputs from the calibration split.

Candidates are ranked by an objective that rewards:

- fail->pass flips
- low pass->fail counts
- lower admission inflation beyond a ceiling
- category coverage
- rescue diversity

The held-out evaluation split is not used for candidate selection.

## Reporting Distinction

v3 separates:

- `proxy_admission_rate`
- `proxy_mean_item_score`

This matters because a drifted ruler can change average proxy scores without changing binary admissions.

## Reading The Local v3 Run

The local v3 run improved interpretability relative to v2, especially for the 4B comparison, but it still did **not** produce held-out same-output binary admission flips. That negative result should be read as part of the evidence, not as something to smooth away.
