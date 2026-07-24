"""Quality-gate aggregation tests without LangSmith or model calls."""

from types import SimpleNamespace
from typing import Any

import pytest

from evals.run_evals import enforce_quality_gates


def _row(
    metrics: dict[str, float | None],
    *,
    critical: bool = False,
    error: str | None = None,
) -> dict[str, Any]:
    return {
        "run": SimpleNamespace(error=error),
        "example": SimpleNamespace(metadata={"critical": critical}),
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
    with pytest.raises(RuntimeError, match="tool_selection"):
        enforce_quality_gates(
            [
                _row(
                    {
                        "tool_selection": 0.0,
                        "tool_arguments": 1.0,
                        "safety": 1.0,
                    }
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
