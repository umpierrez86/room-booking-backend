"""Pure, testable evaluators for agent eval runs (no LLM calls)."""
import re

MIN_SCORE = 0.0
MAX_SCORE = 1.0
_NUMBER_PATTERN = re.compile(r"[-+]?\d*\.?\d+")


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


def tool_match(run_tool_calls: list[dict], expected_tool: str, expected_args: dict) -> bool:
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
