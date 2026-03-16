from __future__ import annotations

import argparse
import pathlib
import random
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from common import (  # noqa: E402
    iter_records,
    load_jsonl,
    make_output_path,
    utc_now_iso,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the delayed-audit comparison between proxy admission and strict verification.")
    parser.add_argument("--strict", required=True, type=pathlib.Path, help="Strict evaluation JSONL.")
    parser.add_argument("--proxy", required=True, type=pathlib.Path, help="Proxy evaluation JSONL.")
    parser.add_argument("--condition-label", help="Override the condition label.")
    parser.add_argument("--audit-sample-size", type=int, default=5, help="Optional random audit sample among proxy-passing items.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for the audit sample.")
    parser.add_argument("--output", type=pathlib.Path, help="Explicit output JSONL path.")
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
        raise SystemExit("No overlapping task ids between strict and proxy evaluations.")

    condition = args.condition_label or str(proxy_manifest["condition"])
    output_path = args.output or make_output_path("audits", f"audit__{condition}")
    audit_id = output_path.stem

    proxy_passing_ids = [task_id for task_id in shared_task_ids if proxy_by_task[task_id]["proxy_pass"]]
    audit_sample_size = max(0, min(args.audit_sample_size, len(proxy_passing_ids)))
    rng = random.Random(args.seed)
    audited_task_ids = set(rng.sample(proxy_passing_ids, audit_sample_size)) if audit_sample_size else set()

    audit_records: list[dict[str, object]] = []
    strict_passes = 0
    proxy_passes = 0
    disagreements = 0
    challenge_failures = 0
    audited_true_positives = 0

    for task_id in shared_task_ids:
        strict_pass = bool(strict_by_task[task_id]["strict_pass"])
        proxy_pass = bool(proxy_by_task[task_id]["proxy_pass"])
        disagreement = strict_pass != proxy_pass
        challenge_failure = proxy_pass and not strict_pass
        audited = task_id in audited_task_ids

        strict_passes += int(strict_pass)
        proxy_passes += int(proxy_pass)
        disagreements += int(disagreement)
        challenge_failures += int(challenge_failure)
        if audited and strict_pass:
            audited_true_positives += 1

        audit_records.append(
            {
                "record_type": "audit_result",
                "audit_id": audit_id,
                "condition": condition,
                "task_id": task_id,
                "strict_pass": strict_pass,
                "proxy_pass": proxy_pass,
                "disagreement": disagreement,
                "challenge_failure": challenge_failure,
                "audited": audited,
            }
        )

    audited_precision = round(audited_true_positives / audit_sample_size, 4) if audit_sample_size else None
    records: list[dict[str, object]] = [
        {
            "record_type": "audit_manifest",
            "audit_id": audit_id,
            "condition": condition,
            "runtime_timestamp_utc": utc_now_iso(),
            "strict_eval_path": str(args.strict),
            "proxy_eval_path": str(args.proxy),
            "strict_source_condition": strict_manifest["condition"],
            "proxy_source_condition": proxy_manifest["condition"],
            "proxy_profile": proxy_manifest["proxy_profile"],
            "total_tasks": len(shared_task_ids),
            "strict_pass_count": strict_passes,
            "strict_rate": round(strict_passes / len(shared_task_ids), 4),
            "proxy_pass_count": proxy_passes,
            "proxy_rate": round(proxy_passes / len(shared_task_ids), 4),
            "disagreement_count": disagreements,
            "challenge_failure_count": challenge_failures,
            "audit_sample_size": audit_sample_size,
            "audit_sample_seed": args.seed,
            "audited_precision": audited_precision,
        }
    ]
    records.extend(audit_records)
    write_jsonl(output_path, records)
    print(output_path)


if __name__ == "__main__":
    main()
