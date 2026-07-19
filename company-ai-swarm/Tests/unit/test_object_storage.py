"""Phase 2: object storage substrate."""

from __future__ import annotations

import pytest

from shared.object_storage import FilesystemObjectStorage


@pytest.fixture()
def storage(tmp_path) -> FilesystemObjectStorage:
    return FilesystemObjectStorage(tmp_path / "objects")


def test_put_and_get_roundtrip(storage: FilesystemObjectStorage) -> None:
    storage.put("reports/report-001.txt", b"market intelligence report content")

    data = storage.get("reports/report-001.txt")

    assert data == b"market intelligence report content"


def test_exists(storage: FilesystemObjectStorage) -> None:
    assert storage.exists("reports/report-001.txt") is False
    storage.put("reports/report-001.txt", b"x")
    assert storage.exists("reports/report-001.txt") is True


def test_get_missing_key_raises(storage: FilesystemObjectStorage) -> None:
    with pytest.raises(FileNotFoundError):
        storage.get("does/not/exist.txt")


def test_delete(storage: FilesystemObjectStorage) -> None:
    storage.put("reports/report-001.txt", b"x")
    storage.delete("reports/report-001.txt")
    assert storage.exists("reports/report-001.txt") is False


def test_path_traversal_is_rejected(storage: FilesystemObjectStorage) -> None:
    with pytest.raises(ValueError, match="Invalid object key"):
        storage.put("../../etc/passwd", b"malicious")
