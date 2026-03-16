from __future__ import annotations

import argparse
import pathlib
import sys
from collections import defaultdict

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from common_v2 import (  # noqa: E402
    iter_records,
    load_jsonl,
    make_output_path,
    relpath,
    utc_now_iso,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze same-output admission flips between two proxy rulers.")
    parser.add_argument("--baseline-proxy", required=True, type=pathlib.Path)
    parser.add_argument("--drifted-proxy", required=True, type=pathlib.Path)
    parser.add_argument("--condition-label", default="ruler_drift_only_v2")
    parser.add_argument("--output", type=pathlib.Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    baseline_records = load_jsonl(args.baseline_proxy)
    drifted_records = load_jsonl(args.drifted_proxy)
    base_manifest = iter_records(baseline_records, "proxy_manifest")[0]
    drift_manifest = iter_records(drifted_records, "proxy_manifest")[0]
    base_by_task = {record["task_id"]: record for record in iter_records(baseline_records, "proxy_eval")}
    drift_by_task = {record["task_id"]: record for record in iter_records(drifted_records, "proxy_eval")}
    shared_task_ids = sorted(set(base_by_task) & set(drift_by_task))
    if not shared_task_ids:
        raise SystemExit("No overlapping task ids between proxy evaluation files.")

    experiment_tag = str(base_manifest["experiment_tag"])
    output_path = args.output or make_output_path("analysis", f"admission_flips__{args.condition_label}__{experiment_tag}")
    analysis_id = output_path.stem
    split_stats = defaultdict(lambda: {"fail_to_pass": 0, "pass_to_fail": 0, "score_diff_sum": 0.0, "total": 0})
    category_stats = defaultdict(lambda: {"fail_to_pass": 0, "pass_to_fail": 0})
    task_records: list[dict[str, object]] = []

    for task_id in shared_task_ids:
        base = base_by_task[task_id]
        drift = drift_by_task[task_id]
        split_name = str(base["split"])
        category = str(base["task_category"])
        fail_to_pass = (not base["proxy_pass"]) and drift["proxy_pass"]
        pass_to_fail = base["proxy_pass"] and (not drift["proxy_pass"])
        score_diff = round(float(drift["proxy_score"]) - float(base["proxy_score"]), 4)
        split_stats[split_name]["fail_to_pass"] += int(fail_to_pass)
        split_stats[split_name]["pass_to_fail"] += int(pass_to_fail)
        split_stats[split_name]["score_diff_sum"] += score_diff
        split_stats[split_name]["total"] += 1
        category_stats[(split_name, category)]["fail_to_pass"] += int(fail_to_pass)
        category_stats[(split_name, category)]["pass_to_fail"] += int(pass_to_fail)
        task_records.append(
            {
                "record_type": "flip_task",
                "analysis_id": analysis_id,
                "condition": args.condition_label,
                "task_id": task_id,
                "split": split_name,
                "task_category": category,
                "baseline_proxy_pass": bool(base["proxy_pass"]),
                "drifted_proxy_pass": bool(drift["proxy_pass"]),
                "fail_to_pass": fail_to_pass,
                "pass_to_fail": pass_to_fail,
                "baseline_proxy_score": base["proxy_score"],
                "drifted_proxy_score": drift["proxy_score"],
                "score_diff": score_diff,
            }
        )

    records: list[dict[str, object]] = [
        {
            "record_type": "flip_manifest",
            "analysis_id": analysis_id,
            "condition": args.condition_label,
            "runtime_timestamp_utc": utc_now_iso(),
            "experiment_tag": experiment_tag,
            "baseline_proxy_path": relpath(args.baseline_proxy),
            "drifted_proxy_path": relpath(args.drifted_proxy),
            "baseline_proxy_label": base_manifest["proxy_profile"],
            "drifted_proxy_label": drift_manifest["proxy_profile"],
        }
    ]
    for split_name, stats in split_stats.items():
        total = int(stats["total"])
        records.append(
            {
                "record_type": "flip_split_summary",
                "analysis_id": analysis_id,
                "condition": args.condition_label,
                "split": split_name,
                "fail_to_pass_count": int(stats["fail_to_pass"]),
                "pass_to_fail_count": int(stats["pass_to_fail"]),
                "mean_score_difference": round(float(stats["score_diff_sum"]) / total, 4) if total else 0.0,
                "total_tasks": total,
            }
        )
    for (split_name, category), stats in sorted(category_stats.items()):
        records.append(
            {
                "record_type": "flip_category_summary",
                "analysis_id": analysis_id,
                "condition": args.condition_label,
                "split": split_name,
                "task_category": category,
                "fail_to_pass_count": int(stats["fail_to_pass"]),
                "pass_to_fail_count": int(stats["pass_to_fail"]),
            }
        )
    records.extend(task_records)
    write_jsonl(output_path, records)
    print(relpath(output_path))


if __name__ == "__main__":
    main()
