"""Preview and safely execute file organization moves."""

from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from .file_categories import CATEGORY_EXTENSIONS
from .scanner import FileInfo

VALID_CATEGORIES = frozenset(CATEGORY_EXTENSIONS) | {"Others"}


@dataclass(frozen=True)
class OrganizationItem:
    source: str
    destination: str
    category: str
    status: str
    expected_size: int
    expected_mtime_ns: int


def _within(path: Path, root: Path) -> bool:
    try:
        path.resolve(strict=False).relative_to(root.resolve(strict=False))
        return True
    except (ValueError, OSError):
        return False


class FileOrganizer:
    """Generate a no-side-effect preview and copy-then-remove moves safely."""

    def _unique_destination(self, directory: Path, name: str, reserved: set[str]) -> Path:
        candidate = directory / name
        number = 1
        while candidate.exists() or os.path.normcase(str(candidate)) in reserved:
            source_name = Path(name)
            candidate = directory / f"{source_name.stem} ({number}){source_name.suffix}"
            number += 1
        return candidate

    def create_preview(self, root: str | Path, files: Iterable[FileInfo]) -> list[OrganizationItem]:
        root_path = Path(root).expanduser().resolve()
        organized_root = root_path / "Organized"
        reserved: set[str] = set()
        preview: list[OrganizationItem] = []
        for file_info in files:
            source = Path(file_info.path)
            category_dir = organized_root / file_info.category
            destination = category_dir / source.name
            status = "Ready"
            try:
                if file_info.category not in VALID_CATEGORIES:
                    status = "Skipped: unknown file category"
                elif not _within(source, root_path):
                    status = "Skipped: source is outside the selected folder"
                elif source.is_symlink() or not source.is_file():
                    status = "Skipped: source is missing or is not a regular file"
                elif _within(source, organized_root) or source.resolve(strict=False) == organized_root.resolve(strict=False):
                    status = "Skipped: source is already organized"
                else:
                    destination = self._unique_destination(category_dir, source.name, reserved)
                    if not _within(destination, root_path):
                        status = "Skipped: destination is outside the selected folder"
                    reserved.add(os.path.normcase(str(destination)))
            except OSError as error:
                status = f"Skipped: could not validate paths ({error})"
            preview.append(OrganizationItem(
                source=str(source), destination=str(destination), category=file_info.category,
                status=status, expected_size=file_info.size, expected_mtime_ns=file_info.modified_ns,
            ))
        return preview

    def _safe_move(self, source: Path, destination: Path) -> None:
        """Copy through an exclusive destination, then remove source.

        This also works across filesystems. If copying fails, the partial target is
        removed and the source is retained. The destination is never overwritten.
        """
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
        descriptor = os.open(destination, flags, 0o666)
        copied = False
        source_identity: tuple[int, int, int, int] | None = None
        try:
            with source.open("rb") as source_handle, os.fdopen(descriptor, "wb") as destination_handle:
                descriptor = -1
                before = os.fstat(source_handle.fileno())
                source_identity = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
                shutil.copyfileobj(source_handle, destination_handle, length=1024 * 1024)
                after = os.fstat(source_handle.fileno())
                if (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns) != source_identity:
                    raise OSError("source changed while it was being copied")
                destination_handle.flush()
                os.fsync(destination_handle.fileno())
            shutil.copystat(source, destination)
            copied = True
        finally:
            if descriptor >= 0:
                os.close(descriptor)
            if not copied:
                try:
                    destination.unlink(missing_ok=True)
                except OSError:
                    pass
        try:
            current = source.stat()
            current_identity = (current.st_dev, current.st_ino, current.st_size, current.st_mtime_ns)
            if current_identity != source_identity:
                destination.unlink(missing_ok=True)
                raise OSError("source changed after it was copied; the source was retained")
        except OSError:
            if destination.exists() and source.exists():
                try:
                    destination.unlink()
                except OSError:
                    pass
            raise
        try:
            source.unlink()
        except OSError as error:
            raise OSError(f"destination was copied but the source could not be removed: {error}") from error

    def execute(self, root: str | Path, preview: Iterable[OrganizationItem]) -> list[OrganizationItem]:
        root_path = Path(root).expanduser().resolve()
        organized_root = root_path / "Organized"
        results: list[OrganizationItem] = []
        reserved: set[str] = set()
        for item in preview:
            source = Path(item.source)
            destination = Path(item.destination)
            status = item.status
            if status != "Ready":
                results.append(item)
                continue
            try:
                if not _within(source, root_path) or source.is_symlink() or not source.is_file():
                    raise ValueError("source is missing, linked, or outside the selected folder")
                if _within(source, organized_root):
                    raise ValueError("source is already inside Organized")
                if item.category not in VALID_CATEGORIES:
                    raise ValueError("unknown category in preview")
                stat = source.stat()
                if stat.st_size != item.expected_size or stat.st_mtime_ns != item.expected_mtime_ns:
                    raise ValueError("source changed after the preview was prepared")

                if organized_root.is_symlink() or getattr(organized_root, "is_junction", lambda: False)():
                    raise ValueError("Organized destination is a symbolic link or junction")
                category_dir = organized_root / item.category
                if category_dir.is_symlink() or getattr(category_dir, "is_junction", lambda: False)():
                    raise ValueError("category destination is a symbolic link or junction")
                category_dir.mkdir(parents=True, exist_ok=True)
                if (category_dir.is_symlink() or getattr(category_dir, "is_junction", lambda: False)()
                        or not _within(category_dir, organized_root)):
                    raise ValueError("category destination resolves outside Organized")
                if not _within(destination, organized_root):
                    raise ValueError("destination is outside Organized")

                chosen = destination
                if chosen.exists() or os.path.normcase(str(chosen)) in reserved:
                    chosen = self._unique_destination(category_dir, source.name, reserved)
                reserved.add(os.path.normcase(str(chosen)))
                self._safe_move(source, chosen)
                destination = chosen
                status = "Moved"
            except FileExistsError:
                status = "Skipped: destination appeared during move"
            except (OSError, ValueError) as error:
                status = f"Failed: {error}"
            results.append(OrganizationItem(
                source=item.source, destination=str(destination), category=item.category, status=status,
                expected_size=item.expected_size, expected_mtime_ns=item.expected_mtime_ns,
            ))
        return results
