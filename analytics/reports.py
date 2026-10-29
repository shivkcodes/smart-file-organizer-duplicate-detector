"""Pure calculations for dashboard and chart summaries."""

from __future__ import annotations

from collections import defaultdict
from typing import Iterable

from core.duplicate_detector import DuplicateGroup
from core.scanner import FileInfo


def build_report(files: Iterable[FileInfo], duplicate_groups: Iterable[DuplicateGroup]) -> dict[str, object]:
    file_list = list(files)
    groups = list(duplicate_groups)
    counts: dict[str, int] = defaultdict(int)
    sizes: dict[str, int] = defaultdict(int)
    for item in file_list:
        counts[item.category] += 1
        sizes[item.category] += item.size
    return {
        "total_file_count": len(file_list),
        "total_size": sum(item.size for item in file_list),
        "category_counts": dict(counts),
        "category_sizes": dict(sizes),
        "duplicate_group_count": len(groups),
        "duplicate_file_count": sum(group.file_count for group in groups),
        "potential_reclaimable_bytes": sum(group.reclaimable_bytes for group in groups),
    }


def format_bytes(value: int) -> str:
    """Format bytes with a readable binary unit."""
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    amount = float(value)
    for unit in units:
        if abs(amount) < 1024 or unit == units[-1]:
            return f"{amount:.0f} {unit}" if unit == "B" else f"{amount:.2f} {unit}"
        amount /= 1024
    return f"{amount:.2f} TiB"
