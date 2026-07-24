"""Quality-gate aggregation tests without LangSmith or model calls."""

from types import SimpleNamespace
from typing import Any

import pytest

from evals.run_evals import _message_text, enforce_quality_gates


def _row(
    metrics: dict[str, float | None],
    *,
    critical: bool = False,
    error: str | None = None,
    case_id: str = "case-1",
    tool_calls: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    return {
        "run": SimpleNamespace(error=error, outputs={"tool_calls": tool_calls or []}),
        "example": SimpleNamespace(
            id="example-1",
            metadata={"critical": critical, "case_id": case_id},
        ),
        "evaluation_results": {
            "results": [
                SimpleNamespace(key=key, score=score) for key, score in metrics.items()
            ]
        },
    }


def test_passing_objective_metrics_return_summary() -> None:
    summary = enforce_quality_gates(
        [
            _row(
                {
                    "tool_selection": 1.0,
                    "tool_arguments": 1.0,
                    "safety": 1.0,
                    "quality_clarity": 0.8,
                },
                critical=True,
            )
        ]
    )
    assert summary["tool_selection"] == 1.0
    assert summary["quality_clarity"] == 0.8
    assert summary["critical"] == 1.0


def test_informational_judge_score_does_not_fail_gate() -> None:
    summary = enforce_quality_gates(
        [
            _row(
                {
                    "tool_selection": 1.0,
                    "tool_arguments": 1.0,
                    "safety": 1.0,
                    "quality_correctness": 0.0,
                },
                critical=True,
            )
        ]
    )
    assert summary["quality_correctness"] == 0.0


def test_objective_metric_below_threshold_fails() -> None:
    with pytest.raises(RuntimeError, match="case-1.*list_available_rooms"):
        enforce_quality_gates(
            [
                _row(
                    {
                        "tool_selection": 0.0,
                        "tool_arguments": 1.0,
                        "safety": 1.0,
                    },
                    tool_calls=[{"name": "list_available_rooms", "args": {}}],
                )
            ]
        )


def test_any_critical_objective_failure_fails() -> None:
    rows = [
        _row({"tool_selection": 1.0, "tool_arguments": 1.0, "safety": 1.0})
        for _ in range(10)
    ]
    rows.append(
        _row(
            {"tool_selection": 0.0, "tool_arguments": 1.0, "safety": 1.0},
            critical=True,
        )
    )
    with pytest.raises(RuntimeError, match="critical"):
        enforce_quality_gates(rows)


def test_target_execution_error_fails_gate() -> None:
    with pytest.raises(RuntimeError, match="runs failed"):
        enforce_quality_gates(
            [
                _row(
                    {
                        "tool_selection": 1.0,
                        "tool_arguments": 1.0,
                        "safety": 1.0,
                    },
                    error="provider unavailable",
                )
            ]
        )


def test_message_text_does_not_call_string_compatible_accessor() -> None:
    class CallableText(str):
        def __call__(self) -> str:
            raise AssertionError("deprecated callable accessor must not be used")

    message = SimpleNamespace(text=CallableText("respuesta"), content="fallback")
    assert _message_text(message) == "respuesta"
