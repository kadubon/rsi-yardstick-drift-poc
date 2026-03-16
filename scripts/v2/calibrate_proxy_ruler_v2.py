from __future__ import annotations

import argparse
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from common_v2 import (  # noqa: E402
    DEFAULT_BASELINE_PROXY_PATH,
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
    parser = argparse.ArgumentParser(description="Calibrate and lock drifted_proxy_v3 using only calibration-split baseline outputs.")
    parser.add_argument("--baseline-raw", required=True, type=pathlib.Path)
    parser.add_argument("--tasks", type=pathlib.Path, default=DEFAULT_TASKS_PATH)
    parser.add_argument("--splits", type=pathlib.Path, default=DEFAULT_SPLITS_PATH)
    parser.add_argument("--baseline-profile", type=pathlib.Path, default=DEFAULT_BASELINE_PROXY_PATH)
    parser.add_argument("--experiment-tag", required=True)
    parser.add_argument("--output-profile", type=pathlib.Path)
    parser.add_argument("--output-search", type=pathlib.Path)
    return parser.parse_args()


def candidate_profiles() -> list[dict[str, object]]:
    profiles: list[dict[str, object]] = []
    index = 0
    for threshold in [6, 7, 8, 9]:
        for allow_scalar in [False, True]:
            for support_feature in ["support_word_count_moderate", "support_word_count_relaxed"]:
                for confidence_weight in [0, 1]:
                    profile = {
                        "profile_name": f"candidate_{index:03d}",
                        "description": "Calibration candidate for drifted proxy v3.",
                        "threshold": threshold,
                        "weights": {
                            "object_json": 2,
                            "schema_relaxed_scalar_answer" if allow_scalar else "schema_string_fields": 2,
                            "non_empty_final_answer": 1,
                            "non_empty_support": 1,
                            "final_answer_short_band": 1,
                            support_feature: 1,
                            "support_grounding_cue": 1,
                        },
                        "rules": {
                            "allow_scalar_final_answer": allow_scalar,
                            "support_min_words": 4,
                            "support_max_words": 18,
                            "support_min_words_relaxed": 3,
                            "support_max_words_relaxed": 28,
                            "final_answer_max_tokens": 4,
                        },
                    }
                    if confidence_weight:
                        profile["weights"]["confidence_word_present"] = confidence_weight
                    profiles.append(profile)
                    index += 1
    return profiles


def summarize_passes(results: list[dict[str, object]]) -> tuple[int, float]:
    count = sum(int(result["proxy_pass"]) for result in results)
    total = len(results)
    return count, (round(count / total, 4) if total else 0.0)


def main() -> None:
    args = parse_args()
    tasks = load_tasks(args.tasks)
    task_map = task_lookup(tasks)
    split_by_id = split_lookup(load_splits(args.splits))
    baseline_profile = load_json(args.baseline_profile)
    raw_records = load_jsonl(args.baseline_raw)
    outputs = [record for record in iter_records(raw_records, "solver_output") if split_by_id[record["task_id"]] == "calibration"]

    baseline_results = {
        record["task_id"]: score_proxy_profile(task_map[record["task_id"]], record.get("parsed_output"), baseline_profile)
        for record in outputs
    }
    baseline_pass_count, baseline_rate = summarize_passes(list(baseline_results.values()))

    search_records: list[dict[str, object]] = []
    selected_profile: dict[str, object] | None = None
    selected_summary: dict[str, object] | None = None

    for candidate in candidate_profiles():
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
        mean_score_diff = round(
            sum(candidate_results[task_id]["proxy_score"] - baseline_results[task_id]["proxy_score"] for task_id in candidate_results) / len(candidate_results),
            4,
        )
        summary = {
            "record_type": "candidate_summary",
            "candidate_profile_name": candidate["profile_name"],
            "fail_to_pass_count": len(fail_to_pass),
            "pass_to_fail_count": len(pass_to_fail),
            "candidate_pass_count": candidate_pass_count,
            "candidate_rate": candidate_rate,
            "baseline_pass_count": baseline_pass_count,
            "baseline_rate": baseline_rate,
            "mean_score_diff": mean_score_diff,
            "fail_to_pass_ids": fail_to_pass,
            "pass_to_fail_ids": pass_to_fail,
            "candidate_profile": candidate,
        }
        search_records.append(summary)

        is_admissible = len(fail_to_pass) >= 1 and len(pass_to_fail) == 0 and candidate_rate <= 0.89
        if not is_admissible:
            continue

        if selected_summary is None:
            selected_profile = candidate
            selected_summary = summary
            continue

        better = (
            summary["fail_to_pass_count"] > selected_summary["fail_to_pass_count"]
            or (
                summary["fail_to_pass_count"] == selected_summary["fail_to_pass_count"]
                and summary["mean_score_diff"] > selected_summary["mean_score_diff"]
            )
            or (
                summary["fail_to_pass_count"] == selected_summary["fail_to_pass_count"]
                and summary["mean_score_diff"] == selected_summary["mean_score_diff"]
                and summary["candidate_rate"] < selected_summary["candidate_rate"]
            )
        )
        if better:
            selected_profile = candidate
            selected_summary = summary

    if selected_profile is None or selected_summary is None:
        raise SystemExit("Calibration failed to find an admissible drifted proxy candidate on the calibration split.")

    locked_profile = {
        "profile_name": "drifted_proxy_v3",
        "description": "Calibration-locked drifted proxy ruler for v2. Selected on calibration split only.",
        "threshold": selected_profile["threshold"],
        "weights": selected_profile["weights"],
        "rules": selected_profile["rules"],
        "calibration_manifest": {
            "runtime_timestamp_utc": utc_now_iso(),
            "experiment_tag": args.experiment_tag,
            "calibrated_from_raw": relpath(args.baseline_raw),
            "tasks_path": relpath(args.tasks),
            "splits_path": relpath(args.splits),
            "selected_from_candidate": selected_summary["candidate_profile_name"],
            "baseline_profile_path": relpath(args.baseline_profile),
            "objective": "maximize fail_to_pass on calibration with pass_to_fail=0 and candidate_rate<=0.89",
            "selected_summary": {
                key: value
                for key, value in selected_summary.items()
                if key not in {"candidate_profile"}
            },
        },
    }

    profile_path = args.output_profile or make_output_path("calibration", f"locked_drifted_proxy_v3__{args.experiment_tag}", suffix=".json")
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
                "tasks_path": relpath(args.tasks),
                "splits_path": relpath(args.splits),
                "baseline_pass_count": baseline_pass_count,
                "baseline_rate": baseline_rate,
                "selection_rule": "maximize fail_to_pass, then mean_score_diff, then lower candidate_rate; require pass_to_fail=0 and candidate_rate<=0.89",
                "locked_profile_path": relpath(profile_path),
            },
            *search_records,
        ],
    )
    print(relpath(profile_path))
    print(relpath(search_path))


if __name__ == "__main__":
    main()
