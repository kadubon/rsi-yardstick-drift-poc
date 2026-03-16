from __future__ import annotations

import argparse
import pathlib
import sys

SCRIPT_DIR = pathlib.Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.append(str(SCRIPT_DIR))

from common import (  # noqa: E402
    DEFAULT_DECODING,
    DEFAULT_ENDPOINT,
    DEFAULT_TASKS_PATH,
    RUN_PRESETS,
    build_task_prompt,
    extract_json_object,
    filter_tasks,
    load_jsonl,
    make_output_path,
    ollama_generate,
    sha256_text,
    utc_now_iso,
    write_jsonl,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local Ollama solver conditions and save raw outputs as JSONL.")
    parser.add_argument("--preset", choices=sorted(RUN_PRESETS), help="Named solver condition to run.")
    parser.add_argument("--tasks", type=pathlib.Path, default=DEFAULT_TASKS_PATH, help="Path to tasks JSONL.")
    parser.add_argument("--prompt", type=pathlib.Path, help="Prompt template path.")
    parser.add_argument("--model", help="Ollama model tag.")
    parser.add_argument("--condition-label", help="Condition label for outputs.")
    parser.add_argument("--endpoint", default=DEFAULT_ENDPOINT, help="Ollama endpoint.")
    parser.add_argument("--temperature", type=float, default=DEFAULT_DECODING["temperature"])
    parser.add_argument("--top-p", type=float, default=DEFAULT_DECODING["top_p"])
    parser.add_argument("--num-predict", type=int, default=DEFAULT_DECODING["num_predict"])
    parser.add_argument("--seed", type=int, default=DEFAULT_DECODING["seed"])
    parser.add_argument("--task-ids", help="Comma-separated subset of task ids.")
    parser.add_argument("--limit", type=int, help="Limit the number of tasks.")
    parser.add_argument("--output", type=pathlib.Path, help="Explicit output JSONL path.")
    return parser.parse_args()


def resolve_config(args: argparse.Namespace) -> tuple[str, str, pathlib.Path]:
    if args.preset:
        preset = RUN_PRESETS[args.preset]
        condition = args.condition_label or preset["condition"]
        model = args.model or preset["model"]
        prompt_path = args.prompt or preset["prompt_path"]
        return condition, model, pathlib.Path(prompt_path)
    if not args.model or not args.prompt:
        raise SystemExit("Either --preset or both --model and --prompt are required.")
    return args.condition_label or "custom_condition", args.model, pathlib.Path(args.prompt)


def main() -> None:
    args = parse_args()
    condition, model, prompt_path = resolve_config(args)
    tasks = load_jsonl(args.tasks)
    task_ids = [item.strip() for item in args.task_ids.split(",")] if args.task_ids else None
    selected_tasks = filter_tasks(tasks, task_ids=task_ids, limit=args.limit)
    if not selected_tasks:
        raise SystemExit("No tasks selected.")

    instruction = prompt_path.read_text(encoding="utf-8").strip()
    decoding = {
        "temperature": args.temperature,
        "top_p": args.top_p,
        "num_predict": args.num_predict,
        "seed": args.seed,
    }
    output_path = args.output or make_output_path("raw", condition)
    run_id = output_path.stem

    records: list[dict[str, object]] = [
        {
            "record_type": "run_manifest",
            "run_id": run_id,
            "condition": condition,
            "runtime_timestamp_utc": utc_now_iso(),
            "model_tag": model,
            "prompt_template_name": prompt_path.name,
            "prompt_template_path": str(prompt_path.relative_to(prompt_path.parents[1])),
            "prompt_template_sha256": sha256_text(instruction),
            "decoding": decoding,
            "ollama_endpoint": args.endpoint,
            "tasks_path": str(args.tasks.relative_to(args.tasks.parents[1])),
            "task_ids": [task["id"] for task in selected_tasks],
            "notes": "keep_alive=0s is used to minimize lingering local model state after each request.",
        }
    ]

    for task in selected_tasks:
        rendered_prompt = build_task_prompt(instruction, task)
        response = ollama_generate(
            endpoint=args.endpoint,
            model=model,
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
                "condition": condition,
                "runtime_timestamp_utc": utc_now_iso(),
                "task_id": task["id"],
                "task_category": task["category"],
                "model_tag": model,
                "prompt_template_name": prompt_path.name,
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
    print(output_path)


if __name__ == "__main__":
    main()
