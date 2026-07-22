"""Topic guard: rejects prompt-injection/off-topic input before the LLM runs.

A hub-hosted topic-restriction validator (`guardrails hub install ...`)
needs network access and API keys unavailable in this environment and in
tests, so the restriction is expressed as a small `Validator` registered
locally with Guardrails AI and run through a real `guardrails.Guard`. It
can be swapped for (or combined with) a hub validator via `Guard().use(...)`
once those credentials are available, without touching `graph.py`.
"""
from collections.abc import Callable

from guardrails import Guard, OnFailAction
from guardrails.errors import ValidationError
from guardrails.validator_base import FailResult, PassResult, Validator, register_validator

INJECTION_MARKERS = ("ignore previous", "ignorá tus instrucciones", "system prompt")
OFF_TOPIC_MESSAGE = "Solo puedo ayudarte con reservas de salas."
TOPIC_VALIDATOR_NAME = "room_booking/reject_prompt_injection"

GuardFn = Callable[[str], str | None]


@register_validator(name=TOPIC_VALIDATOR_NAME, data_type="string")
class RejectPromptInjection(Validator):
    """Fails validation when the input looks like a prompt-injection attempt."""

    def _validate(self, value: str, metadata: dict[str, object]) -> FailResult | PassResult:
        low = value.lower()
        if any(marker in low for marker in INJECTION_MARKERS):
            return FailResult(error_message=OFF_TOPIC_MESSAGE)
        return PassResult()


def make_guard() -> GuardFn:
    """Build a guard function: returns a rejection message, or None if valid."""
    validator = Guard().use(RejectPromptInjection(on_fail=OnFailAction.EXCEPTION))

    def guard(text: str) -> str | None:
        try:
            validator.validate(text)
        except ValidationError:
            return OFF_TOPIC_MESSAGE
        return None

    return guard
