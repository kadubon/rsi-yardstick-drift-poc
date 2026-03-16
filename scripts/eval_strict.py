from __future__ import annotations

import argparse
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from common import (  # noqa: E402
    DEFAULT_TASKS_PATH,
    filter_tasks,
    iter_records,
    load_jsonl,
    make_output_path,
    normalize_answer,
    support_contains_acceptable_span,
    task_lookup,
    utc_now_iso,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Evaluate solver outputs with the strict replayable metric.")
    parser.add_argument("--input", required=True, type=pathlib.Path, help="Raw solver JSONL.")
    parser.add_argument("--tasks", type=pathlib.Path, default=DEFAULT_TASKS_PATH, help="Tasks JSONL.")
    parser.add_argument("--condition-label", help="Override the condition label.")
    parser.add_argument("--task-ids", help="Comma-separated subset of task ids.")
    parser.add_argument("--limit", type=int, help="Limit evaluated tasks after filtering.")
    parser.add_argument("--output", type=pathlib.Path, help="Explicit output JSONL path.")
    return parser.parse_args()


def evaluate_record(task: dict[str, object], parsed_output: dict[str, object] | None) -> dict[str, object]:
    valid_json = isinstance(parsed_output, dict)
    schema_valid = valid_json and isinstance(parsed_output.get("final_answer"), str) and isinstance(parsed_output.get("support"), str)
    final_answer = parsed_output.get("final_answer", "") if isinstance(parsed_output, dict) else ""
    support = parsed_output.get("support", "") if isinstance(parsed_output, dict) else ""
    exact_answer_match = bool(
        schema_valid
        and normalize_answer(task, str(final_answer)) == normalize_answer(task, str(task["gold_answer"]))
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
    tasks = load_jsonl(args.tasks)
    task_ids = [item.strip() for item in args.task_ids.split(",")] if args.task_ids else None
    selected_tasks = filter_tasks(tasks, task_ids=task_ids, limit=args.limit)
    task_map = task_lookup(selected_tasks)

    raw_records = load_jsonl(args.input)
    manifest = iter_records(raw_records, "run_manifest")[0]
    solver_outputs = [record for record in iter_records(raw_records, "solver_output") if record["task_id"] in task_map]

    condition = args.condition_label or str(manifest["condition"])
    output_path = args.output or make_output_path("evals", f"strict__{condition}")
    eval_id = output_path.stem

    results: list[dict[str, object]] = []
    strict_passes: list[bool] = []
    for record in solver_outputs:
        task = task_map[record["task_id"]]
        evaluation = evaluate_record(task, record.get("parsed_output"))
        strict_passes.append(bool(evaluation["strict_pass"]))
        results.append(
            {
                "record_type": "strict_eval",
                "eval_id": eval_id,
                "condition": condition,
                "task_id": record["task_id"],
                "task_category": record["task_category"],
                "input_run_id": manifest["run_id"],
                "input_path": str(args.input),
                **evaluation,
            }
        )

    records: list[dict[str, object]] = [
        {
            "record_type": "strict_manifest",
            "eval_id": eval_id,
            "condition": condition,
            "runtime_timestamp_utc": utc_now_iso(),
            "metric_name": "strict_replayable_metric_v1",
            "input_run_id": manifest["run_id"],
            "input_path": str(args.input),
            "task_ids": [record["task_id"] for record in results],
            "strict_pass_count": sum(strict_passes),
            "strict_total": len(strict_passes),
            "strict_rate": round(sum(strict_passes) / len(strict_passes), 4) if strict_passes else 0.0,
        }
    ]
    records.extend(results)
    write_jsonl(output_path, records)
    print(output_path)


if __name__ == "__main__":
    main()
