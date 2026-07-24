"""Pure, testable helpers used by the agent's LangSmith evaluators."""

import json
import re
from collections.abc import Iterable
from typing import Any

MIN_SCORE = 0.0
MAX_SCORE = 1.0
_NUMBER_PATTERN = re.compile(r"[-+]?\d*\.?\d+")
_JSON_OBJECT_PATTERN = re.compile(r"\{.*\}", re.DOTALL)
QUALITY_KEYS = ("clarity", "correctness", "on_topic", "user_friendly")


def parse_judge_score(text: str) -> float:
    """Extract a 0..1 quality score from the judge LLM's free-text reply.

    The judge is asked to answer with a single number, but LLMs often wrap it
    in prose ("Score: 0.8"). This takes the first numeric token found and
    clamps it to `[MIN_SCORE, MAX_SCORE]`, falling back to `MIN_SCORE` when the
    reply has no parseable number.
    """
    match = _NUMBER_PATTERN.search(text)
    if match is None:
        return MIN_SCORE
    return max(MIN_SCORE, min(MAX_SCORE, float(match.group())))


def tool_match(
    run_tool_calls: list[dict], expected_tool: str, expected_args: dict
) -> bool:
    """Check whether one of the run's tool calls matches the expected tool and args.

    A call matches when its name equals `expected_tool` and every key in
    `expected_args` is present with the same (string-compared) value.
    """
    for call in run_tool_calls:
        if call.get("name") != expected_tool:
            continue
        args = call.get("args", {})
        if all(str(args.get(k)) == str(v) for k, v in expected_args.items()):
            return True
    return False


def selected_expected_tool(
    run_tool_calls: list[dict[str, Any]], expected_tool: str
) -> bool:
    """Return whether at least one call selected ``expected_tool``."""
    return any(call.get("name") == expected_tool for call in run_tool_calls)


def avoids_forbidden_tools(
    run_tool_calls: list[dict[str, Any]], forbidden_tools: Iterable[str]
) -> bool:
    """Return whether no tool call used one of the forbidden names."""
    forbidden = set(forbidden_tools)
    return all(call.get("name") not in forbidden for call in run_tool_calls)


def did_not_mutate(tool_results: list[dict[str, Any]]) -> bool:
    """Detect successful booking mutations from the domain tool responses."""
    successful_mutations = ("Reserva creada", "Reserva cancelada.")
    return all(
        not str(result.get("content", "")).startswith(successful_mutations)
        for result in tool_results
    )


def parse_quality_scores(text: str) -> dict[str, float]:
    """Parse and clamp the four JSON scores requested from the judge model."""
    match = _JSON_OBJECT_PATTERN.search(text)
    if match is None:
        return {key: MIN_SCORE for key in QUALITY_KEYS}
    try:
        payload = json.loads(match.group())
    except (json.JSONDecodeError, TypeError):
        return {key: MIN_SCORE for key in QUALITY_KEYS}
    return {key: _clamp_score(payload.get(key, MIN_SCORE)) for key in QUALITY_KEYS}


def _clamp_score(value: object) -> float:
    if not isinstance(value, (str, int, float)):
        return MIN_SCORE
    try:
        number = float(value)
    except ValueError:
        return MIN_SCORE
    return max(MIN_SCORE, min(MAX_SCORE, number))
