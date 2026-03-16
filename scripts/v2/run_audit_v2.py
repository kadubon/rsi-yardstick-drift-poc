from __future__ import annotations

import argparse
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
    utc_now_iso,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run v2 delayed strict audit for a condition/proxy pair.")
    parser.add_argument("--strict", required=True, type=pathlib.Path)
    parser.add_argument("--proxy", required=True, type=pathlib.Path)
    parser.add_argument("--output", type=pathlib.Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    strict_records = load_jsonl(args.strict)
    proxy_records = load_jsonl(args.proxy)
    strict_manifest = iter_records(strict_records, "strict_manifest")[0]
    proxy_manifest = iter_records(proxy_records, "proxy_manifest")[0]
    strict_by_task = {record["task_id"]: record for record in iter_records(strict_records, "strict_eval")}
    proxy_by_task = {record["task_id"]: record for record in iter_records(proxy_records, "proxy_eval")}
    shared_task_ids = sorted(set(strict_by_task) & set(proxy_by_task))
    if not shared_task_ids:
        raise SystemExit("No overlapping task ids between strict and proxy inputs.")

    condition = str(proxy_manifest["condition"])
    proxy_label = str(proxy_manifest["proxy_profile"])
    experiment_tag = str(proxy_manifest["experiment_tag"])
    output_path = args.output or make_output_path("audits", f"audit__{condition}__{proxy_label}__{experiment_tag}")
    audit_id = output_path.stem

    split_stats = {
        "calibration": {"strict": 0, "proxy": 0, "confirmed": 0, "disagreement": 0, "challenge": 0, "total": 0},
        "evaluation": {"strict": 0, "proxy": 0, "confirmed": 0, "disagreement": 0, "challenge": 0, "total": 0},
    }
    task_records: list[dict[str, object]] = []
    for task_id in shared_task_ids:
        strict_pass = bool(strict_by_task[task_id]["strict_pass"])
        proxy_pass = bool(proxy_by_task[task_id]["proxy_pass"])
        strict_confirmed = strict_pass and proxy_pass
        disagreement = strict_pass != proxy_pass
        challenge_failure = proxy_pass and (not strict_pass)
        split_name = str(proxy_by_task[task_id]["split"])
        split_stats[split_name]["strict"] += int(strict_pass)
        split_stats[split_name]["proxy"] += int(proxy_pass)
        split_stats[split_name]["confirmed"] += int(strict_confirmed)
        split_stats[split_name]["disagreement"] += int(disagreement)
        split_stats[split_name]["challenge"] += int(challenge_failure)
        split_stats[split_name]["total"] += 1
        task_records.append(
            {
                "record_type": "audit_task",
                "audit_id": audit_id,
                "condition": condition,
                "proxy_profile": proxy_label,
                "task_id": task_id,
                "split": split_name,
                "task_category": proxy_by_task[task_id]["task_category"],
                "strict_pass": strict_pass,
                "proxy_pass": proxy_pass,
                "strict_confirmed": strict_confirmed,
                "disagreement": disagreement,
                "challenge_failure": challenge_failure,
            }
        )

    records: list[dict[str, object]] = [
        {
            "record_type": "audit_manifest",
            "audit_id": audit_id,
            "condition": condition,
            "proxy_profile": proxy_label,
            "runtime_timestamp_utc": utc_now_iso(),
            "experiment_tag": experiment_tag,
            "strict_eval_path": relpath(args.strict),
            "proxy_eval_path": relpath(args.proxy),
            "strict_source_condition": strict_manifest["condition"],
            "proxy_source_condition": proxy_manifest["condition"],
        }
    ]
    for split_name, stats in split_stats.items():
        proxy_admitted = int(stats["proxy"])
        strict_confirmed = int(stats["confirmed"])
        total = int(stats["total"])
        records.append(
            {
                "record_type": "audit_split_summary",
                "audit_id": audit_id,
                "condition": condition,
                "proxy_profile": proxy_label,
                "split": split_name,
                "strict_score": round(int(stats["strict"]) / total, 4) if total else 0.0,
                "proxy_score": round(proxy_admitted / total, 4) if total else 0.0,
                "binary_admission_count": proxy_admitted,
                "proxy_admitted_count": proxy_admitted,
                "strict_confirmed_count": strict_confirmed,
                "challenge_failure_count": int(stats["challenge"]),
                "disagreement_count": int(stats["disagreement"]),
                "audited_precision": round(strict_confirmed / proxy_admitted, 4) if proxy_admitted else None,
                "total_tasks": total,
            }
        )
    records.extend(task_records)
    write_jsonl(output_path, records)
    print(relpath(output_path))


if __name__ == "__main__":
    main()

