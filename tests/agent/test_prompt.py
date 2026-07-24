"""Tests for the context included in the agent's system prompt."""
import datetime as dt

from app.adapters.agent import prompt


def test_system_prompt_includes_current_local_date(monkeypatch) -> None:
    class FixedDateTime(dt.datetime):
        @classmethod
        def now(cls, tz: dt.tzinfo | None = None) -> dt.datetime:
            return cls(2026, 7, 22, 12, tzinfo=tz)

    monkeypatch.setattr(prompt.dt, "datetime", FixedDateTime)

    assert "2026-07-22" in prompt.make_system_prompt("America/Montevideo")


def test_system_prompt_forbids_technical_tool_names() -> None:
    assert "Nunca nombres herramientas" in prompt.SYSTEM_PROMPT


def test_system_prompt_forbids_inventing_missing_booking_fields() -> None:
    assert "Nunca completes ni supongas" in prompt.SYSTEM_PROMPT
    assert "sala, fecha, hora de inicio, hora de fin, título" in prompt.SYSTEM_PROMPT
    assert "sin llamar ninguna herramienta" in prompt.SYSTEM_PROMPT
