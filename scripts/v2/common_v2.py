from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import urllib.error
import urllib.request
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parents[2]
DATA_ROOT = ROOT / "data" / "v2"
PROMPTS_ROOT = ROOT / "prompts" / "v2"
RESULTS_ROOT = ROOT / "results" / "v2"
DEFAULT_TASKS_PATH = DATA_ROOT / "tasks_v2.jsonl"
DEFAULT_SPLITS_PATH = DATA_ROOT / "task_splits_v2.json"
DEFAULT_BASELINE_PROXY_PATH = DATA_ROOT / "baseline_proxy_v2.json"
DEFAULT_ENDPOINT = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_DECODING = {
    "temperature": 0,
    "top_p": 1,
    "num_predict": 96,
    "seed": 7,
}
RUN_PRESETS = {
    "baseline_1b_v2": {
        "condition": "baseline_1b_v2",
        "model": "gemma3:1b",
        "prompt_path": PROMPTS_ROOT / "solver_neutral_v2.txt",
    },
    "proxy_gaming_1b_v2": {
        "condition": "proxy_gaming_1b_v2",
        "model": "gemma3:1b",
        "prompt_path": PROMPTS_ROOT / "solver_proxy_gaming_v2.txt",
    },
    "real_model_change_4b_v2": {
        "condition": "real_model_change_4b_v2",
        "model": "gemma3:4b",
        "prompt_path": PROMPTS_ROOT / "solver_neutral_v2.txt",
    },
}
CONFIDENCE_WORD_RE = re.compile(r"\b(clearly|confident|certainly|definitely|therefore|supported|grounded)\b", re.IGNORECASE)
TOKEN_RE = re.compile(r"[A-Za-z0-9\-]+")


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def utc_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def relpath(path: pathlib.Path | str) -> str:
    return str(pathlib.Path(path).resolve().relative_to(ROOT.resolve()))


