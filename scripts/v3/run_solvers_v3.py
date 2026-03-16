from __future__ import annotations

import argparse
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from common_v3 import (  # noqa: E402
    DEFAULT_DECODING,
    DEFAULT_ENDPOINT,
    DEFAULT_SPLITS_PATH,
    DEFAULT_TASKS_PATH,
    RUN_PRESETS,
    build_task_prompt,
    extract_json_object,
    get_prompt_path,
    load_splits,
    load_tasks,
    make_output_path,
    ollama_generate,
    relpath,
    sha256_text,
    split_lookup,
    utc_now_iso,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run v3 solver conditions with category-conditioned prompts and local Ollama.")
    parser.add_argument("--preset", choices=sorted(RUN_PRESETS), required=True)
    parser.add_argument("--tasks", type=pathlib.Path, default=DEFAULT_TASKS_PATH)
    parser.add_argument("--splits", type=pathlib.Path, default=DEFAULT_SPLITS_PATH)
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT)
    parser.add_argument("--temperature", type=float, default=DEFAULT_DECODING["temperature"])
    parser.add_argument("--top-p", type=float, default=DEFAULT_DECODING["top_p"])
    parser.add_argument("--num-predict", type=int, default=DEFAULT_DECODING["num_predict"])
    parser.add_argument("--seed", type=int, default=DEFAULT_DECODING["seed"])
    parser.add_argument("--experiment-tag", required=True)
    parser.add_argument("--output", type=pathlib.Path)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    preset = RUN_PRESETS[args.preset]
    tasks = load_tasks(args.tasks)
    split_by_id = split_lookup(load_splits(args.splits))
    decoding = {
        "temperature": args.temperature,
        "top_p": args.top_p,
        "num_predict": args.num_predict,
        "seed": args.seed,
    }
    output_path = args.output or make_output_path("raw", f"{preset['condition']}__{args.experiment_tag}")
    run_id = output_path.stem

    prompt_manifest: dict[str, dict[str, str]] = {}
    prompt_cache: dict[tuple[str, str], str] = {}
    for category in sorted({task["category"] for task in tasks}):
        prompt_path = get_prompt_path(preset["prompt_set"], category)
        instruction = prompt_path.read_text(encoding="utf-8").strip()
        prompt_cache[(preset["prompt_set"], category)] = instruction
        prompt_manifest[category] = {
            "prompt_template_name": prompt_path.name,
            "prompt_template_path": relpath(prompt_path),
            "prompt_template_sha256": sha256_text(instruction),
        }

    records: list[dict[str, object]] = [
        {
            "record_type": "run_manifest",
            "run_id": run_id,
            "condition": preset["condition"],
            "runtime_timestamp_utc": utc_now_iso(),
            "experiment_tag": args.experiment_tag,
            "model_tag": preset["model"],
            "prompt_set": preset["prompt_set"],
            "prompt_templates": prompt_manifest,
            "decoding": decoding,
            "ollama_endpoint": args.endpoint,
            "tasks_path": relpath(args.tasks),
            "splits_path": relpath(args.splits),
            "task_ids": [task["id"] for task in tasks],
            "notes": "v3 run with category-conditioned prompt contracts and keep_alive=0s.",
        }
    ]

    for task in tasks:
        prompt_path = get_prompt_path(preset["prompt_set"], task["category"])
        instruction = prompt_cache[(preset["prompt_set"], task["category"])]
        rendered_prompt = build_task_prompt(instruction, task)
        response = ollama_generate(
            endpoint=args.endpoint,
            model=preset["model"],
            prompt=rendered_prompt,
            decoding=decoding,
            keep_alive="0s",
        )
        raw_text = response.get("response", "")
        parsed_output, parse_error = extract_json_object(raw_text)
        records.append(
            {
                "record_type": "solver_output",
                "run_id": run_id,
                "condition": preset["condition"],
                "experiment_tag": args.experiment_tag,
                "runtime_timestamp_utc": utc_now_iso(),
                "task_id": task["id"],
                "split": split_by_id[task["id"]],
                "task_category": task["category"],
                "model_tag": preset["model"],
                "prompt_set": preset["prompt_set"],
                "prompt_template_name": prompt_path.name,
                "prompt_template_path": relpath(prompt_path),
                "decoding": decoding,
                "ollama_endpoint": args.endpoint,
                "rendered_prompt": rendered_prompt,
                "raw_response_text": raw_text,
                "parsed_output": parsed_output,
                "parse_error": parse_error,
                "ollama_response_meta": {key: value for key, value in response.items() if key != "response"},
            }
        )

    write_jsonl(output_path, records)
    print(relpath(output_path))


if __name__ == "__main__":
    main()
