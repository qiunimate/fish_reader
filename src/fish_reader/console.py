"""Output helpers that work around Windows console codepage / PowerShell encoding issues.

PowerShell 5.1's [Console]::OutputEncoding is its own cached layer (commonly
defaulting to cp850), separate from the raw console codepage (chcp /
SetConsoleOutputCP); a child process changing the codepage doesn't get
picked up by it, so plain print() garbles Chinese text in PS5.1. Calling
WriteConsoleW directly on the console handle writes UTF-16 text and bypasses
that translation layer entirely.
"""

from __future__ import annotations

import ctypes
import os
import sys
import unicodedata

_STD_OUTPUT_HANDLE = -11


def _console_handle() -> int:
    return ctypes.windll.kernel32.GetStdHandle(_STD_OUTPUT_HANDLE)


def _is_real_console() -> bool:
    """GetConsoleMode fails when stdout is redirected to a file/pipe; plain print() is fine then."""
    if sys.platform != "win32":
        return False
    mode = ctypes.c_uint32()
    handle = _console_handle()
    return bool(ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)))


_USE_WRITE_CONSOLE = _is_real_console()


def safe_print(text: str = "", end: str = "\n") -> None:
    """Encoding-safe output that won't garble Chinese text under PS5.1."""
    if _USE_WRITE_CONSOLE:
        line = text + end
        written = ctypes.c_uint32(0)
        ctypes.windll.kernel32.WriteConsoleW(
            _console_handle(), line, len(line), ctypes.byref(written), None
        )
    else:
        print(text, end=end)


def safe_input(prompt: str = "") -> str:
    """Encoding-safe input(): the prompt text goes through safe_print so input() doesn't print it with the wrong encoding."""
    safe_print(prompt, end="")
    return input()


def clear_screen() -> None:
    os.system("cls" if sys.platform == "win32" else "clear")


def _display_width(text: str) -> int:
    """CJK characters take up 2 terminal columns, everything else 1; must count columns, not characters, to know how much to clear."""
    return sum(2 if unicodedata.east_asian_width(ch) in ("W", "F") else 1 for ch in text)


class _COORD(ctypes.Structure):
    _fields_ = [("X", ctypes.c_short), ("Y", ctypes.c_short)]


class _SMALL_RECT(ctypes.Structure):
    _fields_ = [
        ("Left", ctypes.c_short),
        ("Top", ctypes.c_short),
        ("Right", ctypes.c_short),
        ("Bottom", ctypes.c_short),
    ]


class _CONSOLE_SCREEN_BUFFER_INFO(ctypes.Structure):
    _fields_ = [
        ("dwSize", _COORD),
        ("dwCursorPosition", _COORD),
        ("wAttributes", ctypes.c_ushort),
        ("srWindow", _SMALL_RECT),
        ("dwMaximumWindowSize", _COORD),
    ]


def _screen_info() -> _CONSOLE_SCREEN_BUFFER_INFO:
    info = _CONSOLE_SCREEN_BUFFER_INFO()
    ctypes.windll.kernel32.GetConsoleScreenBufferInfo(_console_handle(), ctypes.byref(info))
    return info


def _set_cursor(pos: _COORD) -> None:
    ctypes.windll.kernel32.SetConsoleCursorPosition(_console_handle(), pos)


def _fill_blank(start: _COORD, count: int) -> None:
    written = ctypes.c_uint32(0)
    ctypes.windll.kernel32.FillConsoleOutputCharacterW(
        _console_handle(), ctypes.c_wchar(" "), count, start, ctypes.byref(written)
    )


def _read_row_text(row: int, width: int) -> str:
    buf = ctypes.create_unicode_buffer(width + 1)
    read = ctypes.c_uint32(0)
    ok = ctypes.windll.kernel32.ReadConsoleOutputCharacterW(
        _console_handle(), buf, width, _COORD(0, row), ctypes.byref(read)
    )
    if not ok:
        return ""
    return buf.value[: read.value]


_PROMPT_DELIMITERS = ("> ", "$ ", "# ", "% ")


def capture_prompt_prefix() -> str | None:
    """Call this before printing anything else: reads the row above the
    cursor (the "prompt + command" line from just before Enter was pressed)
    and strips off the command, keeping only the prompt itself. The prompt
    varies per user (conda env name, path, oh-my-posh theme, ...), so it has
    to be read at runtime rather than hard-coded; returns None if no common
    prompt delimiter is found, and callers must have a fallback.
    """
    if not _USE_WRITE_CONSOLE:
        return None

    info = _screen_info()
    row = info.dwCursorPosition.Y - 1
    if row < 0:
        return None

    buffer_width = max(info.dwSize.X, 1)
    row_text = _read_row_text(row, buffer_width).rstrip()
    for delim in _PROMPT_DELIMITERS:
        idx = row_text.rfind(delim)
        if idx != -1:
            return row_text[: idx + len(delim)]
    return None


_anchor: _COORD | None = None
_last_rows = 1


def _rows_needed(width: int, start_col: int, buffer_width: int) -> int:
    first_row_capacity = max(buffer_width - start_col, 0)
    if width <= first_row_capacity:
        return 1
    remaining = width - first_row_capacity
    return 1 + -(-remaining // buffer_width)  # ceil division


def overwrite_line(text: str) -> None:
    """Redraw the same "line" in place by seeking to a fixed cursor position, instead of just using \\r.

    A novel line often exceeds the terminal width and wraps, actually
    occupying several screen rows; \\r alone only returns to the start of
    the current row and can't clear the rows a wrapped line spilled into,
    leaving leftovers when a shorter line follows. This remembers the
    starting cursor position and blanks out however many rows the previous
    write actually used before redrawing. The anchor column isn't always 0
    (e.g. writing right after a shell prompt), so the row count and the
    clear range both need to account for that starting-column offset.
    """
    global _anchor, _last_rows

    if not _USE_WRITE_CONSOLE:
        safe_print(text)
        return

    info = _screen_info()
    buffer_width = max(info.dwSize.X, 1)

    if _anchor is None:
        _anchor = _COORD(info.dwCursorPosition.X, info.dwCursorPosition.Y)
    else:
        _set_cursor(_anchor)

    width = _display_width(text)
    rows_needed = _rows_needed(width, _anchor.X, buffer_width)
    clear_rows = max(_last_rows, rows_needed)

    _fill_blank(_anchor, buffer_width * clear_rows - _anchor.X)
    _set_cursor(_anchor)
    safe_print(text, end="")
    _last_rows = rows_needed

