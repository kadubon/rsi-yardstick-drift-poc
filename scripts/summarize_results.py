from __future__ import annotations

import argparse
import csv
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from common import (  # noqa: E402
    iter_records,
    load_jsonl,
    make_output_path,
    utc_timestamp,
    write_text,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize audit outputs into CSV and Markdown.")
    parser.add_argument("--audits", nargs="+", required=True, type=pathlib.Path, help="Audit JSONL files.")
    parser.add_argument("--output-stem", help="Optional stem for the CSV and Markdown outputs.")
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    stem = args.output_stem or f"condition_summary__{utc_timestamp()}"
    csv_path = make_output_path("summaries", "condition_summary", stem=stem, suffix=".csv")
    md_path = make_output_path("summaries", "condition_summary", stem=stem, suffix=".md")

    rows: list[dict[str, object]] = []
    for audit_path in args.audits:
        records = load_jsonl(audit_path)
        manifest = iter_records(records, "audit_manifest")[0]
        rows.append(
            {
                "condition": manifest["condition"],
                "proxy_profile": manifest["proxy_profile"],
                "total_tasks": manifest["total_tasks"],
                "strict_score": manifest["strict_rate"],
                "proxy_score": manifest["proxy_rate"],
                "disagreement_count": manifest["disagreement_count"],
                "challenge_failure_count": manifest["challenge_failure_count"],
                "audit_sample_size": manifest["audit_sample_size"],
                "audited_precision": manifest["audited_precision"],
                "audit_file": str(audit_path),
            }
        )

    rows.sort(key=lambda row: row["condition"])
    fieldnames = [
        "condition",
        "proxy_profile",
        "total_tasks",
        "strict_score",
        "proxy_score",
        "disagreement_count",
        "challenge_failure_count",
        "audit_sample_size",
        "audited_precision",
        "audit_file",
    ]

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    markdown_lines = [
        "# Condition Summary",
        "",
        "| condition | proxy_profile | total_tasks | strict_score | proxy_score | disagreement_count | challenge_failure_count | audit_sample_size | audited_precision |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |",
    ]
    for row in rows:
        markdown_lines.append(
            "| {condition} | {proxy_profile} | {total_tasks} | {strict_score} | {proxy_score} | {disagreement_count} | {challenge_failure_count} | {audit_sample_size} | {audited_precision} |".format(
                **row
            )
        )

    write_text(md_path, "\n".join(markdown_lines) + "\n")
    print(csv_path)
    print(md_path)


if __name__ == "__main__":
    main()
