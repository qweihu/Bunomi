"""Auditable phrase-level reading overrides."""

from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class ReadingOverride:
    id: str
    phrase: str
    reading: str
    romaji: str
    reason: str


def load_reading_overrides() -> tuple[ReadingOverride, ...]:
    path = Path(__file__).with_name("data") / "reading_overrides.json"
    try:
        raw_items = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取读音覆盖规则: {path}") from exc

    overrides = tuple(ReadingOverride(**item) for item in raw_items)
    if any(not item.phrase or not item.reading for item in overrides):
        raise RuntimeError(f"读音覆盖规则包含空 phrase 或 reading: {path}")
    if len({item.id for item in overrides}) != len(overrides):
        raise RuntimeError(f"读音覆盖规则 id 重复: {path}")
    return tuple(sorted(overrides, key=lambda item: (-len(item.phrase), item.id)))
