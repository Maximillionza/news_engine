"""Object storage substrate for documents/artifacts (EIAS sec.8 "Object Storage").

Dev/test implementation: local filesystem, rooted under a configurable directory. Production
deployment swaps this for a real object store (S3, MinIO, etc.); the interface (`put`, `get`,
`exists`, `delete`) is deliberately small so that swap doesn't touch callers. Same
test-only-substitution pattern as shared/db.py - see
Documentation/operations/technology_decisions.md.
"""

from __future__ import annotations

import os
from pathlib import Path


class FilesystemObjectStorage:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _resolve(self, key: str) -> Path:
        # Reject path traversal - a key is a flat identifier, not a filesystem path.
        if ".." in Path(key).parts or Path(key).is_absolute():
            raise ValueError(f"Invalid object key: {key!r}")
        return self.root / key

    def put(self, key: str, data: bytes) -> None:
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)

    def get(self, key: str) -> bytes:
        path = self._resolve(key)
        if not path.exists():
            raise FileNotFoundError(f"No object with key {key!r}")
        return path.read_bytes()

    def exists(self, key: str) -> bool:
        return self._resolve(key).exists()

    def delete(self, key: str) -> None:
        path = self._resolve(key)
        if path.exists():
            os.remove(path)
