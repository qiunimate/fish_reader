"""Library: scans the books/ directory for txt files."""

from __future__ import annotations

from pathlib import Path

BOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "books"


def list_books() -> list[Path]:
    if not BOOKS_DIR.exists():
        return []
    return sorted(BOOKS_DIR.glob("*.txt"))


# Novel txt files floating around are usually GBK/GB18030, not UTF-8; try in
# order, strict decode first, and only fall back to errors="ignore" if every
# candidate fails, to avoid mangling the whole book.
_CANDIDATE_ENCODINGS = ("utf-8-sig", "gb18030")


def _decode_book(raw: bytes) -> str:
    for encoding in _CANDIDATE_ENCODINGS:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def load_lines(book_path: Path) -> list[str]:
    """Read the novel's text line by line, dropping blank lines (so a keypress never lands on nothing)."""
    text = _decode_book(book_path.read_bytes())
    return [line.strip() for line in text.splitlines() if line.strip()]


def chunk_lines(lines: list[str], chars_per_chunk: int) -> list[str]:
    """Split each line into fixed-size chunks, controlling how much text shows per keypress."""
    if chars_per_chunk <= 0:
        return lines
    chunks: list[str] = []
    for line in lines:
        for start in range(0, len(line), chars_per_chunk):
            chunks.append(line[start : start + chars_per_chunk])
    return chunks
