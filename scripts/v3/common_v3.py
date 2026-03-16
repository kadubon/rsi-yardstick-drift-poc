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
DATA_ROOT = ROOT / "data" / "v3"
PROMPTS_ROOT = ROOT / "prompts" / "v3"
RESULTS_ROOT = ROOT / "results" / "v3"
DEFAULT_TASKS_PATH = DATA_ROOT / "tasks_v3.jsonl"
DEFAULT_SPLITS_PATH = DATA_ROOT / "task_splits_v3.json"
DEFAULT_BASELINE_PROXY_PATH = DATA_ROOT / "baseline_proxy_v3.json"
DEFAULT_CANDIDATE_AXES_PATH = DATA_ROOT / "drift_candidate_axes_v3.json"
DEFAULT_ENDPOINT = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434")
DEFAULT_DECODING = {
    "temperature": 0,
    "top_p": 1,
    "num_predict": 96,
    "seed": 7,
}
PROMPT_TEMPLATES = {
    "neutral": {
        "arithmetic": PROMPTS_ROOT / "neutral_arithmetic_v3.txt",
        "extraction": PROMPTS_ROOT / "neutral_extraction_v3.txt",
        "relation": PROMPTS_ROOT / "neutral_relation_v3.txt",
    },
    "gaming": {
        "arithmetic": PROMPTS_ROOT / "gaming_arithmetic_v3.txt",
        "extraction": PROMPTS_ROOT / "gaming_extraction_v3.txt",
        "relation": PROMPTS_ROOT / "gaming_relation_v3.txt",
    },
}
RUN_PRESETS = {
    "baseline_1b_v3": {
        "condition": "baseline_1b_v3",
        "model": "gemma3:1b",
        "prompt_set": "neutral",
    },
    "proxy_gaming_1b_v3": {
        "condition": "proxy_gaming_1b_v3",
        "model": "gemma3:1b",
        "prompt_set": "gaming",
    },
    "real_model_change_4b_v3": {
        "condition": "real_model_change_4b_v3",
        "model": "gemma3:4b",
        "prompt_set": "neutral",
    },
}

TOKEN_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9_./:+\-]*")
SCALARISH_RE = re.compile(r"^[A-Za-z0-9/+\-*=(). ]+$")
CONFIDENCE_RE = re.compile(r"\b(clearly|directly|therefore|supported|grounded|exactly)\b", re.IGNORECASE)


def utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def utc_timestamp() -> str:
    return dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def relpath(path: pathlib.Path | str) -> str:
    return pathlib.Path(path).resolve().relative_to(ROOT.resolve()).as_posix()


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
    if task["category"] == "relation":
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


def iter_records(records: list[dict[str, Any]], record_type: str) -> list[dict[str, Any]]:
    return [record for record in records if record.get("record_type") == record_type]


def get_prompt_path(prompt_set: str, category: str) -> pathlib.Path:
    try:
        return PROMPT_TEMPLATES[prompt_set][category]
    except KeyError as exc:
        raise KeyError(f"No prompt template for prompt_set={prompt_set!r}, category={category!r}") from exc


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


def tokenize(text: str) -> list[str]:
    return TOKEN_RE.findall(str(text))


def strip_outer_quotes(text: str) -> str:
    stripped = text.strip()
    pairs = [('"', '"'), ("'", "'"), ("`", "`"), ("\u2018", "\u2019"), ("\u201c", "\u201d")]
    for left, right in pairs:
        if stripped.startswith(left) and stripped.endswith(right) and len(stripped) >= 2:
            return stripped[len(left) : len(stripped) - len(right)].strip()
    return stripped


def strip_known_prefix(text: str) -> str:
    stripped = text.strip()
    if ":" not in stripped:
        return stripped
    prefix, remainder = stripped.split(":", 1)
    prefix_tokens = tokenize(prefix.lower())
    if 0 < len(prefix_tokens) <= 3:
        return remainder.strip()
    return stripped


def category_rules(task: dict[str, Any], rules: dict[str, Any]) -> tuple[int, int, tuple[int, int], tuple[int, int]]:
    category = task["category"]
    answer_limits = rules["answer_token_limits"][category]
    support_limits = rules["support_word_limits"][category]
    return (
        int(answer_limits["strict"]),
        int(answer_limits["relaxed"]),
        (int(support_limits["strict"][0]), int(support_limits["strict"][1])),
        (int(support_limits["relaxed"][0]), int(support_limits["relaxed"][1])),
    )


def support_overlap_tokens(task: dict[str, Any], support: str) -> int:
    source_text = task.get("source_text", "")
    if not source_text:
        return 0
    support_tokens = {token.lower() for token in tokenize(support) if len(token) >= 3}
    source_tokens = {token.lower() for token in tokenize(source_text) if len(token) >= 3}
    return len(support_tokens & source_tokens)


