"""Command-line interface for Bunomi."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

from . import __version__
from .core import BunomiError, EngineUnavailableError, annotate_text


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bunomi",
        description="为日语文本中的汉字添加可校验的 <ruby> 振假名标注。",
    )
    parser.add_argument("text", nargs="?", help="直接传入一段文本；省略时从 stdin 读取")
    parser.add_argument("-f", "--file", help="从 UTF-8 文本文件读取")
    parser.add_argument("-r", "--romaji", action="store_true", help="使用罗马音标注")
    parser.add_argument(
        "--assume-japanese",
        action="store_true",
        help="仅在你确认文本为日语时使用；跳过中日汉字歧义检查",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "html"),
        default=None,
        help="输出格式；直接文本默认输出 Ruby 内容，--file 默认生成 HTML",
    )
    parser.add_argument("--version", action="version", version=__version__)
    return parser


def _read_input(args: argparse.Namespace) -> str:
    if args.file and args.text is not None:
        raise BunomiError("不能同时使用位置文本和 --file")
    if args.file:
        try:
            return Path(args.file).expanduser().read_text(encoding="utf-8")
        except OSError as exc:
            raise BunomiError(f"无法读取输入文件: {args.file}: {exc}") from exc
    if args.text is not None:
        return args.text
    return sys.stdin.read()


def _render_html(annotated: str) -> str:
    body = annotated.replace("\n", "<br>\n")
    return (
        '<!doctype html>\n<html lang="ja">\n<head>\n'
        '<meta charset="utf-8">\n<title>Bunomi</title>\n'
        '</head>\n<body>\n<main class="bunomi">\n'
        f"{body}\n"
        "</main>\n</body>\n</html>\n"
    )


def _next_file_target(source: Path, suffix: str) -> Path:
    stamp = datetime.now().astimezone().strftime("%Y%m%d-%H%M%S")
    target = source.with_name(f"{source.stem}.{stamp}{suffix}")
    counter = 2
    while target.exists():
        target = source.with_name(f"{source.stem}.{stamp}-{counter}{suffix}")
        counter += 1
    return target


def _write_file_output(content: str, source: Path, suffix: str) -> Path:
    target = _next_file_target(source, suffix)
    try:
        target.write_text(content, encoding="utf-8")
    except OSError as exc:
        raise BunomiError(f"无法写入输出文件: {target}: {exc}") from exc
    return target


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        source = _read_input(args)
        source_path = Path(args.file).expanduser().resolve() if args.file else None
        output_format = args.format or ("html" if source_path else "markdown")
        mode = "romaji" if args.romaji else "hiragana"
        result = annotate_text(
            source,
            mode=mode,
            force=args.assume_japanese,
        )
        for warning in result.warnings:
            print(f"bunomi: warning: {warning}", file=sys.stderr)
        if output_format == "markdown":
            rendered = result.annotated
        else:
            rendered = _render_html(result.annotated)
        if source_path:
            suffix = ".html" if output_format == "html" else ".md"
            target = _write_file_output(rendered, source_path, suffix)
            print(f"处理完成！已保存：{target}", file=sys.stderr)
        else:
            print(rendered, end="" if rendered.endswith("\n") else "\n")
        return 0
    except (BunomiError, EngineUnavailableError) as exc:
        print(f"bunomi: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
