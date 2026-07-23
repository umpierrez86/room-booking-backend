"""Tests for the deterministic evaluators used by agent evals."""
import pytest

from evals.evaluators import parse_judge_score, tool_match


def test_matches_tool_and_args() -> None:
    calls = [{"name": "create_booking", "args": {"room": "C", "start": "10:00", "end": "11:30", "attendees": 6}}]
    assert tool_match(calls, "create_booking", {"room": "C", "attendees": 6})


def test_wrong_tool_fails() -> None:
    calls = [{"name": "list_available_rooms", "args": {}}]
    assert not tool_match(calls, "create_booking", {"room": "C"})


def test_missing_arg_fails() -> None:
    calls = [{"name": "create_booking", "args": {"room": "B"}}]
    assert not tool_match(calls, "create_booking", {"room": "C"})


@pytest.mark.parametrize(
    ("reply", "expected"),
    [
        ("0.8", 0.8),
        ("Score: 0.75 overall", 0.75),
        ("1", 1.0),
        ("1.5", 1.0),  # clamped to the max
        ("-0.3", 0.0),  # clamped to the min
        ("sin puntaje", 0.0),  # no number -> fallback
    ],
)
def test_parse_judge_score(reply: str, expected: float) -> None:
    assert parse_judge_score(reply) == expected
