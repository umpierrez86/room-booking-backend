"""Repository-to-LangSmith dataset synchronization tests."""

import uuid
from dataclasses import dataclass, field
from typing import Any

import pytest

from evals.dataset import CASES, EvalCase
from evals.sync_dataset import MANAGED_SOURCE, stable_example_id, sync_dataset


@dataclass
class FakeDataset:
    id: uuid.UUID = field(default_factory=uuid.uuid4)


@dataclass
class FakeExample:
    id: uuid.UUID
    metadata: dict[str, Any] | None


class FakeClient:
    def __init__(
        self, *, exists: bool = True, examples: list[FakeExample] | None = None
    ):
        self.exists = exists
        self.dataset = FakeDataset()
        self.examples = examples or []
        self.uploaded: list[dict[str, Any]] = []
        self.updated: list[tuple[uuid.UUID, dict[str, Any]]] = []
        self.deleted: list[uuid.UUID] = []

    def has_dataset(self, *, dataset_name: str) -> bool:
        return self.exists

    def read_dataset(self, *, dataset_name: str) -> FakeDataset:
        return self.dataset

    def create_dataset(self, dataset_name: str, *, description: str) -> FakeDataset:
        self.exists = True
        return self.dataset

    def list_examples(self, *, dataset_id: uuid.UUID) -> list[FakeExample]:
        return self.examples

    def create_examples(
        self, *, dataset_id: uuid.UUID, examples: list[dict[str, Any]]
    ) -> object:
        self.uploaded = examples
        return object()

    def update_example(
        self,
        example_id: uuid.UUID,
        *,
        inputs: dict[str, Any],
        outputs: dict[str, Any],
        metadata: dict[str, Any],
        split: str,
        dataset_id: uuid.UUID,
    ) -> object:
        self.updated.append(
            (
                example_id,
                {
                    "inputs": inputs,
                    "outputs": outputs,
                    "metadata": metadata,
                    "split": split,
                },
            )
        )
        return object()

    def delete_example(self, example_id: uuid.UUID) -> None:
        self.deleted.append(example_id)


def test_sync_upserts_every_repository_case_with_stable_ids() -> None:
    client = FakeClient()
    sync_dataset(client, CASES)

    assert len(client.uploaded) == len(CASES)
    assert {example["id"] for example in client.uploaded} == {
        stable_example_id(case["id"]) for case in CASES
    }
    assert all(
        example["metadata"]["source"] == MANAGED_SOURCE for example in client.uploaded
    )
    assert len(CASES) == 30
    assert len({case["id"] for case in CASES}) == len(CASES)


def test_sync_deletes_only_stale_repository_managed_examples() -> None:
    stale = FakeExample(uuid.uuid4(), {"source": MANAGED_SOURCE})
    manual = FakeExample(uuid.uuid4(), {"source": "manual"})
    current = FakeExample(stable_example_id(CASES[0]["id"]), {"source": MANAGED_SOURCE})
    client = FakeClient(examples=[stale, manual, current])

    sync_dataset(client, CASES)

    assert client.deleted == [stale.id]
    assert [example_id for example_id, _ in client.updated] == [current.id]
    assert len(client.uploaded) == len(CASES) - 1


def test_sync_creates_dataset_when_missing() -> None:
    client = FakeClient(exists=False)
    dataset = sync_dataset(client, CASES)
    assert dataset is client.dataset
    assert client.uploaded


def test_duplicate_case_ids_are_rejected() -> None:
    duplicate: EvalCase = {**CASES[0]}
    with pytest.raises(ValueError, match="Duplicate evaluation case ids"):
        sync_dataset(FakeClient(), [CASES[0], duplicate])
