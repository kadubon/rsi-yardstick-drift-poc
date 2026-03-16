from __future__ import annotations

import argparse
import csv
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from common_v2 import (  # noqa: E402
    iter_records,
    load_jsonl,
    make_output_path,
    relpath,
    utc_timestamp,
    write_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize v2 audit outputs and ruler-drift flip analysis.")
    parser.add_argument("--audits", nargs="+", required=True, type=pathlib.Path)
    parser.add_argument("--flip-analysis", required=True, type=pathlib.Path)
    parser.add_argument("--output-stem")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stem = args.output_stem or f"v2_condition_summary__{utc_timestamp()}"
    csv_path = make_output_path("summaries", stem, suffix=".csv")
    md_path = make_output_path("summaries", stem, suffix=".md")

    rows: list[dict[str, object]] = []
    for audit_path in args.audits:
        records = load_jsonl(audit_path)
        manifest = iter_records(records, "audit_manifest")[0]
        for summary in iter_records(records, "audit_split_summary"):
            rows.append(
                {
                    "condition": summary["condition"],
                    "proxy_profile": summary["proxy_profile"],
                    "split": summary["split"],
                    "strict_score": summary["strict_score"],
                    "proxy_score": summary["proxy_score"],
                    "binary_admission_count": summary["binary_admission_count"],
                    "strict_confirmed_count": summary["strict_confirmed_count"],
                    "challenge_failure_count": summary["challenge_failure_count"],
                    "disagreement_count": summary["disagreement_count"],
                    "audited_precision": summary["audited_precision"],
                    "audit_file": relpath(audit_path),
                    "experiment_tag": manifest["experiment_tag"],
                }
            )

    rows.sort(key=lambda row: (row["split"], row["condition"], row["proxy_profile"]))
    fieldnames = [
        "condition",
        "proxy_profile",
        "split",
        "strict_score",
        "proxy_score",
        "binary_admission_count",
        "strict_confirmed_count",
        "challenge_failure_count",
        "disagreement_count",
        "audited_precision",
        "audit_file",
        "experiment_tag",
    ]
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    flip_records = load_jsonl(args.flip_analysis)
    flip_manifest = iter_records(flip_records, "flip_manifest")[0]
    flip_summaries = iter_records(flip_records, "flip_split_summary")
    flip_categories = iter_records(flip_records, "flip_category_summary")

    markdown_lines = [
        "# PoC v2 Summary",
        "",
        "## Condition By Split",
        "",
        "| condition | proxy_profile | split | strict_score | proxy_score | binary_admission_count | strict_confirmed_count | challenge_failure_count | disagreement_count | audited_precision |",
        "| --- | --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        markdown_lines.append(
            "| {condition} | {proxy_profile} | {split} | {strict_score} | {proxy_score} | {binary_admission_count} | {strict_confirmed_count} | {challenge_failure_count} | {disagreement_count} | {audited_precision} |".format(
                **row
            )
        )

    markdown_lines.extend(
        [
            "",
            "## Ruler-Drift Flip Analysis",
            "",
            f"Flip analysis file: `{relpath(args.flip_analysis)}`",
            "",
            "| split | fail_to_pass_count | pass_to_fail_count | mean_score_difference | total_tasks |",
            "| --- | ---: | ---: | ---: | ---: |",
        ]
    )
    for summary in flip_summaries:
        markdown_lines.append(
            "| {split} | {fail_to_pass_count} | {pass_to_fail_count} | {mean_score_difference} | {total_tasks} |".format(
                **summary
            )
        )

    markdown_lines.extend(
        [
            "",
            "| split | task_category | fail_to_pass_count | pass_to_fail_count |",
            "| --- | --- | ---: | ---: |",
        ]
    )
    for row in flip_categories:
        markdown_lines.append(
            "| {split} | {task_category} | {fail_to_pass_count} | {pass_to_fail_count} |".format(
                **row
            )
        )

    markdown_lines.extend(
        [
            "",
            "## Calibration Note",
            "",
            f"Drifted ruler was locked before held-out evaluation. Source manifest: `{flip_manifest['drifted_proxy_path']}`",
            "",
        ]
    )
    write_text(md_path, "\n".join(markdown_lines))
    print(relpath(csv_path))
    print(relpath(md_path))


if __name__ == "__main__":
    main()

