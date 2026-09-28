"""Windows 下绕开控制台代码页/PowerShell 编码问题的输出封装。

PowerShell 5.1 的 [Console]::OutputEncoding 是它自己缓存的一层（常见默认是
cp850），跟原始控制台代码页（chcp/SetConsoleOutputCP）是两回事，子进程改
代码页它不会跟着同步，所以普通 print() 在 PS5.1 里打印中文会乱码。
直接调 WriteConsoleW 往控制台句柄写 UTF-16 文本可以绕开这层转换。
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
    """stdout 被重定向到文件/管道时 GetConsoleMode 会失败，这时用普通 print 即可。"""
    if sys.platform != "win32":
        return False
    mode = ctypes.c_uint32()
    handle = _console_handle()
    return bool(ctypes.windll.kernel32.GetConsoleMode(handle, ctypes.byref(mode)))


_USE_WRITE_CONSOLE = _is_real_console()


def safe_print(text: str = "", end: str = "\n") -> None:
    """跨编码环境安全的输出，中文/PS5.1 场景不会乱码。"""
    if _USE_WRITE_CONSOLE:
        line = text + end
        written = ctypes.c_uint32(0)
        ctypes.windll.kernel32.WriteConsoleW(
            _console_handle(), line, len(line), ctypes.byref(written), None
        )
    else:
        print(text, end=end)


def safe_input(prompt: str = "") -> str:
    """跨编码环境安全的 input()：提示文字走 safe_print，避免 input() 自己用错编码打印。"""
    safe_print(prompt, end="")
    return input()


def clear_screen() -> None:
    os.system("cls" if sys.platform == "win32" else "clear")


def _display_width(text: str) -> int:
    """终端里中日韩字符占 2 列、其余占 1 列，算要清多少列不能按字符数算。"""
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


_anchor: _COORD | None = None
_last_rows = 1


def overwrite_line(text: str) -> None:
    """原地刷新同一"行"：定位到固定光标坐标覆盖写，而不是只用 \\r。

    小说一行文字常常超出终端宽度会自动换行，实际占用多行屏幕；只用 \\r
    回到本行行首没法清掉上面被折行占用的部分，换短行时会有残留。这里
    改成记住起始光标坐标，按上一次实际占用的行数整块清空后再重写。
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
    rows_needed = max(1, -(-width // buffer_width))  # 向上取整
    clear_rows = max(_last_rows, rows_needed)

    _fill_blank(_anchor, buffer_width * clear_rows)
    _set_cursor(_anchor)
    safe_print(text, end="")
    _last_rows = rows_needed

