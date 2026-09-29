"""CLI entry point: pick a book, enter the reading loop."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fish_reader import config, library, progress, reader
from fish_reader.console import capture_prompt_prefix, clear_screen, safe_input, safe_print


def _pick_book(books: list[Path], requested_name: str | None) -> Path:
    if requested_name is not None:
        matches = [b for b in books if b.name == requested_name or b.stem == requested_name]
        if not matches:
            safe_print(f"Book not found: {requested_name}")
            sys.exit(1)
        return matches[0]

    last_book = progress.get_last_book()
    default_index = next(
        (i for i, b in enumerate(books) if b.name == last_book), 0
    )

    safe_print("Library:")
    for i, b in enumerate(books):
        marker = " (last read)" if b.name == last_book else ""
        safe_print(f"  [{i}] {b.stem}{marker}")

    raw = safe_input(f"Pick one (Enter for default [{default_index}]): ").strip()
    if raw == "":
        return books[default_index]
    if not raw.isdigit() or not (0 <= int(raw) < len(books)):
        safe_print("Invalid input")
        sys.exit(1)
    return books[int(raw)]


def main() -> None:
    # Must capture this before printing anything: it's "the line right before
    # Enter was pressed on fish-reader". Any later and our own output pushes
    # it out of reach.
    prompt_prefix = capture_prompt_prefix()

    parser = argparse.ArgumentParser(description="Disguised fish-reading tool")
    parser.add_argument("book", nargs="?", help="Book name (filename or stem); omit to pick from the library")
    parser.add_argument(
        "--chunk-size",
        type=int,
        default=None,
        metavar="N",
        help=f"How many characters to show per keypress; saved as the default (default {config.DEFAULT_CHARS_PER_CHUNK})",
    )
    args = parser.parse_args()

    if args.chunk_size is not None:
        if args.chunk_size <= 0:
            safe_print("--chunk-size must be a positive integer")
            sys.exit(1)
        config.set_chars_per_chunk(args.chunk_size)
    chars_per_chunk = config.get_chars_per_chunk()

    books = library.list_books()
    if not books:
        safe_print("No .txt files found in books/ — drop some novels in there first.")
        sys.exit(1)

    book_path = _pick_book(books, args.book)
    lines = library.chunk_lines(library.load_lines(book_path), chars_per_chunk)
    clear_screen()
    if prompt_prefix:
        safe_print(prompt_prefix, end="")
    reader.run(book_path, lines)


if __name__ == "__main__":
    main()
