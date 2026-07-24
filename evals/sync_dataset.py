"""Synchronize the repository-owned evaluation cases to LangSmith."""

import uuid
from collections.abc import Iterable
from typing import Any, Protocol

from evals.dataset import EvalCase

DATASET_NAME = "room-booking-agent"
DATASET_DESCRIPTION = (
    "Natural-language room-booking requests and expected agent behavior."
)
MANAGED_SOURCE = "repository"
_EXAMPLE_NAMESPACE = uuid.UUID("e8ca60d7-9970-4e73-bdb1-c3b44e51bb99")


class DatasetRef(Protocol):
    id: uuid.UUID


class ExampleRef(Protocol):
    id: uuid.UUID
    metadata: dict[str, Any] | None


class LangSmithDatasetClient(Protocol):
    """Subset of ``langsmith.Client`` used by the synchronizer."""

    def has_dataset(self, *, dataset_name: str) -> bool: ...

    def read_dataset(self, *, dataset_name: str) -> DatasetRef: ...

    def create_dataset(self, dataset_name: str, *, description: str) -> DatasetRef: ...

    def list_examples(self, *, dataset_id: uuid.UUID) -> Iterable[ExampleRef]: ...

    def create_examples(
        self, *, dataset_id: uuid.UUID, examples: list[dict[str, Any]]
    ) -> object: ...

    def update_example(
        self,
        example_id: uuid.UUID,
        *,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        metadata: dict[str, Any],
        split: str,
        dataset_id: uuid.UUID,
    ) -> object: ...

    def delete_example(self, example_id: uuid.UUID) -> None: ...


def stable_example_id(case_id: str) -> uuid.UUID:
    """Return the same LangSmith example ID for a case across every sync."""
    return uuid.uuid5(_EXAMPLE_NAMESPACE, case_id)


def sync_dataset(
    client: LangSmithDatasetClient, cases: Iterable[EvalCase]
) -> DatasetRef:
    """Upsert repository cases and delete only stale repository-managed examples."""
    case_list = list(cases)
    _validate_unique_ids(case_list)
    dataset = (
        client.read_dataset(dataset_name=DATASET_NAME)
        if client.has_dataset(dataset_name=DATASET_NAME)
        else client.create_dataset(DATASET_NAME, description=DATASET_DESCRIPTION)
    )

    existing = list(client.list_examples(dataset_id=dataset.id))
    existing_by_id = {example.id: example for example in existing}
    desired = {
        stable_example_id(case["id"]): _to_langsmith_example(case) for case in case_list
    }
    new_examples: list[dict[str, Any]] = []
    for example_id, payload in desired.items():
        if example_id not in existing_by_id:
            new_examples.append(payload)
            continue
        client.update_example(
            example_id,
            inputs=payload["inputs"],
            outputs=payload["outputs"],
            metadata=payload["metadata"],
            split=payload["split"],
            dataset_id=dataset.id,
        )
    if new_examples:
        client.create_examples(dataset_id=dataset.id, examples=new_examples)

    for example in existing:
        metadata = example.metadata or {}
        if metadata.get("source") == MANAGED_SOURCE and example.id not in desired:
            client.delete_example(example.id)
    return dataset


def _to_langsmith_example(case: EvalCase) -> dict[str, Any]:
    return {
        "id": stable_example_id(case["id"]),
        "inputs": {"input": case["input"]},
        "outputs": {
            "expected_tool": case["expected_tool"],
            "expected_args": case["expected_args"],
            "forbidden_tools": case["forbidden_tools"],
            "must_not_mutate": case["must_not_mutate"],
        },
        "metadata": {
            "source": MANAGED_SOURCE,
            "case_id": case["id"],
            "category": case["category"],
            "critical": case["critical"],
        },
        "split": "test",
    }


def _validate_unique_ids(cases: list[EvalCase]) -> None:
    ids = [case["id"] for case in cases]
    duplicates = sorted({case_id for case_id in ids if ids.count(case_id) > 1})
    if duplicates:
        raise ValueError(f"Duplicate evaluation case ids: {', '.join(duplicates)}")
