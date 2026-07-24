"""Tests for the deterministic evaluators used by agent evals."""

import pytest

from evals.evaluators import (
    avoids_forbidden_tools,
    did_not_mutate,
    parse_judge_score,
    parse_quality_scores,
    selected_expected_tool,
    tool_match,
)


def test_matches_tool_and_args() -> None:
    calls = [
        {
            "name": "create_booking",
            "args": {"room": "C", "start": "10:00", "end": "11:30", "attendees": 6},
        }
    ]
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


def test_selected_expected_tool_only_checks_the_name() -> None:
    calls = [{"name": "get_room_schedule", "args": {"room": "D"}}]
    assert selected_expected_tool(calls, "get_room_schedule")
    assert not selected_expected_tool(calls, "list_available_rooms")


def test_forbidden_tool_detection() -> None:
    calls = [{"name": "cancel_booking", "args": {"booking_id": "x"}}]
    assert not avoids_forbidden_tools(calls, ["cancel_booking"])
    assert avoids_forbidden_tools(calls, ["create_booking"])


def test_successful_mutations_are_detected_from_tool_results() -> None:
    assert not did_not_mutate([{"content": "Reserva creada: Sala A"}])
    assert not did_not_mutate([{"content": "Reserva cancelada."}])
    assert did_not_mutate([{"content": "La reserva no existe."}])


def test_quality_scores_parse_json_and_clamp_values() -> None:
    scores = parse_quality_scores(
        'Resultado: {"clarity": 0.8, "correctness": 1.2, '
        '"on_topic": -0.1, "user_friendly": "0.9"}'
    )
    assert scores == {
        "clarity": 0.8,
        "correctness": 1.0,
        "on_topic": 0.0,
        "user_friendly": 0.9,
    }


def test_invalid_quality_json_returns_zero_scores() -> None:
    assert set(parse_quality_scores("sin JSON").values()) == {0.0}
