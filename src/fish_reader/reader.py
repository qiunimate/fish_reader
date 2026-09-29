"""Interactive reading loop: any key advances a line, q / Ctrl+C quits."""

from __future__ import annotations

import sys
from pathlib import Path

from fish_reader import progress
from fish_reader.console import clear_screen, overwrite_line, safe_print

QUIT_KEYS = {"q", "Q", "\x03"}  # \x03 = Ctrl+C
BACK_KEYS = {"\x08", "\x7f"}  # Backspace (\x08 on Windows/most terminals, \x7f on some)


def _read_key() -> str:
    """Read a single keypress, no echo, no Enter required."""
    if sys.platform == "win32":
        import msvcrt

        ch = msvcrt.getch()
        try:
            return ch.decode("utf-8", errors="ignore")
        except UnicodeDecodeError:
            return ""
    else:
        import termios
        import tty

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setcbreak(fd)
            return sys.stdin.read(1)
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def run(book_path: Path, lines: list[str]) -> None:
    book_name = book_path.name
    start = progress.get_line_index(book_name)

    if start >= len(lines):
        safe_print(f'"{book_path.stem}" is already finished.')
        return

    # pos is the index of the currently displayed line; -1 means nothing shown yet
    pos = start - 1
    try:
        while True:
            key = _read_key()
            if key in QUIT_KEYS:
                break
            if key in BACK_KEYS:
                if pos <= 0:
                    continue
                pos -= 1
            else:
                pos = min(pos + 1, len(lines) - 1)
            overwrite_line(lines[pos])
    except KeyboardInterrupt:
        pass
    finally:
        progress.set_line_index(book_name, pos + 1)
        clear_screen()
