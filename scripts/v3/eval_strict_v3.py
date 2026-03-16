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
    load_jsonl,
    load_splits,
    load_tasks,
    make_output_path,
    normalize_answer,
    relpath,
    split_lookup,
    support_contains_acceptable_span,
    task_lookup,
    utc_now_iso,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate v3 raw outputs with the conservative deterministic strict metric.")
    parser.add_argument("--input", required=True, type=pathlib.Path)
    parser.add_argument("--tasks", type=pathlib.Path, default=DEFAULT_TASKS_PATH)
    parser.add_argument("--splits", type=pathlib.Path, default=DEFAULT_SPLITS_PATH)
    parser.add_argument("--condition-label")
    parser.add_argument("--output", type=pathlib.Path)
    return parser.parse_args()


def evaluate_record(task: dict[str, object], parsed_output: dict[str, object] | None) -> dict[str, object]:
    valid_json = isinstance(parsed_output, dict)
    schema_valid = valid_json and isinstance(parsed_output.get("final_answer"), str) and isinstance(parsed_output.get("support"), str)
    final_answer = parsed_output.get("final_answer", "") if isinstance(parsed_output, dict) else ""
    support = parsed_output.get("support", "") if isinstance(parsed_output, dict) else ""
    exact_answer_match = bool(
        schema_valid and normalize_answer(task, str(final_answer)) == normalize_answer(task, str(task["gold_answer"]))
    )
    evidence_match = support_contains_acceptable_span(task, str(support)) if schema_valid else support_contains_acceptable_span(task, "")
    strict_pass = bool(valid_json and schema_valid and exact_answer_match and (evidence_match in (True, None)))
    failed_checks: list[str] = []
    if not valid_json:
        failed_checks.append("valid_json")
    if valid_json and not schema_valid:
        failed_checks.append("schema_valid")
    if schema_valid and not exact_answer_match:
        failed_checks.append("exact_answer_match")
    if evidence_match is False:
        failed_checks.append("evidence_span_exists")
    return {
        "valid_json": valid_json,
        "schema_valid": schema_valid,
        "exact_answer_match": exact_answer_match,
        "evidence_span_exists": evidence_match,
        "strict_pass": strict_pass,
        "failed_checks": failed_checks,
    }


def main() -> None:
    args = parse_args()
    tasks = load_tasks(args.tasks)
    task_map = task_lookup(tasks)
    split_by_id = split_lookup(load_splits(args.splits))
    raw_records = load_jsonl(args.input)
    manifest = iter_records(raw_records, "run_manifest")[0]
    outputs = iter_records(raw_records, "solver_output")
    condition = args.condition_label or str(manifest["condition"])
    output_path = args.output or make_output_path("evals", f"strict__{condition}__{manifest['experiment_tag']}")
    eval_id = output_path.stem

    split_counts: dict[str, dict[str, int]] = {
        "calibration": {"pass": 0, "total": 0, "valid_json": 0},
        "evaluation": {"pass": 0, "total": 0, "valid_json": 0},
    }
    category_counts: dict[tuple[str, str], dict[str, int]] = {}
    task_records: list[dict[str, object]] = []

    for record in outputs:
        task = task_map[record["task_id"]]
        evaluation = evaluate_record(task, record.get("parsed_output"))
        split_name = split_by_id[record["task_id"]]
        category = str(record["task_category"])
        category_counts.setdefault((split_name, category), {"pass": 0, "total": 0, "valid_json": 0})
        split_counts[split_name]["pass"] += int(evaluation["strict_pass"])
        split_counts[split_name]["total"] += 1
        split_counts[split_name]["valid_json"] += int(evaluation["valid_json"])
        category_counts[(split_name, category)]["pass"] += int(evaluation["strict_pass"])
        category_counts[(split_name, category)]["total"] += 1
        category_counts[(split_name, category)]["valid_json"] += int(evaluation["valid_json"])
        task_records.append(
            {
                "record_type": "strict_eval",
                "eval_id": eval_id,
                "condition": condition,
                "experiment_tag": manifest["experiment_tag"],
                "input_run_id": manifest["run_id"],
                "input_path": relpath(args.input),
                "task_id": record["task_id"],
                "split": split_name,
                "task_category": category,
                **evaluation,
            }
        )

    records: list[dict[str, object]] = [
        {
            "record_type": "strict_manifest",
            "eval_id": eval_id,
            "condition": condition,
            "runtime_timestamp_utc": utc_now_iso(),
            "experiment_tag": manifest["experiment_tag"],
            "metric_name": "strict_replayable_metric_v3_conservative",
            "input_run_id": manifest["run_id"],
            "input_path": relpath(args.input),
            "tasks_path": relpath(args.tasks),
            "splits_path": relpath(args.splits),
        }
    ]
    for split_name, counts in split_counts.items():
        total = counts["total"]
        passes = counts["pass"]
        records.append(
            {
                "record_type": "strict_split_summary",
                "eval_id": eval_id,
                "condition": condition,
                "split": split_name,
                "strict_pass_count": passes,
                "strict_total": total,
                "strict_score": round(passes / total, 4) if total else 0.0,
                "valid_json_count": counts["valid_json"],
            }
        )
    for (split_name, category), counts in sorted(category_counts.items()):
        total = counts["total"]
        records.append(
            {
                "record_type": "strict_category_summary",
                "eval_id": eval_id,
                "condition": condition,
                "split": split_name,
                "task_category": category,
                "strict_pass_count": counts["pass"],
                "strict_total": total,
                "strict_score": round(counts["pass"] / total, 4) if total else 0.0,
                "valid_json_count": counts["valid_json"],
            }
        )
    records.extend(task_records)
    write_jsonl(output_path, records)
    print(relpath(output_path))


if __name__ == "__main__":
    main()
