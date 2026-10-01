"""Interactive reading loop: a/d move back/forward a line, s toggles hiding the text, q / Ctrl+C quits."""

from __future__ import annotations

import sys
from pathlib import Path

from fish_reader import progress
from fish_reader.console import clear_last_block, overwrite_line, safe_print

QUIT_KEYS = {"q", "Q", "\x03"}  # \x03 = Ctrl+C
BACK_KEYS = {"a", "A"}
FORWARD_KEYS = {"d", "D"}
TOGGLE_HIDE_KEYS = {"s", "S"}


def _read_key() -> str:
    """Read a single keypress, no echo, no Enter required."""
    if sys.platform == "win32":
        import msvcrt

        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):
            # Extended key (arrows, Home/End, PageUp/Down, Delete, F-keys):
            # msvcrt reports it as this lead byte followed by a second
            # getch() call for the actual scan code. Consume that second
            # byte now so it doesn't get misread as the next real keypress.
            msvcrt.getch()
            return ""
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


def run(book_path: Path, lines: list[str], start_override: int | None = None) -> None:
    book_name = book_path.name
    start = start_override if start_override is not None else progress.get_line_index(book_name)

    if start >= len(lines):
        safe_print(f'"{book_path.stem}" is already finished.')
        return

    # pos is the index of the currently displayed line; -1 means nothing shown yet
    pos = start - 1
    hidden = False
    try:
        while True:
            key = _read_key()
            if key == "":
                continue  # unrecognized/undecodable key, ignore and wait for the next one
            if key in QUIT_KEYS:
                break
            if key in TOGGLE_HIDE_KEYS:
                hidden = not hidden
                if pos >= 0:
                    overwrite_line("" if hidden else lines[pos])
                continue
            if key in BACK_KEYS:
                if pos <= 0:
                    continue
                pos -= 1
            elif key in FORWARD_KEYS:
                pos = min(pos + 1, len(lines) - 1)
            else:
                continue  # unbound key, ignore
            if not hidden:
                overwrite_line(lines[pos])
    except KeyboardInterrupt:
        pass
    finally:
        progress.set_line_index(book_name, pos + 1)
        clear_last_block()
