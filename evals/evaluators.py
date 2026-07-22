"""Pure, testable evaluators for agent eval runs (no LLM calls)."""


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
