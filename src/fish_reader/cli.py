"""命令行入口：选书、进入阅读循环。"""

from __future__ import annotations

import argparse
import sys

from fish_reader import library, progress, reader


def _ensure_utf8_stdout() -> None:
    # Windows 终端默认代码页常是 cp1252/gbk，直接打印小说里的中文会抛 UnicodeEncodeError
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _pick_book(books: list, requested_name: str | None):
    if requested_name is not None:
        matches = [b for b in books if b.name == requested_name or b.stem == requested_name]
        if not matches:
            print(f"没找到书: {requested_name}")
            sys.exit(1)
        return matches[0]

    last_book = progress.get_last_book()
    default_index = next(
        (i for i, b in enumerate(books) if b.name == last_book), 0
    )

    print("书架：")
    for i, b in enumerate(books):
        marker = " (上次读到这本)" if b.name == last_book else ""
        print(f"  [{i}] {b.stem}{marker}")

    raw = input(f"选一本 (回车默认 [{default_index}]): ").strip()
    if raw == "":
        return books[default_index]
    if not raw.isdigit() or not (0 <= int(raw) < len(books)):
        print("输入无效")
        sys.exit(1)
    return books[int(raw)]


def main() -> None:
    _ensure_utf8_stdout()
    parser = argparse.ArgumentParser(description="伪装摸鱼阅读器")
    parser.add_argument("book", nargs="?", help="书名（文件名或不带后缀的名字），不传则进入书架选择")
    args = parser.parse_args()

    books = library.list_books()
    if not books:
        print(f"books/ 目录里没有找到任何 .txt 文件，先放几本小说进去吧。")
        sys.exit(1)

    book_path = _pick_book(books, args.book)
    lines = library.load_lines(book_path)
    reader.run(book_path, lines)


if __name__ == "__main__":
    main()
