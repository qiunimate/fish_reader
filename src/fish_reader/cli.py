"""CLI entry point: pick a book, enter the reading loop."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from fish_reader import config, library, progress, reader
from fish_reader.console import clear_previous_rows, count_rows, reclaim_command_line, safe_input, safe_print


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

    # Tally rows as we print so we can wipe exactly this menu later, even if
    # printing it scrolled the console buffer (see console.count_rows).
    printed_rows = 0

    header = "Library:"
    safe_print(header)
    printed_rows += count_rows(header)
    for i, b in enumerate(books):
        marker = " (last read)" if b.name == last_book else ""
        line = f"  [{i}] {b.stem}{marker}"
        safe_print(line)
        printed_rows += count_rows(line)

    prompt = f"Pick one (Enter for default [{default_index}]): "
    raw = safe_input(prompt).strip()
    printed_rows += count_rows(prompt + raw)

    if raw != "" and (not raw.isdigit() or not (0 <= int(raw) < len(books))):
        safe_print("Invalid input")
        sys.exit(1)

    clear_previous_rows(printed_rows + 1)  # +1 for the blank row Enter left the cursor on
    return books[default_index] if raw == "" else books[int(raw)]


def main() -> None:
    # Must happen before printing anything else: it erases "fish-reader ..."
    # on the line just above (see reclaim_command_line) and reserves that
    # spot for the novel's first line.
    reclaim_command_line()

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
    reader.run(book_path, lines)


if __name__ == "__main__":
    main()
