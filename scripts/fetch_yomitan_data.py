#!/usr/bin/env python3
"""Fetch a pinned Yomitan dictionary release into a local, auditable cache.

The downloaded archives are intentionally kept outside the Python package. The
script records the release tag, asset URL, byte size, SHA-256 digest, and fetch
time so a later annotation or benchmark can identify exactly which dictionary
snapshot was used.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
import sys
from typing import Any
from urllib.request import Request, urlopen
import zipfile


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG = ROOT / "data" / "yomitan-sources.json"
DEFAULT_OUTPUT = ROOT / "var" / "yomitan"
USER_AGENT = "bunomi-yomitan-fetcher/0.1"


class FetchError(RuntimeError):
    """Raised for a reproducible source or archive error."""


def _read_json(path: Path) -> dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise FetchError(f"无法读取配置文件: {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise FetchError(f"配置文件必须是 JSON 对象: {path}")
    return value


def _request_json(url: str) -> dict[str, Any]:
    request = Request(
        url,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": USER_AGENT,
        },
    )
    try:
        with urlopen(request, timeout=30) as response:
            payload = response.read()
    except OSError as exc:
        raise FetchError(f"无法访问 Yomitan 发布接口: {url}: {exc}") from exc
    try:
        value = json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise FetchError(f"Yomitan 发布接口返回了无效 JSON: {url}") from exc
    if not isinstance(value, dict):
        raise FetchError(f"Yomitan 发布接口返回格式异常: {url}")
    return value


def _download(url: str, target: Path, *, force: bool) -> tuple[int, str]:
    if target.exists() and not force:
        raise FetchError(f"目标文件已存在，为避免覆盖请加 --force: {target}")
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + ".part")
    digest = hashlib.sha256()
    size = 0
    request = Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=120) as response, temporary.open("wb") as handle:
            while True:
                chunk = response.read(1024 * 1024)
                if not chunk:
                    break
                handle.write(chunk)
                digest.update(chunk)
                size += len(chunk)
        temporary.replace(target)
    except OSError as exc:
        try:
            temporary.unlink()
        except FileNotFoundError:
            pass
        raise FetchError(f"无法下载 Yomitan 数据: {url}: {exc}") from exc
    return size, digest.hexdigest()


def _safe_extract(archive: Path, destination: Path) -> list[str]:
    """Extract a ZIP only when every member stays inside destination."""

    destination = destination.resolve()
    if destination.exists():
        raise FetchError(f"解压目录已存在，请换目录或先人工确认后删除: {destination}")
    destination.mkdir(parents=True)
    extracted: list[str] = []
    try:
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                candidate = (destination / member.filename).resolve()
                if candidate != destination and destination not in candidate.parents:
                    raise FetchError(f"ZIP 包含越界路径，拒绝解压: {member.filename}")
            bundle.extractall(destination)
            extracted = [member.filename for member in bundle.infolist()]
    except (OSError, zipfile.BadZipFile) as exc:
        shutil.rmtree(destination, ignore_errors=True)
        raise FetchError(f"无法解压词典归档 {archive}: {exc}") from exc
    return extracted


def _asset_config(config: dict[str, Any]) -> dict[str, dict[str, Any]]:
    assets: dict[str, dict[str, Any]] = {}
    for key in ("default_assets", "optional_assets"):
        for item in config.get(key, []):
            if not isinstance(item, dict) or not item.get("filename"):
                raise FetchError(f"配置中的 {key} 存在无效资产")
            assets[str(item["filename"])] = item
    return assets


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="获取 Yomitan/JMdict 词典快照，并登记版本与 SHA-256。"
    )
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument(
        "--asset",
        action="append",
        help="指定要下载的资产文件名；可重复传入。省略时下载默认资产。",
    )
    parser.add_argument(
        "--include-optional",
        action="store_true",
        help="同时下载配置中的可选资产，例如带例句的 JMdict。",
    )
    parser.add_argument("--list", action="store_true", help="只列出最新 release 的资产，不下载")
    parser.add_argument("--extract", action="store_true", help="安全解压 ZIP 到 extracted/ 下")
    parser.add_argument("--force", action="store_true", help="允许覆盖同名缓存文件")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        config = _read_json(args.config.expanduser().resolve())
        release_api = str(config["release_api"])
        release = _request_json(release_api)
        tag = str(release.get("tag_name", ""))
        assets = release.get("assets")
        if not tag or not isinstance(assets, list):
            raise FetchError("最新 Yomitan release 缺少 tag_name 或 assets")

        available = {
            str(asset.get("name")): asset
            for asset in assets
            if isinstance(asset, dict) and asset.get("name")
        }
        if args.list:
            for name in sorted(available):
                print(name)
            return 0

        configured = _asset_config(config)
        if args.asset:
            requested = list(dict.fromkeys(args.asset))
        else:
            requested = [item["filename"] for item in config.get("default_assets", [])]
            if args.include_optional:
                requested.extend(item["filename"] for item in config.get("optional_assets", []))

        unknown = [name for name in requested if name not in available]
        if unknown:
            raise FetchError("最新 release 没有这些资产: " + ", ".join(unknown))

        output_dir = args.output_dir.expanduser().resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        fetched_at = datetime.now(timezone.utc).isoformat()
        records: list[dict[str, Any]] = []
        for name in requested:
            asset = available[name]
            target = output_dir / name
            size, sha256 = _download(str(asset["browser_download_url"]), target, force=args.force)
            record: dict[str, Any] = {
                "filename": name,
                "kind": configured.get(name, {}).get("kind", "unclassified"),
                "role": configured.get(name, {}).get("role", ""),
                "release_tag": tag,
                "source_url": str(asset["browser_download_url"]),
                "bytes": size,
                "sha256": sha256,
                "fetched_at": fetched_at,
            }
            if args.extract:
                extracted = _safe_extract(
                    target,
                    output_dir / "extracted" / Path(name).stem,
                )
                record["extracted_files"] = len(extracted)
            records.append(record)

        manifest = {
            "schema_version": 1,
            "repository": config.get("repository"),
            "release_tag": tag,
            "release_url": config.get("release_page"),
            "fetched_at": fetched_at,
            "assets": records,
        }
        (output_dir / "manifest.json").write_text(
            json.dumps(manifest, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        print(f"已获取 {len(records)} 个 Yomitan 词典资产，release={tag}")
        print(f"清单：{output_dir / 'manifest.json'}")
        return 0
    except (KeyError, FetchError, OSError) as exc:
        print(f"fetch_yomitan_data: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
