from __future__ import annotations

import argparse
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from common_v3 import (  # noqa: E402
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
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate v3 raw outputs with a locked proxy ruler.")
    parser.add_argument("--input", required=True, type=pathlib.Path)
    parser.add_argument("--profile", required=True, type=pathlib.Path)
    parser.add_argument("--proxy-label", help="Override the proxy profile label.")
    parser.add_argument("--condition-label", help="Override the condition label.")
    parser.add_argument("--tasks", type=pathlib.Path, default=DEFAULT_TASKS_PATH)
    parser.add_argument("--splits", type=pathlib.Path, default=DEFAULT_SPLITS_PATH)
    parser.add_argument("--output", type=pathlib.Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    tasks = load_tasks(args.tasks)
    task_map = task_lookup(tasks)
    split_by_id = split_lookup(load_splits(args.splits))
    profile = load_json(args.profile)
    raw_records = load_jsonl(args.input)
    manifest = iter_records(raw_records, "run_manifest")[0]
    outputs = iter_records(raw_records, "solver_output")
    condition = args.condition_label or str(manifest["condition"])
    proxy_label = args.proxy_label or str(profile["profile_name"])
    output_path = args.output or make_output_path("evals", f"proxy__{condition}__{proxy_label}__{manifest['experiment_tag']}")
    eval_id = output_path.stem

    split_totals: dict[str, dict[str, float]] = {
        "calibration": {"pass": 0, "total": 0, "score_sum": 0.0, "valid_json": 0},
        "evaluation": {"pass": 0, "total": 0, "score_sum": 0.0, "valid_json": 0},
    }
    category_totals: dict[tuple[str, str], dict[str, float]] = {}
    task_records: list[dict[str, object]] = []

    for record in outputs:
        task = task_map[record["task_id"]]
        result = score_proxy_profile(task, record.get("parsed_output"), profile)
        split_name = split_by_id[record["task_id"]]
        category = str(record["task_category"])
        category_totals.setdefault((split_name, category), {"pass": 0, "total": 0, "score_sum": 0.0, "valid_json": 0})
        split_totals[split_name]["pass"] += int(result["proxy_pass"])
        split_totals[split_name]["total"] += 1
        split_totals[split_name]["score_sum"] += float(result["proxy_mean_item_score"])
        split_totals[split_name]["valid_json"] += int(result["proxy_features"]["object_json"])
        category_totals[(split_name, category)]["pass"] += int(result["proxy_pass"])
        category_totals[(split_name, category)]["total"] += 1
        category_totals[(split_name, category)]["score_sum"] += float(result["proxy_mean_item_score"])
        category_totals[(split_name, category)]["valid_json"] += int(result["proxy_features"]["object_json"])
        task_records.append(
            {
                "record_type": "proxy_eval",
                "eval_id": eval_id,
                "condition": condition,
                "proxy_profile": proxy_label,
                "experiment_tag": manifest["experiment_tag"],
                "input_run_id": manifest["run_id"],
                "input_path": relpath(args.input),
                "task_id": record["task_id"],
                "split": split_name,
                "task_category": category,
                **result,
            }
        )

    records: list[dict[str, object]] = [
        {
            "record_type": "proxy_manifest",
            "eval_id": eval_id,
            "condition": condition,
            "proxy_profile": proxy_label,
            "runtime_timestamp_utc": utc_now_iso(),
            "experiment_tag": manifest["experiment_tag"],
            "input_run_id": manifest["run_id"],
            "input_path": relpath(args.input),
            "profile_path": relpath(args.profile),
            "profile_description": profile["description"],
            "tasks_path": relpath(args.tasks),
            "splits_path": relpath(args.splits),
        }
    ]
    for split_name, totals in split_totals.items():
        total = int(totals["total"])
        passes = int(totals["pass"])
        mean_score = round(float(totals["score_sum"]) / total, 4) if total else 0.0
        records.append(
            {
                "record_type": "proxy_split_summary",
                "eval_id": eval_id,
                "condition": condition,
                "proxy_profile": proxy_label,
                "split": split_name,
                "proxy_admitted_count": passes,
                "proxy_total": total,
                "proxy_admission_rate": round(passes / total, 4) if total else 0.0,
                "proxy_mean_item_score": mean_score,
                "valid_json_count": int(totals["valid_json"]),
            }
        )
    for (split_name, category), totals in sorted(category_totals.items()):
        total = int(totals["total"])
        passes = int(totals["pass"])
        records.append(
            {
                "record_type": "proxy_category_summary",
                "eval_id": eval_id,
                "condition": condition,
                "proxy_profile": proxy_label,
                "split": split_name,
                "task_category": category,
                "proxy_admitted_count": passes,
                "proxy_total": total,
                "proxy_admission_rate": round(passes / total, 4) if total else 0.0,
                "proxy_mean_item_score": round(float(totals["score_sum"]) / total, 4) if total else 0.0,
                "valid_json_count": int(totals["valid_json"]),
            }
        )
    records.extend(task_records)
    write_jsonl(output_path, records)
    print(relpath(output_path))


if __name__ == "__main__":
    main()
