from __future__ import annotations

import argparse
import csv
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
    utc_timestamp,
    write_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize v3 audit outputs and ruler-drift flip analysis.")
    parser.add_argument("--audits", nargs="+", required=True, type=pathlib.Path)
    parser.add_argument("--flip-analysis", required=True, type=pathlib.Path)
    parser.add_argument("--near-miss-analysis", type=pathlib.Path)
    parser.add_argument("--output-stem")
    return parser.parse_args()


def csv_write(path: pathlib.Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    stem = args.output_stem or f"v3_condition_summary__{utc_timestamp()}"
    condition_csv = make_output_path("summaries", stem, suffix=".csv")
    condition_md = make_output_path("summaries", stem, suffix=".md")
    category_csv = make_output_path("summaries", stem.replace("condition", "category"), suffix=".csv")
    category_md = make_output_path("summaries", stem.replace("condition", "category"), suffix=".md")

    condition_rows: list[dict[str, object]] = []
    category_rows: list[dict[str, object]] = []
    for audit_path in args.audits:
        records = load_jsonl(audit_path)
        manifest = iter_records(records, "audit_manifest")[0]
        for summary in iter_records(records, "audit_split_summary"):
            condition_rows.append(
                {
                    "condition": summary["condition"],
                    "proxy_profile": summary["proxy_profile"],
                    "split": summary["split"],
                    "strict_score": summary["strict_score"],
                    "proxy_admission_rate": summary["proxy_admission_rate"],
                    "proxy_mean_item_score": summary["proxy_mean_item_score"],
                    "proxy_admitted_count": summary["proxy_admitted_count"],
                    "strict_confirmed_count": summary["strict_confirmed_count"],
                    "challenge_failure_count": summary["challenge_failure_count"],
                    "disagreement_count": summary["disagreement_count"],
                    "valid_json_count": summary["valid_json_count"],
                    "audited_precision": summary["audited_precision"],
                    "audit_file": relpath(audit_path),
                    "experiment_tag": manifest["experiment_tag"],
                }
            )
        for summary in iter_records(records, "audit_category_summary"):
            category_rows.append(
                {
                    "condition": summary["condition"],
                    "proxy_profile": summary["proxy_profile"],
                    "split": summary["split"],
                    "task_category": summary["task_category"],
                    "strict_score": summary["strict_score"],
                    "proxy_admission_rate": summary["proxy_admission_rate"],
                    "proxy_mean_item_score": summary["proxy_mean_item_score"],
                    "proxy_admitted_count": summary["proxy_admitted_count"],
                    "strict_confirmed_count": summary["strict_confirmed_count"],
                    "challenge_failure_count": summary["challenge_failure_count"],
                    "disagreement_count": summary["disagreement_count"],
                    "valid_json_count": summary["valid_json_count"],
                    "audited_precision": summary["audited_precision"],
                    "audit_file": relpath(audit_path),
                    "experiment_tag": manifest["experiment_tag"],
                }
            )

    condition_rows.sort(key=lambda row: (row["split"], row["condition"], row["proxy_profile"]))
    category_rows.sort(key=lambda row: (row["split"], row["condition"], row["proxy_profile"], row["task_category"]))
    condition_fields = [
        "condition",
        "proxy_profile",
        "split",
        "strict_score",
        "proxy_admission_rate",
        "proxy_mean_item_score",
        "proxy_admitted_count",
        "strict_confirmed_count",
        "challenge_failure_count",
        "disagreement_count",
        "valid_json_count",
        "audited_precision",
        "audit_file",
        "experiment_tag",
    ]
    category_fields = [
        "condition",
        "proxy_profile",
        "split",
        "task_category",
        "strict_score",
        "proxy_admission_rate",
        "proxy_mean_item_score",
        "proxy_admitted_count",
        "strict_confirmed_count",
        "challenge_failure_count",
        "disagreement_count",
        "valid_json_count",
        "audited_precision",
        "audit_file",
        "experiment_tag",
    ]
    csv_write(condition_csv, condition_rows, condition_fields)
    csv_write(category_csv, category_rows, category_fields)

    flip_records = load_jsonl(args.flip_analysis)
    flip_manifest = iter_records(flip_records, "flip_manifest")[0]
    flip_split = iter_records(flip_records, "flip_split_summary")
    flip_categories = iter_records(flip_records, "flip_category_summary")
    flip_tasks = iter_records(flip_records, "flip_task")
    heldout_flip_tasks = [row for row in flip_tasks if row["split"] == "evaluation" and (row["fail_to_pass"] or row["pass_to_fail"])]

    near_miss_lines: list[str] = []
    if args.near_miss_analysis:
        near_miss_records = load_jsonl(args.near_miss_analysis)
        rescued = [
            row
            for row in iter_records(near_miss_records, "near_miss_task")
            if row["split"] == "evaluation" and row["drifted_proxy_pass"] and (not row["baseline_proxy_pass"])
        ]
        near_miss_lines.extend(
            [
                "",
                "## Held-Out Near-Miss Rescues",
                "",
                f"Near-miss file: `{relpath(args.near_miss_analysis)}`",
                "",
                "| task_id | task_category | baseline_proxy_mean_item_score | drifted_proxy_mean_item_score | drift_rescue_features |",
                "| --- | --- | ---: | ---: | --- |",
            ]
        )
        if rescued:
            for row in rescued:
                near_miss_lines.append(
                    f"| {row['task_id']} | {row['task_category']} | {row['baseline_proxy_mean_item_score']} | {row['drifted_proxy_mean_item_score']} | {', '.join(row['drift_rescue_features'])} |"
                )
        else:
            near_miss_lines.append("| none | - | - | - | - |")

    condition_lines = [
        "# PoC v3 Summary",
        "",
        "## Condition By Split",
        "",
        "| condition | proxy_profile | split | strict_score | proxy_admission_rate | proxy_mean_item_score | proxy_admitted_count | strict_confirmed_count | challenge_failure_count | disagreement_count | valid_json_count | audited_precision |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in condition_rows:
        condition_lines.append(
            "| {condition} | {proxy_profile} | {split} | {strict_score} | {proxy_admission_rate} | {proxy_mean_item_score} | {proxy_admitted_count} | {strict_confirmed_count} | {challenge_failure_count} | {disagreement_count} | {valid_json_count} | {audited_precision} |".format(
                **row
            )
        )
    condition_lines.extend(
        [
            "",
            "## Ruler-Drift Analysis",
            "",
            f"Flip analysis file: `{relpath(args.flip_analysis)}`",
            "",
            "| split | fail_to_pass_count | pass_to_fail_count | net_admission_difference | proxy_mean_item_score_delta | total_tasks |",
            "| --- | ---: | ---: | ---: | ---: | ---: |",
        ]
    )
    for row in flip_split:
        condition_lines.append(
            "| {split} | {fail_to_pass_count} | {pass_to_fail_count} | {net_admission_difference} | {proxy_mean_item_score_delta} | {total_tasks} |".format(
                **row
            )
        )
    condition_lines.extend(
        [
            "",
            "| split | task_category | fail_to_pass_count | pass_to_fail_count |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for row in flip_categories:
        condition_lines.append(
            "| {split} | {task_category} | {fail_to_pass_count} | {pass_to_fail_count} |".format(
                **row
            )
        )
    condition_lines.extend(
        [
            "",
            "## Held-Out Item-Level Flip Table",
            "",
            "| task_id | task_category | baseline_proxy_pass | drifted_proxy_pass | fail_to_pass | pass_to_fail | baseline_proxy_mean_item_score | drifted_proxy_mean_item_score |",
            "| --- | --- | --- | --- | --- | --- | ---: | ---: |",
        ]
    )
    if heldout_flip_tasks:
        for row in heldout_flip_tasks:
            condition_lines.append(
                f"| {row['task_id']} | {row['task_category']} | {row['baseline_proxy_pass']} | {row['drifted_proxy_pass']} | {row['fail_to_pass']} | {row['pass_to_fail']} | {row['baseline_proxy_mean_item_score']} | {row['drifted_proxy_mean_item_score']} |"
            )
    else:
        condition_lines.append("| none | - | - | - | - | - | - | - |")
    condition_lines.extend(
        [
            "",
            "## Calibration Note",
            "",
            f"Drifted ruler was locked before held-out evaluation. Source manifest: `{flip_manifest['drifted_proxy_path']}`",
            "",
        ]
    )
    condition_lines.extend(near_miss_lines)

    category_lines = [
        "# PoC v3 Category Summary",
        "",
        "| condition | proxy_profile | split | task_category | strict_score | proxy_admission_rate | proxy_mean_item_score | proxy_admitted_count | strict_confirmed_count | challenge_failure_count | disagreement_count | valid_json_count | audited_precision |",
        "| --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in category_rows:
        category_lines.append(
            "| {condition} | {proxy_profile} | {split} | {task_category} | {strict_score} | {proxy_admission_rate} | {proxy_mean_item_score} | {proxy_admitted_count} | {strict_confirmed_count} | {challenge_failure_count} | {disagreement_count} | {valid_json_count} | {audited_precision} |".format(
                **row
            )
        )

    write_text(condition_md, "\n".join(condition_lines))
    write_text(category_md, "\n".join(category_lines))
    print(relpath(condition_csv))
    print(relpath(condition_md))
    print(relpath(category_csv))
    print(relpath(category_md))


if __name__ == "__main__":
    main()
