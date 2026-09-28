"""交互式阅读循环：按任意键翻下一行，q / Ctrl+C 退出。"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from fish_reader import progress
from fish_reader.console import safe_print

QUIT_KEYS = {"q", "Q", "\x03"}  # \x03 = Ctrl+C


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

    index = start
    try:
        while index < len(lines):
            key = _read_key()
            if key in QUIT_KEYS:
                break
            safe_print(lines[index])
            index += 1
    except KeyboardInterrupt:
        pass
    finally:
        progress.set_line_index(book_name, index)
        _clear_screen()
