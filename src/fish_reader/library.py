"""书架：扫描 books/ 目录下的 txt 文件。"""

from __future__ import annotations

from pathlib import Path

BOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "books"


def list_books() -> list[Path]:
    if not BOOKS_DIR.exists():
        return []
    return sorted(BOOKS_DIR.glob("*.txt"))


def load_lines(book_path: Path) -> list[str]:
    """按行读取小说正文，过滤掉空行（避免翻页翻到空白浪费一次按键）。"""
    text = book_path.read_text(encoding="utf-8", errors="ignore")
    return [line.strip() for line in text.splitlines() if line.strip()]
