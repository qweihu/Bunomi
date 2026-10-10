#!/usr/bin/env python3
"""Install the Bunomi skill (root-level SKILL.md) into a Codex skills directory.

The command is intentionally explicit about its destination and refuses to
overwrite an existing installation unless ``--force`` is supplied.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]
SKILL_ITEMS = ("SKILL.md", "PROMPT.md", "agents")
MIN_PYTHON = (3, 10)


def default_destination() -> Path:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    return codex_home / "skills" / "bunomi"


def install(destination: Path, *, force: bool) -> Path:
    if not (ROOT / "SKILL.md").is_file():
        raise RuntimeError(f"项目 Skill 不完整: {ROOT}")
    destination = destination.expanduser().resolve()
    if destination.exists() and not force:
        raise RuntimeError(f"目标已存在，为避免覆盖请加 --force: {destination}")
    destination.mkdir(parents=True, exist_ok=True)
    for item in SKILL_ITEMS:
        source = ROOT / item
        target = destination / item
        if source.is_dir():
            if target.exists():
                shutil.rmtree(target)
            shutil.copytree(source, target)
        else:
            shutil.copy2(source, target)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="安装 Bunomi Codex Skill")
    parser.add_argument("--destination", type=Path, help="安装目标目录（默认 CODEX_HOME/skills/bunomi）")
    parser.add_argument("--force", action="store_true", help="允许更新已有安装")
    args = parser.parse_args(argv)
    try:
        if sys.version_info < MIN_PYTHON:
            raise RuntimeError("Bunomi 需要 Python 3.10 或更高版本")
        target = install(args.destination or default_destination(), force=args.force)
    except (OSError, RuntimeError) as exc:
        print(f"install_bunomi_skill: {exc}", file=sys.stderr)
        return 2
    print(f"Bunomi Skill 已安装：{target}")
    print("新会话触发矩阵与最近一次验证记录见 docs/codex-skill-trigger-test.md。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
