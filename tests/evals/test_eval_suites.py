"""Evaluation-suite selection tests without model or LangSmith calls."""

from types import SimpleNamespace

import pytest

from evals.dataset import CASES
from evals.run_evals import SMOKE_CASE_IDS, _eval_suite, _selected_examples


def _example(case_id: str) -> SimpleNamespace:
    return SimpleNamespace(metadata={"case_id": case_id})


def test_smoke_suite_selects_only_eight_representative_cases() -> None:
    examples = [_example(case_id) for case_id in SMOKE_CASE_IDS]
    examples.append(_example("full-only-case"))

    selected = _selected_examples(examples, "smoke")

    assert len(selected) == 8
    assert {item.metadata["case_id"] for item in selected} == SMOKE_CASE_IDS


def test_every_smoke_case_exists_in_versioned_dataset() -> None:
    case_ids = {case["id"] for case in CASES}

    assert len(SMOKE_CASE_IDS) == 8
    assert SMOKE_CASE_IDS <= case_ids


def test_full_suite_keeps_every_example() -> None:
    examples = [_example("one"), _example("two")]

    assert _selected_examples(examples, "full") == examples


def test_eval_suite_defaults_to_full(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("AGENT_EVAL_SUITE", raising=False)

    assert _eval_suite() == "full"


def test_eval_suite_rejects_unknown_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AGENT_EVAL_SUITE", "nightly")

    with pytest.raises(ValueError, match="smoke.*full"):
        _eval_suite()