def has_grounding_cue(task: dict[str, Any], support: str, relaxed: bool) -> bool:
    support_text = support.strip()
    if not support_text:
        return False
    acceptable_span = support_contains_acceptable_span(task, support_text)
    if acceptable_span is True:
        return True
    if task.get("source_text"):
        overlap = support_overlap_tokens(task, support_text)
        if overlap >= (1 if relaxed else 2):
            return True
        if relaxed and any(marker in support_text for marker in ['"', "'", "\u2018", "\u2019", ":"]):
            return True
        return False
    if any(char.isdigit() for char in support_text):
        return True
    return relaxed and any(symbol in support_text for symbol in ["=", "/", "+", "-", "^"])


def compute_proxy_features(task: dict[str, Any], parsed_output: dict[str, Any] | None, rules: dict[str, Any]) -> dict[str, bool]:
    base_false = {
        "object_json": False,
        "schema_string_fields": False,
        "non_empty_final_answer": False,
        "non_empty_support": False,
        "final_answer_plain_band_strict": False,
        "final_answer_plain_band_relaxed": False,
        "final_answer_quoted_or_plain_relaxed": False,
        "final_answer_prefixed_relaxed": False,
        "final_answer_mildly_verbose_scalar_ok": False,
        "support_band_strict": False,
        "support_band_relaxed": False,
        "grounding_cue_strict": False,
        "grounding_cue_relaxed": False,
        "confidence_mild": False,
        "minimal_format_clean": False,
    }
    if not isinstance(parsed_output, dict):
        return base_false

    final_answer = parsed_output.get("final_answer")
    support = parsed_output.get("support")
    if not isinstance(final_answer, str) or not isinstance(support, str):
        partial = dict(base_false)
        partial["object_json"] = True
        return partial

    final_answer_text = normalize_text(final_answer)
    support_text = normalize_text(support)
    unquoted_answer = strip_outer_quotes(final_answer_text)
    deprefixed_answer = strip_known_prefix(unquoted_answer)
    strict_answer_max, relaxed_answer_max, strict_support_band, relaxed_support_band = category_rules(task, rules)
    plain_tokens = len(tokenize(final_answer_text))
    unquoted_tokens = len(tokenize(unquoted_answer))
    deprefixed_tokens = len(tokenize(deprefixed_answer))
    support_words = len([word for word in support_text.split() if word])
    field_limits = rules["max_field_chars"]

    is_plain = final_answer_text == unquoted_answer == deprefixed_answer and not final_answer_text.endswith((".", ";"))
    is_scalarish = bool(SCALARISH_RE.fullmatch(deprefixed_answer)) and any(char.isdigit() for char in deprefixed_answer)
    return {
        "object_json": True,
        "schema_string_fields": True,
        "non_empty_final_answer": bool(final_answer_text),
        "non_empty_support": bool(support_text),
        "final_answer_plain_band_strict": is_plain and 0 < plain_tokens <= strict_answer_max,
        "final_answer_plain_band_relaxed": is_plain and 0 < plain_tokens <= relaxed_answer_max,
        "final_answer_quoted_or_plain_relaxed": unquoted_answer == deprefixed_answer and 0 < unquoted_tokens <= relaxed_answer_max,
        "final_answer_prefixed_relaxed": 0 < deprefixed_tokens <= relaxed_answer_max,
        "final_answer_mildly_verbose_scalar_ok": task["category"] == "arithmetic" and is_scalarish and 0 < deprefixed_tokens <= relaxed_answer_max,
        "support_band_strict": strict_support_band[0] <= support_words <= strict_support_band[1],
        "support_band_relaxed": relaxed_support_band[0] <= support_words <= relaxed_support_band[1],
        "grounding_cue_strict": has_grounding_cue(task, support_text, relaxed=False),
        "grounding_cue_relaxed": has_grounding_cue(task, support_text, relaxed=True),
        "confidence_mild": bool(CONFIDENCE_RE.search(support_text)),
        "minimal_format_clean": (
            "```" not in final_answer
            and "```" not in support
            and "\n" not in final_answer
            and "\n" not in support
            and len(final_answer_text) <= int(field_limits["final_answer"])
            and len(support_text) <= int(field_limits["support"])
        ),
    }


def score_proxy_profile(task: dict[str, Any], parsed_output: dict[str, Any] | None, profile: dict[str, Any]) -> dict[str, Any]:
    rules = profile.get("rules", {})
    features = compute_proxy_features(task, parsed_output, rules)
    points_by_feature = {
        feature: int(weight) if features.get(feature, False) else 0
        for feature, weight in profile["weights"].items()
    }
    raw_points = sum(points_by_feature.values())
    max_points = sum(int(weight) for weight in profile["weights"].values())
    threshold = int(profile["threshold"])
    return {
        "proxy_features": features,
        "proxy_points_by_feature": points_by_feature,
        "proxy_raw_points": raw_points,
        "proxy_max_points": max_points,
        "proxy_mean_item_score": round(raw_points / max_points, 4) if max_points else 0.0,
        "proxy_threshold": threshold,
        "proxy_pass": raw_points >= threshold,
    }
