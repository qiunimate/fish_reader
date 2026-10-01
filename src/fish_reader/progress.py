"""Reading progress persistence: stored in the user's home directory, not tracked alongside the library."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PROGRESS_DIR = Path.home() / ".fish_reader"
PROGRESS_FILE = PROGRESS_DIR / "progress.json"


def _load_all() -> dict[str, Any]:
    if not PROGRESS_FILE.exists():
        return {}
    try:
        return json.loads(PROGRESS_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # Treat a corrupt progress file as no progress; doesn't affect normal usage
        return {}


def _save_all(data: dict[str, Any]) -> None:
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_line_index(book_name: str) -> int:
    """Return where a book was last left off (index of the next line to show); 0 if never read."""
    data = _load_all()
    books: dict[str, int] = data.get("books", {})
    return books.get(book_name, 0)


def set_line_index(book_name: str, line_index: int) -> None:
    data = _load_all()
    books: dict[str, int] = data.setdefault("books", {})
    books[book_name] = line_index
    data["last_book"] = book_name
    _save_all(data)


def get_last_book() -> str | None:
    data = _load_all()
    return data.get("last_book")
