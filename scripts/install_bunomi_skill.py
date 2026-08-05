#!/usr/bin/env python3
"""Install project Skills (default: Bunomi) into a Codex skills directory.

The command is intentionally explicit about its destination and refuses to
overwrite an existing installation unless ``--force`` is supplied. It does
not run a Codex session itself; the separate trigger checklist records the
actual new-session verification.

Other skills in ``skills/`` (e.g. ``japanese-translation``) can be installed
with ``--name``.
"""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import shutil
import sys


ROOT = Path(__file__).resolve().parents[1]


def default_destination(name: str) -> Path:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    return codex_home / "skills" / name


def install(name: str, destination: Path, *, force: bool) -> Path:
    source = ROOT / "skills" / name
    if not name.replace("-", "").isalnum():
        raise RuntimeError(f"非法的技能名称: {name}")
    if not (source / "SKILL.md").is_file():
        raise RuntimeError(f"项目 Skill 不完整: {source}")
    destination = destination.expanduser().resolve()
    if destination.exists() and not force:
        raise RuntimeError(f"目标已存在，为避免覆盖请加 --force: {destination}")
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(source, destination, dirs_exist_ok=force)
    return destination


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="安装项目 Codex Skill")
    parser.add_argument("--name", default="bunomi", help="skills/ 下的技能名称（默认 bunomi）")
    parser.add_argument("--destination", type=Path, help="安装目标目录（默认 CODEX_HOME/skills/<name>）")
    parser.add_argument("--force", action="store_true", help="允许更新已有安装")
    args = parser.parse_args(argv)
    try:
        destination = args.destination or default_destination(args.name)
        target = install(args.name, destination, force=args.force)
    except (OSError, RuntimeError) as exc:
        print(f"install_bunomi_skill: {exc}", file=sys.stderr)
        return 2
    print(f"{args.name} Skill 已安装：{target}")
    print("新会话触发矩阵与最近一次验证记录见 docs/codex-skill-trigger-test.md。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
