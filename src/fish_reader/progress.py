"""阅读进度持久化：存在用户目录下，不跟书架一起进版本库。"""

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
        # 进度文件损坏就当没有进度，不影响正常使用
        return {}


def _save_all(data: dict[str, Any]) -> None:
    PROGRESS_DIR.mkdir(parents=True, exist_ok=True)
    PROGRESS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_line_index(book_name: str) -> int:
    """返回某本书上次读到的行号（下一行要读的位置），没有记录则为 0。"""
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
