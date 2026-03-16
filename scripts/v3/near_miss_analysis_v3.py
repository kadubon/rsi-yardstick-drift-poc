from __future__ import annotations

import argparse
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from common_v3 import (  # noqa: E402
    iter_records,
    load_jsonl,
    make_output_path,
    relpath,
    utc_now_iso,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Identify baseline near-misses and possible drift rescues for v3.")
    parser.add_argument("--baseline-proxy", required=True, type=pathlib.Path)
    parser.add_argument("--drifted-proxy", required=True, type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    baseline_records = load_jsonl(args.baseline_proxy)
    drifted_records = load_jsonl(args.drifted_proxy)
    base_manifest = iter_records(baseline_records, "proxy_manifest")[0]
    drift_manifest = iter_records(drifted_records, "proxy_manifest")[0]
    baseline_by_task = {record["task_id"]: record for record in iter_records(baseline_records, "proxy_eval")}
    drifted_by_task = {record["task_id"]: record for record in iter_records(drifted_records, "proxy_eval")}
    shared_task_ids = sorted(set(baseline_by_task) & set(drifted_by_task))
    output_path = args.output or make_output_path("analysis", f"near_miss_rescues__{base_manifest['experiment_tag']}")
    analysis_id = output_path.stem

    records: list[dict[str, object]] = [
        {
            "record_type": "near_miss_manifest",
            "analysis_id": analysis_id,
            "runtime_timestamp_utc": utc_now_iso(),
            "experiment_tag": base_manifest["experiment_tag"],
            "baseline_proxy_path": relpath(args.baseline_proxy),
            "drifted_proxy_path": relpath(args.drifted_proxy),
            "baseline_proxy_label": base_manifest["proxy_profile"],
            "drifted_proxy_label": drift_manifest["proxy_profile"],
        }
    ]
    for task_id in shared_task_ids:
        baseline = baseline_by_task[task_id]
        drifted = drifted_by_task[task_id]
        if baseline["proxy_pass"]:
            continue
        missing_baseline = sorted(feature for feature, points in baseline["proxy_points_by_feature"].items() if int(points) == 0)
        drift_rescues = sorted(
            feature
            for feature, points in drifted["proxy_points_by_feature"].items()
            if int(points) > 0 and int(baseline["proxy_points_by_feature"].get(feature, 0)) == 0
        )
        records.append(
            {
                "record_type": "near_miss_task",
                "analysis_id": analysis_id,
                "task_id": task_id,
                "split": baseline["split"],
                "task_category": baseline["task_category"],
                "baseline_proxy_pass": bool(baseline["proxy_pass"]),
                "drifted_proxy_pass": bool(drifted["proxy_pass"]),
                "baseline_proxy_mean_item_score": baseline["proxy_mean_item_score"],
                "drifted_proxy_mean_item_score": drifted["proxy_mean_item_score"],
                "missing_baseline_features": missing_baseline,
                "drift_rescue_features": drift_rescues,
            }
        )
    write_jsonl(output_path, records)
    print(relpath(output_path))


if __name__ == "__main__":
    main()
