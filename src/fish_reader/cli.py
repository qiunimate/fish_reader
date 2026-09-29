"""命令行入口：选书、进入阅读循环。"""

from __future__ import annotations

import argparse
import sys

from fish_reader import config, library, progress, reader
from fish_reader.console import capture_prompt_prefix, clear_screen, safe_input, safe_print


def _pick_book(books: list, requested_name: str | None):
    if requested_name is not None:
        matches = [b for b in books if b.name == requested_name or b.stem == requested_name]
        if not matches:
            safe_print(f"没找到书: {requested_name}")
            sys.exit(1)
        return matches[0]

    last_book = progress.get_last_book()
    default_index = next(
        (i for i, b in enumerate(books) if b.name == last_book), 0
    )

    safe_print("书架：")
    for i, b in enumerate(books):
        marker = " (上次读到这本)" if b.name == last_book else ""
        safe_print(f"  [{i}] {b.stem}{marker}")

    raw = safe_input(f"选一本 (回车默认 [{default_index}]): ").strip()
    if raw == "":
        return books[default_index]
    if not raw.isdigit() or not (0 <= int(raw) < len(books)):
        safe_print("输入无效")
        sys.exit(1)
    return books[int(raw)]


def main() -> None:
    # 必须在打印任何东西之前抓，抓的是"刚敲完 fish-reader 回车前那一行"，
    # 晚了这一行就被后面的输出顶上去、读不到了。
    prompt_prefix = capture_prompt_prefix()

    parser = argparse.ArgumentParser(description="伪装摸鱼阅读器")
    parser.add_argument("book", nargs="?", help="书名（文件名或不带后缀的名字），不传则进入书架选择")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        metavar="N",
        help=f"每次翻页显示多少个字符，会保存为默认配置（默认 {config.DEFAULT_CHARS_PER_CHUNK}）",
    )
    args = parser.parse_args()

    if args.chunk_size is not None:
        if args.chunk_size <= 0:
            safe_print("--chunk-size 必须是正整数")
            sys.exit(1)
        config.set_chars_per_chunk(args.chunk_size)
    chars_per_chunk = config.get_chars_per_chunk()

    books = library.list_books()
    if not books:
        safe_print("books/ 目录里没有找到任何 .txt 文件，先放几本小说进去吧。")
        sys.exit(1)

    book_path = _pick_book(books, args.book)
    lines = library.chunk_lines(library.load_lines(book_path), chars_per_chunk)
    clear_screen()
    if prompt_prefix:
        safe_print(prompt_prefix, end="")
    reader.run(book_path, lines)


if __name__ == "__main__":
    main()
