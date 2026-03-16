from __future__ import annotations

import argparse
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from common import (  # noqa: E402
    DEFAULT_TASKS_PATH,
    PROXY_PRESETS,
    PROXY_PROFILES,
    filter_tasks,
    iter_records,
    load_jsonl,
    make_output_path,
    score_proxy_features,
    task_lookup,
    utc_now_iso,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate solver outputs with the drift-prone proxy metric.")
    parser.add_argument("--input", required=True, type=pathlib.Path, help="Raw solver JSONL.")
    parser.add_argument("--tasks", type=pathlib.Path, default=DEFAULT_TASKS_PATH, help="Tasks JSONL.")
    parser.add_argument("--preset", choices=sorted(PROXY_PRESETS), help="Named proxy-evaluation condition.")
    parser.add_argument("--profile", choices=sorted(PROXY_PROFILES), help="Proxy scoring profile.")
    parser.add_argument("--condition-label", help="Override the condition label.")
    parser.add_argument("--task-ids", help="Comma-separated subset of task ids.")
    parser.add_argument("--limit", type=int, help="Limit evaluated tasks after filtering.")
    parser.add_argument("--output", type=pathlib.Path, help="Explicit output JSONL path.")
    return parser.parse_args()


def resolve_condition_and_profile(args: argparse.Namespace) -> tuple[str, str]:
    if args.preset:
        preset = PROXY_PRESETS[args.preset]
        condition = args.condition_label or preset["condition"]
        profile = args.profile or preset["profile"]
        return condition, profile
    if not args.profile:
        raise SystemExit("Either --preset or --profile is required.")
    return args.condition_label or "custom_proxy_condition", args.profile


def main() -> None:
    args = parse_args()
    condition, profile_name = resolve_condition_and_profile(args)
    profile = PROXY_PROFILES[profile_name]

    tasks = load_jsonl(args.tasks)
    task_ids = [item.strip() for item in args.task_ids.split(",")] if args.task_ids else None
    selected_tasks = filter_tasks(tasks, task_ids=task_ids, limit=args.limit)
    task_map = task_lookup(selected_tasks)

    raw_records = load_jsonl(args.input)
    manifest = iter_records(raw_records, "run_manifest")[0]
    solver_outputs = [record for record in iter_records(raw_records, "solver_output") if record["task_id"] in task_map]

    output_path = args.output or make_output_path("evals", f"proxy__{condition}")
    eval_id = output_path.stem

    result_records: list[dict[str, object]] = []
    proxy_passes: list[bool] = []
    total_weight = sum(profile["weights"].values())

    for record in solver_outputs:
        features = score_proxy_features(record.get("parsed_output"))
        points_by_feature = {
            feature: weight if features.get(feature, False) else 0
            for feature, weight in profile["weights"].items()
        }
        raw_points = sum(points_by_feature.values())
        proxy_pass = raw_points >= profile["threshold"]
        proxy_passes.append(proxy_pass)
        result_records.append(
            {
                "record_type": "proxy_eval",
                "eval_id": eval_id,
                "condition": condition,
                "task_id": record["task_id"],
                "task_category": record["task_category"],
                "input_run_id": manifest["run_id"],
                "input_path": str(args.input),
                "proxy_profile": profile_name,
                "proxy_features": features,
                "proxy_points_by_feature": points_by_feature,
                "proxy_raw_points": raw_points,
                "proxy_max_points": total_weight,
                "proxy_score": round(raw_points / total_weight, 4) if total_weight else 0.0,
                "proxy_threshold": profile["threshold"],
                "proxy_pass": proxy_pass,
            }
        )

    records: list[dict[str, object]] = [
        {
            "record_type": "proxy_manifest",
            "eval_id": eval_id,
            "condition": condition,
            "runtime_timestamp_utc": utc_now_iso(),
            "metric_name": "proxy_metric_v1",
            "proxy_profile": profile_name,
            "proxy_profile_description": profile["description"],
            "input_run_id": manifest["run_id"],
            "input_path": str(args.input),
            "task_ids": [record["task_id"] for record in result_records],
            "proxy_pass_count": sum(proxy_passes),
            "proxy_total": len(proxy_passes),
            "proxy_rate": round(sum(proxy_passes) / len(proxy_passes), 4) if proxy_passes else 0.0,
        }
    ]
    records.extend(result_records)
    write_jsonl(output_path, records)
    print(output_path)


if __name__ == "__main__":
    main()
