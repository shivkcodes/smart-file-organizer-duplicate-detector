"""Crash-resistant local JSON scan history."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


class HistoryFormatError(ValueError):
    """Raised when existing history is malformed and must be preserved."""


class HistoryManager:
    """Read and safely append scan snapshots to a JSON history file."""

    def __init__(self, history_path: str | Path) -> None:
        self.history_path = Path(history_path)

    def load_with_warnings(self) -> tuple[list[dict[str, Any]], list[str]]:
        if not self.history_path.exists():
            return [], []
        try:
            with self.history_path.open("r", encoding="utf-8") as history_file:
                data = json.load(history_file)
            if not isinstance(data, list) or any(not isinstance(item, dict) for item in data):
                raise ValueError("history root must be a JSON list of records")
            return data, []
        except (OSError, json.JSONDecodeError, ValueError) as error:
            return [], [f"Could not load scan history at {self.history_path}: {error}"]

    def load(self) -> list[dict[str, Any]]:
        return self.load_with_warnings()[0]

    def save(self, record: dict[str, Any]) -> None:
        """Append one snapshot using a same-directory temporary and atomic replace."""
        records: list[dict[str, Any]] = []
        if self.history_path.exists():
            try:
                with self.history_path.open("r", encoding="utf-8") as history_file:
                    existing = json.load(history_file)
                if not isinstance(existing, list) or any(not isinstance(item, dict) for item in existing):
                    raise ValueError("history root must be a JSON list of records")
                records = existing
            except (OSError, json.JSONDecodeError, ValueError) as error:
                raise HistoryFormatError(f"Existing history was left untouched: {error}") from error
        records.append(record)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.history_path.parent,
                                             prefix=f".{self.history_path.name}.", suffix=".tmp", delete=False) as temp_file:
                temporary_path = Path(temp_file.name)
                json.dump(records, temp_file, ensure_ascii=False, indent=2)
                temp_file.write("\n")
                temp_file.flush()
                os.fsync(temp_file.fileno())
            os.replace(temporary_path, self.history_path)
            temporary_path = None
        finally:
            if temporary_path is not None:
                try:
                    temporary_path.unlink(missing_ok=True)
                except OSError:
                    pass
