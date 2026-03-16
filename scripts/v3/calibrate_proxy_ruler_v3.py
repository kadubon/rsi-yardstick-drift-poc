from __future__ import annotations

import argparse
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from common_v3 import (  # noqa: E402
    DEFAULT_BASELINE_PROXY_PATH,
    DEFAULT_CANDIDATE_AXES_PATH,
    DEFAULT_SPLITS_PATH,
    DEFAULT_TASKS_PATH,
    iter_records,
    load_json,
    load_jsonl,
    load_splits,
    load_tasks,
    make_output_path,
    relpath,
    score_proxy_profile,
    split_lookup,
    task_lookup,
    utc_now_iso,
    write_json,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Calibrate and lock drifted_proxy_v4 using only calibration-split baseline outputs.")
    parser.add_argument("--baseline-raw", required=True, type=pathlib.Path)
    parser.add_argument("--tasks", type=pathlib.Path, default=DEFAULT_TASKS_PATH)
    parser.add_argument("--splits", type=pathlib.Path, default=DEFAULT_SPLITS_PATH)
    parser.add_argument("--baseline-profile", type=pathlib.Path, default=DEFAULT_BASELINE_PROXY_PATH)
    parser.add_argument("--candidate-axes", type=pathlib.Path, default=DEFAULT_CANDIDATE_AXES_PATH)
    parser.add_argument("--experiment-tag", required=True)
    parser.add_argument("--output-profile", type=pathlib.Path)
    parser.add_argument("--output-search", type=pathlib.Path)
    return parser.parse_args()


def build_candidate_profiles(baseline_profile: dict[str, object], axes: dict[str, object]) -> list[dict[str, object]]:
    profiles: list[dict[str, object]] = []
    base_rules = baseline_profile["rules"]
    index = 0
    for threshold in axes["thresholds"]:
        for answer_feature in axes["answer_features"]:
            for support_feature in axes["support_features"]:
                for grounding_feature in axes["grounding_features"]:
                    for confidence_weight in axes["confidence_weights"]:
                        for format_weight in axes["format_weights"]:
                            profile = {
                                "profile_name": f"candidate_{index:03d}",
                                "description": "Calibration candidate for drifted proxy v4.",
                                "threshold": int(threshold),
                                "weights": {
                                    "object_json": 2,
                                    "schema_string_fields": 2,
                                    "non_empty_final_answer": 1,
                                    "non_empty_support": 1,
                                    answer_feature: 1,
                                    support_feature: 1,
                                    grounding_feature: 1,
                                    "minimal_format_clean": int(format_weight),
                                },
                                "rules": base_rules,
                                "axes": {
                                    "answer_feature": answer_feature,
                                    "support_feature": support_feature,
                                    "grounding_feature": grounding_feature,
                                    "confidence_weight": int(confidence_weight),
                                    "format_weight": int(format_weight),
                                },
                            }
                            if int(confidence_weight):
                                profile["weights"]["confidence_mild"] = int(confidence_weight)
                            profiles.append(profile)
                            index += 1
    return profiles


def summarize_passes(results: list[dict[str, object]]) -> tuple[int, float]:
    count = sum(int(result["proxy_pass"]) for result in results)
    total = len(results)
    return count, (round(count / total, 4) if total else 0.0)


def rescue_signatures(
    baseline_profile: dict[str, object],
    candidate_profile: dict[str, object],
    baseline_result: dict[str, object],
    candidate_result: dict[str, object],
) -> list[str]:
    signatures: list[str] = []
    baseline_weights = baseline_profile["weights"]
    candidate_weights = candidate_profile["weights"]
    baseline_features = baseline_result["proxy_features"]
    candidate_features = candidate_result["proxy_features"]
    for feature in candidate_weights:
        if not candidate_features.get(feature, False):
            continue
        baseline_weight = int(baseline_weights.get(feature, 0))
        if baseline_weight == 0 or not baseline_features.get(feature, False):
            signatures.append(feature)
    return sorted(signatures)


def main() -> None:
    args = parse_args()
    tasks = load_tasks(args.tasks)
    task_map = task_lookup(tasks)
    split_by_id = split_lookup(load_splits(args.splits))
    baseline_profile = load_json(args.baseline_profile)
    axes = load_json(args.candidate_axes)
    raw_records = load_jsonl(args.baseline_raw)
    outputs = [record for record in iter_records(raw_records, "solver_output") if split_by_id[record["task_id"]] == "calibration"]

    baseline_results = {
        record["task_id"]: score_proxy_profile(task_map[record["task_id"]], record.get("parsed_output"), baseline_profile)
        for record in outputs
    }
    baseline_pass_count, baseline_rate = summarize_passes(list(baseline_results.values()))
    admission_ceiling = round(min(0.92, baseline_rate + 0.18), 4)

    search_records: list[dict[str, object]] = []
    selected_profile: dict[str, object] | None = None
    selected_summary: dict[str, object] | None = None

    for candidate in build_candidate_profiles(baseline_profile, axes):
        candidate_results = {
            record["task_id"]: score_proxy_profile(task_map[record["task_id"]], record.get("parsed_output"), candidate)
            for record in outputs
        }
        fail_to_pass = sorted(
            task_id
            for task_id in candidate_results
            if (not baseline_results[task_id]["proxy_pass"]) and candidate_results[task_id]["proxy_pass"]
        )
        pass_to_fail = sorted(
            task_id
            for task_id in candidate_results
            if baseline_results[task_id]["proxy_pass"] and (not candidate_results[task_id]["proxy_pass"])
        )
        candidate_pass_count, candidate_rate = summarize_passes(list(candidate_results.values()))
        mean_score_delta = round(
            sum(
                float(candidate_results[task_id]["proxy_mean_item_score"]) - float(baseline_results[task_id]["proxy_mean_item_score"])
                for task_id in candidate_results
            )
            / len(candidate_results),
            4,
        )
        categories = sorted({task_map[task_id]["category"] for task_id in fail_to_pass})
        rescue_feature_signatures = {
            task_id: rescue_signatures(baseline_profile, candidate, baseline_results[task_id], candidate_results[task_id])
            for task_id in fail_to_pass
        }
        rescue_diversity = len({tuple(signature) for signature in rescue_feature_signatures.values() if signature})
        coverage_count = len(categories)
        objective = round(
            (6.0 * len(fail_to_pass))
            - (8.0 * len(pass_to_fail))
            - (30.0 * max(0.0, candidate_rate - admission_ceiling))
            + (1.5 * coverage_count)
            + (1.0 * rescue_diversity)
            + mean_score_delta,
            4,
        )
        summary = {
            "record_type": "candidate_summary",
            "candidate_profile_name": candidate["profile_name"],
            "candidate_profile": candidate,
            "fail_to_pass_count": len(fail_to_pass),
            "pass_to_fail_count": len(pass_to_fail),
            "candidate_pass_count": candidate_pass_count,
            "candidate_admission_rate": candidate_rate,
            "baseline_pass_count": baseline_pass_count,
            "baseline_admission_rate": baseline_rate,
            "admission_ceiling": admission_ceiling,
            "proxy_mean_item_score_delta": mean_score_delta,
            "flip_category_coverage_count": coverage_count,
            "flip_categories": categories,
            "rescue_diversity": rescue_diversity,
            "objective_score": objective,
            "fail_to_pass_ids": fail_to_pass,
            "pass_to_fail_ids": pass_to_fail,
            "rescue_feature_signatures": rescue_feature_signatures,
        }
        search_records.append(summary)

        admissible = len(fail_to_pass) >= 1 and len(pass_to_fail) <= 1 and candidate_rate <= admission_ceiling
        if not admissible:
            continue
        if selected_summary is None:
            selected_profile = candidate
            selected_summary = summary
            continue
        better = (
            summary["objective_score"] > selected_summary["objective_score"]
            or (
                summary["objective_score"] == selected_summary["objective_score"]
                and summary["fail_to_pass_count"] > selected_summary["fail_to_pass_count"]
            )
            or (
                summary["objective_score"] == selected_summary["objective_score"]
                and summary["fail_to_pass_count"] == selected_summary["fail_to_pass_count"]
                and summary["pass_to_fail_count"] < selected_summary["pass_to_fail_count"]
            )
        )
        if better:
            selected_profile = candidate
            selected_summary = summary

    if selected_profile is None or selected_summary is None:
        raise SystemExit("Calibration failed to find an admissible drifted proxy candidate on the calibration split.")

    locked_profile = {
        "profile_name": "drifted_proxy_v4",
        "description": "Calibration-locked drifted proxy ruler for v3. Selected on the calibration split only.",
        "threshold": selected_profile["threshold"],
        "weights": selected_profile["weights"],
        "rules": selected_profile["rules"],
        "axes": selected_profile["axes"],
        "calibration_manifest": {
            "runtime_timestamp_utc": utc_now_iso(),
            "experiment_tag": args.experiment_tag,
            "calibrated_from_raw": relpath(args.baseline_raw),
            "tasks_path": relpath(args.tasks),
            "splits_path": relpath(args.splits),
            "selected_from_candidate": selected_summary["candidate_profile_name"],
            "baseline_profile_path": relpath(args.baseline_profile),
            "candidate_axes_path": relpath(args.candidate_axes),
            "objective": "maximize calibration fail_to_pass with strong penalties for pass_to_fail and excessive admission rate, while rewarding category coverage and rescue diversity",
            "admission_ceiling": admission_ceiling,
            "selected_summary": {
                key: value
                for key, value in selected_summary.items()
                if key not in {"candidate_profile"}
            },
        },
    }

    profile_path = args.output_profile or make_output_path("calibration", f"locked_drifted_proxy_v4__{args.experiment_tag}", suffix=".json")
    search_path = args.output_search or make_output_path("calibration", f"calibration_search__{args.experiment_tag}")
    write_json(profile_path, locked_profile)
    write_jsonl(
        search_path,
        [
            {
                "record_type": "calibration_manifest",
                "runtime_timestamp_utc": utc_now_iso(),
                "experiment_tag": args.experiment_tag,
                "baseline_raw": relpath(args.baseline_raw),
                "baseline_profile_path": relpath(args.baseline_profile),
                "candidate_axes_path": relpath(args.candidate_axes),
                "tasks_path": relpath(args.tasks),
                "splits_path": relpath(args.splits),
                "baseline_pass_count": baseline_pass_count,
                "baseline_admission_rate": baseline_rate,
                "selection_rule": "rank admissible candidates by objective_score; admissible means fail_to_pass>=1, pass_to_fail<=1, and admission_rate<=admission_ceiling",
                "locked_profile_path": relpath(profile_path),
                "admission_ceiling": admission_ceiling,
            },
            *search_records,
        ],
    )
    print(relpath(profile_path))
    print(relpath(search_path))


if __name__ == "__main__":
    main()
