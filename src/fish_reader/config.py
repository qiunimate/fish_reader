"""可调配置：目前只有"每次显示多少个字符"这一项。"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

CONFIG_DIR = Path.home() / ".fish_reader"
CONFIG_FILE = CONFIG_DIR / "config.json"

DEFAULT_CHARS_PER_CHUNK = 50


def _load() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        # 配置文件损坏就当没配置，用默认值，不影响正常使用
        return {}


def _save(data: dict[str, Any]) -> None:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def get_chars_per_chunk() -> int:
    return _load().get("chars_per_chunk", DEFAULT_CHARS_PER_CHUNK)


def set_chars_per_chunk(value: int) -> None:
    data = _load()
    data["chars_per_chunk"] = value
    _save(data)
