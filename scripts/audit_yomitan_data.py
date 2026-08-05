#!/usr/bin/env python3
"""Audit a downloaded Yomitan cache before it is used for annotations.

This is separate from the dependency-free production audit because the cache
is intentionally ignored by source control and may not exist on a clean clone.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "var" / "yomitan"
REQUIRED_SOURCES = {"terms", "names", "kanji", "forms"}
sys.path.insert(0, str(ROOT / "src"))


class AuditError(RuntimeError):
    pass


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise AuditError(f"无法读取 JSON: {path}: {exc}") from exc


def _sha256(path: Path) -> tuple[int, str]:
    digest = hashlib.sha256()
    size = 0
    try:
        with path.open("rb") as handle:
            for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(chunk)
                size += len(chunk)
    except OSError as exc:
        raise AuditError(f"无法读取词典归档: {path}: {exc}") from exc
    return size, digest.hexdigest()


def audit(root: Path) -> dict[str, Any]:
    manifest_path = root / "manifest.json"
    manifest = _read_json(manifest_path)
    if not isinstance(manifest, dict):
        raise AuditError("manifest.json 必须是对象")
    if manifest.get("repository") != "yomidevs/jmdict-yomitan":
        raise AuditError("manifest 的 repository 不是预期的 yomidevs/jmdict-yomitan")
    release_tag = str(manifest.get("release_tag") or "")
    assets = manifest.get("assets")
    if not release_tag or not isinstance(assets, list):
        raise AuditError("manifest 缺少 release_tag 或 assets")

    seen_kinds: set[str] = set()
    verified_assets: list[dict[str, Any]] = []
    for asset in assets:
        if not isinstance(asset, dict):
            raise AuditError("manifest.assets 存在无效记录")
        filename = str(asset.get("filename") or "")
        kind = str(asset.get("kind") or "")
        expected_size = asset.get("bytes")
        expected_hash = str(asset.get("sha256") or "")
        archive = root / filename
        if not filename or not archive.is_file():
            raise AuditError(f"词典归档不存在: {archive}")
        size, digest = _sha256(archive)
        if size != expected_size or digest != expected_hash:
            raise AuditError(f"词典归档校验失败: {archive}")
        seen_kinds.add(kind)
        verified_assets.append({"filename": filename, "kind": kind, "bytes": size})

    missing_kinds = sorted(REQUIRED_SOURCES - seen_kinds)
    if missing_kinds:
        raise AuditError("manifest 缺少默认数据类型: " + ", ".join(missing_kinds))

    extracted = root / "extracted"
    for source_dir in sorted(path for path in extracted.iterdir() if path.is_dir()):
        index_path = source_dir / "index.json"
        if not index_path.is_file():
            raise AuditError(f"解压词典缺少 index.json: {source_dir}")
        index = _read_json(index_path)
        if not isinstance(index, dict) or index.get("format") != 3:
            raise AuditError(f"不是支持的 Yomitan format 3: {index_path}")

    from bunomi.yomitan import load_yomitan_dictionary

    dictionary = load_yomitan_dictionary(extracted)
    if dictionary.term_count <= 0 or dictionary.kanji_count <= 0:
        raise AuditError(
            f"词典索引为空: terms={dictionary.term_count}, kanji={dictionary.kanji_count}"
        )
    expected_terms = {"日本語", "山田", "東京", "行く"}
    missing_terms = sorted(term for term in expected_terms if not dictionary.lookup(term))
    if missing_terms:
        raise AuditError("词典缺少基本 term 样本: " + ", ".join(missing_terms))
    if not dictionary.kanji_lookup("学"):
        raise AuditError("词典缺少基本 KANJIDIC 样本: 学")
    return {
        "release_tag": release_tag,
        "assets": verified_assets,
        "sources": list(dictionary.sources),
        "term_count": dictionary.term_count,
        "kanji_count": dictionary.kanji_count,
        "sample_terms": sorted(expected_terms),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="审计本地 Yomitan 词典快照")
    parser.add_argument("--root", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        result = audit(args.root.expanduser().resolve())
    except (AuditError, OSError) as exc:
        print(f"audit_yomitan_data: {exc}", file=sys.stderr)
        return 2
    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(
            f"Yomitan cache OK: release={result['release_tag']}, "
            f"terms={result['term_count']}, kanji={result['kanji_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
