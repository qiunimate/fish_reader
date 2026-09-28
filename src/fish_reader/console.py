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
    """在程序打印任何东西之前调用：把光标上一行（也就是刚敲完回车前的
    "提示符 + 命令" 那一行）读出来，截掉命令只留提示符本身。提示符本身
    因人而异（conda 环境名、路径、oh-my-posh 主题……），所以只能现读，
    不能写死；找不到常见提示符分隔符就放弃，调用方要有兜底逻辑。
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
    return 1 + -(-remaining // buffer_width)  # 向上取整


def overwrite_line(text: str) -> None:
    """原地刷新同一"行"：定位到固定光标坐标覆盖写，而不是只用 \\r。

    小说一行文字常常超出终端宽度会自动换行，实际占用多行屏幕；只用 \\r
    回到本行行首没法清掉上面被折行占用的部分，换短行时会有残留。这里
    改成记住起始光标坐标，按上一次实际占用的行数整块清空后再重写。锚点
    列不一定是 0（比如紧跟在 shell 提示符后面写），所以行数/清除范围都
    要把起始列的偏移算进去。
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

