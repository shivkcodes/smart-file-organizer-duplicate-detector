"""Recursive filesystem scanner that collects file metadata only."""

from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from .file_categories import classify_extension


@dataclass(frozen=True)
class FileInfo:
    """Metadata captured for one file during a scan."""

    name: str
    extension: str
    size: int
    path: str
    modified_at: str
    category: str
    modified_ns: int

    def to_dict(self) -> dict[str, str | int]:
        return asdict(self)


@dataclass
class ScanResult:
    """Files and non-fatal warnings collected from a root folder."""

    root: str
    files: list[FileInfo]
    warnings: list[str]


class FileScanner:
    """Find regular files recursively without following symbolic links."""

    def scan(self, root: str | Path) -> ScanResult:
        root_path = Path(root).expanduser()
        if not root_path.exists():
            raise FileNotFoundError(f"Folder does not exist: {root_path}")
        if not root_path.is_dir():
            raise NotADirectoryError(f"Selected path is not a folder: {root_path}")
        root_path = root_path.resolve()
        files: list[FileInfo] = []
        warnings: list[str] = []
        organized_path = root_path / "Organized"
        organized_key = os.path.normcase(str(organized_path.resolve(strict=False)))

        def on_walk_error(error: OSError) -> None:
            warnings.append(f"Could not access {error.filename or root_path}: {error.strerror or error}")

        for current, dirnames, filenames in os.walk(root_path, topdown=True, followlinks=False, onerror=on_walk_error):
            current_path = Path(current)
            kept_dirs: list[str] = []
            for dirname in dirnames:
                candidate = current_path / dirname
                try:
                    if candidate.is_symlink() or getattr(candidate, "is_junction", lambda: False)():
                        continue
                    if os.path.normcase(str(candidate.resolve(strict=False))) == organized_key:
                        continue
                except OSError as error:
                    warnings.append(f"Could not inspect directory {candidate}: {error}")
                    continue
                kept_dirs.append(dirname)
            dirnames[:] = kept_dirs

            for filename in filenames:
                path = current_path / filename
                try:
                    if path.is_symlink():
                        continue
                    stat = path.stat(follow_symlinks=False)
                    if not path.is_file():
                        continue
                    suffix = path.suffix.lower()
                    files.append(FileInfo(
                        name=path.name,
                        extension=suffix or "(none)",
                        size=stat.st_size,
                        path=str(path.absolute()),
                        modified_at=datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
                        category=classify_extension(suffix),
                        modified_ns=stat.st_mtime_ns,
                    ))
                except (OSError, PermissionError) as error:
                    warnings.append(f"Could not read file metadata for {path}: {error}")

        files.sort(key=lambda item: item.path.casefold())
        return ScanResult(root=str(root_path), files=files, warnings=warnings)
