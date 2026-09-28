"""Windows 下绕开控制台代码页/PowerShell 编码问题的输出封装。

PowerShell 5.1 的 [Console]::OutputEncoding 是它自己缓存的一层（常见默认是
cp850），跟原始控制台代码页（chcp/SetConsoleOutputCP）是两回事，子进程改
代码页它不会跟着同步，所以普通 print() 在 PS5.1 里打印中文会乱码。
直接调 WriteConsoleW 往控制台句柄写 UTF-16 文本可以绕开这层转换。
"""

from __future__ import annotations

import ctypes
import sys

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


_last_overwrite_len = 0


def overwrite_line(text: str) -> None:
    """原地刷新同一行：\\r 回到行首覆盖写，不产生新行，避免屏幕一直往下滚。"""
    global _last_overwrite_len
    padded = text.ljust(_last_overwrite_len)
    _last_overwrite_len = len(text)
    safe_print("\r" + padded, end="")

