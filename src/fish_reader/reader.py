"""交互式阅读循环：按任意键翻下一行，q / Ctrl+C 退出。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fish_reader import progress
from fish_reader.console import overwrite_line, safe_print

QUIT_KEYS = {"q", "Q", "\x03"}  # \x03 = Ctrl+C
BACK_KEYS = {"\x08", "\x7f"}  # Backspace（Windows/大多数终端 \x08，部分终端 \x7f）


def _read_key() -> str:
    """读取一个按键，不回显、不需要回车。"""
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


def _clear_screen() -> None:
    os.system("cls" if sys.platform == "win32" else "clear")


def run(book_path: Path, lines: list[str]) -> None:
    book_name = book_path.name
    start = progress.get_line_index(book_name)

    if start >= len(lines):
        safe_print(f"《{book_path.stem}》已经读完啦。")
        return

    # pos 是当前显示行的下标，-1 表示还没显示过任何一行
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
        _clear_screen()
