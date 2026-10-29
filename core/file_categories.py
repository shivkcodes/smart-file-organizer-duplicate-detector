"""Extension-based file classification."""

from pathlib import Path

CATEGORY_EXTENSIONS: dict[str, frozenset[str]] = {
    "Documents": frozenset({".pdf", ".doc", ".docx", ".odt", ".rtf", ".txt", ".md", ".tex", ".ppt", ".pptx", ".xls", ".xlsx", ".csv", ".tsv"}),
    "Images": frozenset({".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tif", ".tiff", ".webp", ".heic", ".svg", ".ico"}),
    "Videos": frozenset({".mp4", ".mkv", ".mov", ".avi", ".wmv", ".webm", ".m4v", ".mpeg", ".mpg"}),
    "Audio": frozenset({".mp3", ".wav", ".aac", ".flac", ".ogg", ".m4a", ".wma", ".aiff"}),
    "Archives": frozenset({".zip", ".rar", ".7z", ".tar", ".gz", ".bz2", ".xz", ".cab"}),
    "Code": frozenset({".py", ".pyw", ".js", ".ts", ".jsx", ".tsx", ".java", ".c", ".h", ".cpp", ".cs", ".go", ".rs", ".php", ".html", ".css", ".json", ".xml", ".yaml", ".yml", ".sql", ".sh", ".ps1"}),
}


def classify_extension(extension: str | None) -> str:
    """Return the category for a suffix (including its leading dot)."""
    normalized = (extension or "").strip().lower()
    if normalized and not normalized.startswith("."):
        normalized = f".{normalized}"
    for category, extensions in CATEGORY_EXTENSIONS.items():
        if normalized in extensions:
            return category
    return "Others"


def classify_file(path: str | Path) -> str:
    """Classify a path by its extension without reading file contents."""
    return classify_extension(Path(path).suffix)
