"""SHA-256 based duplicate content detection."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .scanner import FileInfo


@dataclass(frozen=True)
class DuplicateGroup:
    """A set of files with matching size and SHA-256 content hash."""

    sha256: str
    size: int
    paths: tuple[str, ...]

    @property
    def file_count(self) -> int:
        return len(self.paths)

    @property
    def reclaimable_bytes(self) -> int:
        return self.size * max(0, self.file_count - 1)


@dataclass
class DuplicateResult:
    groups: list[DuplicateGroup]
    warnings: list[str]


class DuplicateDetector:
    """Use file size to narrow candidates, then compare SHA-256 hashes."""

    def __init__(self, chunk_size: int = 1024 * 1024) -> None:
        self.chunk_size = chunk_size

    def _hash_file(self, path: Path, expected_size: int, expected_mtime_ns: int) -> str:
        before = path.stat()
        if before.st_size != expected_size or before.st_mtime_ns != expected_mtime_ns:
            raise RuntimeError("file changed since scanning")
        digest = hashlib.sha256()
        with path.open("rb") as file_handle:
            while chunk := file_handle.read(self.chunk_size):
                digest.update(chunk)
        after = path.stat()
        if after.st_size != before.st_size or after.st_mtime_ns != before.st_mtime_ns:
            raise RuntimeError("file changed while hashing")
        return digest.hexdigest()

    def find_duplicates(self, files: Iterable[FileInfo]) -> DuplicateResult:
        by_size: dict[int, list[FileInfo]] = {}
        for file_info in files:
            by_size.setdefault(file_info.size, []).append(file_info)

        hashed: dict[str, dict[str, list[str]]] = {}
        warnings: list[str] = []
        for size, candidates in by_size.items():
            if len(candidates) < 2:
                continue
            for candidate in candidates:
                path = Path(candidate.path)
                try:
                    digest = self._hash_file(path, candidate.size, candidate.modified_ns)
                    hashed.setdefault(digest, {}).setdefault(str(size), []).append(str(path))
                except (OSError, RuntimeError) as error:
                    warnings.append(f"Could not hash {path}: {error}")

        # Hash grouping already includes the size, but keep the size explicit in the key.
        groups: list[DuplicateGroup] = []
        by_digest_size: dict[tuple[str, int], list[str]] = {}
        for digest, size_groups in hashed.items():
            for size_text, paths in size_groups.items():
                if len(paths) > 1:
                    by_digest_size[(digest, int(size_text))] = paths
        for (digest, size), paths in sorted(by_digest_size.items()):
            groups.append(DuplicateGroup(digest, size, tuple(sorted(paths, key=str.casefold))))
        return DuplicateResult(groups, warnings)
