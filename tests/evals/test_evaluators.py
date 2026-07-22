"""Tests for the deterministic tool_match evaluator used by agent evals."""
from evals.evaluators import tool_match


def test_matches_tool_and_args() -> None:
    calls = [{"name": "create_booking", "args": {"room": "C", "start": "10:00", "end": "11:30", "attendees": 6}}]
    assert tool_match(calls, "create_booking", {"room": "C", "attendees": 6})


def test_wrong_tool_fails() -> None:
    calls = [{"name": "list_available_rooms", "args": {}}]
    assert not tool_match(calls, "create_booking", {"room": "C"})


def test_missing_arg_fails() -> None:
    calls = [{"name": "create_booking", "args": {"room": "B"}}]
    assert not tool_match(calls, "create_booking", {"room": "C"})
