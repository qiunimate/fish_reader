"""书架：扫描 books/ 目录下的 txt 文件。"""

from __future__ import annotations

from pathlib import Path

BOOKS_DIR = Path(__file__).resolve().parent.parent.parent / "books"


def list_books() -> list[Path]:
    if not BOOKS_DIR.exists():
        return []
    return sorted(BOOKS_DIR.glob("*.txt"))


# 国内流传的小说 txt 十有八九不是 UTF-8，而是 GBK/GB18030；顺序尝试，
# 优先严格解码，任何一种都失败才用 errors="ignore" 兜底，避免整本乱码。
_CANDIDATE_ENCODINGS = ("utf-8-sig", "gb18030")


def _decode_book(raw: bytes) -> str:
    for encoding in _CANDIDATE_ENCODINGS:
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="ignore")


def load_lines(book_path: Path) -> list[str]:
    """按行读取小说正文，过滤掉空行（避免翻页翻到空白浪费一次按键）。"""
    text = _decode_book(book_path.read_bytes())
    return [line.strip() for line in text.splitlines() if line.strip()]


def chunk_lines(lines: list[str], chars_per_chunk: int) -> list[str]:
    """把每行按固定字符数切块，控制每次翻页显示多少字。"""
    if chars_per_chunk <= 0:
        return lines
    chunks: list[str] = []
    for line in lines:
        for start in range(0, len(line), chars_per_chunk):
            chunks.append(line[start : start + chars_per_chunk])
    return chunks