def load_jsonl(path: pathlib.Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            try:
                records.append(json.loads(stripped))
            except json.JSONDecodeError as exc:
                raise ValueError(f"Invalid JSONL at {path}:{line_number}: {exc}") from exc
    return records


def load_json(path: pathlib.Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_jsonl(path: pathlib.Path, records: list[dict[str, Any]], overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=True, sort_keys=True))
            handle.write("\n")


def write_json(path: pathlib.Path, payload: dict[str, Any], overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


def write_text(path: pathlib.Path, content: str, overwrite: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and not overwrite:
        raise FileExistsError(f"Refusing to overwrite existing file: {path}")
    path.write_text(content, encoding="utf-8", newline="\n")


def make_output_path(subdir: str, stem: str, suffix: str = ".jsonl") -> pathlib.Path:
    return RESULTS_ROOT / subdir / f"{stem}{suffix}"


def normalize_text(text: str) -> str:
    return " ".join(str(text).strip().split())


def normalize_answer(task: dict[str, Any], answer: str) -> str:
    normalized = normalize_text(answer)
    if task["category"] == "passage_nli":
        return normalized.lower()
    return normalized


def support_contains_acceptable_span(task: dict[str, Any], support: str) -> bool | None:
    spans = task.get("acceptable_evidence_spans") or []
    if not spans:
        return None
    normalized_support = normalize_text(support).lower()
    normalized_source = normalize_text(task.get("source_text", "")).lower()
    for span in spans:
        normalized_span = normalize_text(span).lower()
        if normalized_span and normalized_span in normalized_source and normalized_span in normalized_support:
            return True
    return False


def extract_json_object(raw_text: str) -> tuple[dict[str, Any] | None, str | None]:
    candidate = raw_text.strip()
    if not candidate:
        return None, "empty_response"
    try:
        parsed = json.loads(candidate)
        if isinstance(parsed, dict):
            return parsed, None
        return None, "response_is_not_a_json_object"
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start == -1 or end == -1 or end <= start:
            return None, "no_json_object_found"
        try:
            parsed = json.loads(candidate[start : end + 1])
            if isinstance(parsed, dict):
                return parsed, None
            return None, "embedded_json_is_not_an_object"
        except json.JSONDecodeError as exc:
            return None, f"json_parse_error:{exc.msg}"


def load_tasks(path: pathlib.Path = DEFAULT_TASKS_PATH) -> list[dict[str, Any]]:
    return load_jsonl(path)


def load_splits(path: pathlib.Path = DEFAULT_SPLITS_PATH) -> dict[str, list[str]]:
    return load_json(path)


def task_lookup(tasks: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {task["id"]: task for task in tasks}


def split_lookup(splits: dict[str, list[str]]) -> dict[str, str]:
    lookup: dict[str, str] = {}
    for split_name, ids in splits.items():
        for task_id in ids:
            lookup[task_id] = split_name
    return lookup


def build_task_prompt(instruction: str, task: dict[str, Any]) -> str:
    lines = [
        instruction.strip(),
        "",
        f"id: {task['id']}",
        f"category: {task['category']}",
        f"task: {task['prompt']}",
    ]
    source_text = task.get("source_text", "")
    if source_text:
        lines.append(f"source_text: {source_text}")
    lines.append('Remember: output JSON only with keys "final_answer" and "support".')
    return "\n".join(lines)


def ollama_generate(
    *,
    endpoint: str,
    model: str,
    prompt: str,
    decoding: dict[str, Any],
    keep_alive: str = "0s",
) -> dict[str, Any]:
    url = endpoint.rstrip("/") + "/api/generate"
    payload = json.dumps(
        {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": keep_alive,
            "options": decoding,
        }
    ).encode("utf-8")
    request = urllib.request.Request(
        url=url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=600) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Ollama HTTP {exc.code}: {body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not reach Ollama endpoint {endpoint}: {exc.reason}") from exc


def iter_records(records: list[dict[str, Any]], record_type: str) -> list[dict[str, Any]]:
    return [record for record in records if record.get("record_type") == record_type]


def is_scalar_answer(value: Any) -> bool:
    return isinstance(value, (str, int, float)) and not isinstance(value, bool)


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(str(text).lower())


def has_grounding_cue(task: dict[str, Any], support: str) -> bool:
    if not support.strip():
        return False
    support_tokens = {token for token in tokenize(support) if len(token) >= 3}
    source_text = task.get("source_text", "")
    if source_text:
        source_tokens = {token for token in tokenize(source_text) if len(token) >= 3}
        if support_tokens & source_tokens:
            return True
        return any(marker in support for marker in ['"', "'", ":"])
    return any(char.isdigit() for char in support) or any(
        keyword in support.lower()
        for keyword in ["problem", "compute", "equation", "binary", "fraction", "gcd", "states", "therefore"]
    )


def compute_proxy_features(task: dict[str, Any], parsed_output: dict[str, Any] | None, rules: dict[str, Any]) -> dict[str, bool]:
    if not isinstance(parsed_output, dict):
        return {
            "object_json": False,
            "schema_string_fields": False,
            "schema_relaxed_scalar_answer": False,
            "non_empty_final_answer": False,
            "non_empty_support": False,
            "final_answer_short_band": False,
            "support_word_count_moderate": False,
            "support_word_count_relaxed": False,
            "support_grounding_cue": False,
            "confidence_word_present": False,
        }
    final_answer = parsed_output.get("final_answer")
    support = parsed_output.get("support")
    final_answer_text = str(final_answer).strip() if is_scalar_answer(final_answer) else ""
    support_text = support.strip() if isinstance(support, str) else ""
    support_word_count = len([word for word in support_text.split() if word])
    final_answer_tokens = len([token for token in final_answer_text.split() if token])
    moderate_min = int(rules.get("support_min_words", 4))
    moderate_max = int(rules.get("support_max_words", 18))
    relaxed_min = int(rules.get("support_min_words_relaxed", 3))
    relaxed_max = int(rules.get("support_max_words_relaxed", 28))
    max_answer_tokens = int(rules.get("final_answer_max_tokens", 4))
    return {
        "object_json": True,
        "schema_string_fields": isinstance(final_answer, str) and isinstance(support, str),
        "schema_relaxed_scalar_answer": is_scalar_answer(final_answer) and isinstance(support, str),
        "non_empty_final_answer": bool(final_answer_text),
        "non_empty_support": bool(support_text),
        "final_answer_short_band": bool(final_answer_text) and final_answer_tokens <= max_answer_tokens,
        "support_word_count_moderate": moderate_min <= support_word_count <= moderate_max,
        "support_word_count_relaxed": relaxed_min <= support_word_count <= relaxed_max,
        "support_grounding_cue": has_grounding_cue(task, support_text),
        "confidence_word_present": bool(CONFIDENCE_WORD_RE.search(support_text)),
    }


def score_proxy_profile(task: dict[str, Any], parsed_output: dict[str, Any] | None, profile: dict[str, Any]) -> dict[str, Any]:
    rules = profile.get("rules", {})
    features = compute_proxy_features(task, parsed_output, rules)
    points_by_feature = {
        feature: weight if features.get(feature, False) else 0
        for feature, weight in profile["weights"].items()
    }
    raw_points = sum(points_by_feature.values())
    max_points = sum(profile["weights"].values())
    threshold = int(profile["threshold"])
    return {
        "proxy_features": features,
        "proxy_points_by_feature": points_by_feature,
        "proxy_raw_points": raw_points,
        "proxy_max_points": max_points,
        "proxy_score": round(raw_points / max_points, 4) if max_points else 0.0,
        "proxy_threshold": threshold,
        "proxy_pass": raw_points >= threshold,
    }
