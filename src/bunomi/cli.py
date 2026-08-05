"""Command-line interface for Bunomi."""

from __future__ import annotations

import argparse
from pathlib import Path
import json
import sys

from japanese_language_core.reading import conjugate
from japanese_language_core.sentences import SentenceBank

from . import __version__
from .core import BunomiError, EngineUnavailableError, annotate_text
from .yomitan import YomitanDataError, load_yomitan_dictionary


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="bunomi",
        description="为日语文本中的汉字添加可校验的 <ruby> 振假名标注。",
    )
    parser.add_argument("text", nargs="?", help="直接传入一段文本；省略时从 stdin 读取")
    parser.add_argument("-f", "--file", help="从 UTF-8 文本文件读取")
    parser.add_argument("-r", "--romaji", action="store_true", help="使用罗马音标注")
    parser.add_argument(
        "--engine",
        choices=("auto", "sudachi", "pykakasi"),
        default="auto",
        help="读音引擎，默认 auto（优先 Sudachi，缺失时回退 PyKakasi）",
    )
    parser.add_argument("--no-overrides", action="store_true", help="禁用已审核的短语读音覆盖规则")
    parser.add_argument(
        "--dictionary-dir",
        help="可选的 Yomitan 词典目录或 var/yomitan/extracted；只用于 JSON 审计增强",
    )
    parser.add_argument(
        "--format",
        choices=("markdown", "html", "json"),
        default="markdown",
        help="输出格式，默认 markdown",
    )
    parser.add_argument("-o", "--output", help="明确指定输出文件；省略时只输出到 stdout")
    parser.add_argument("--overwrite", action="store_true", help="允许覆盖已存在的输出文件")
    parser.add_argument("--create-parent", action="store_true", help="输出目录不存在时创建目录")
    parser.add_argument("--conjugations", action="store_true", help="JSON 输出附带辞書形的常用活用形")
    parser.add_argument("--sentences", help="可选的 Tatoeba 日语句表 TSV（JSON 输出附带例句）")
    parser.add_argument("--sentence-links", help="可选的 Tatoeba 链接 TSV（配合 --sentences）")
    parser.add_argument("--force", action="store_true", help="绕过日语检测；仅在确认输入是日语时使用")
    parser.add_argument("-q", "--quiet", action="store_true", help="导出文件时不打印保存提示")
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


def _render_json(
    result,
    mode: str,
    *,
    conjugations: bool = False,
    examples: dict[str, list[dict[str, object]]] | None = None,
) -> str:
    token_payload = []
    for token in result.tokens:
        item = {
            "orig": token.orig,
            "hira": token.hira,
            "hepburn": token.hepburn,
            "part_of_speech": token.part_of_speech,
            "dictionary_form": token.dictionary_form,
            "normalized_form": token.normalized_form,
        }
        if conjugations and token.dictionary_form:
            item["conjugations"] = conjugate(token.dictionary_form)
        token_payload.append(item)
    payload = {
        "language": {
            "label": result.detection.label,
            "score": result.detection.score,
            "japanese_chars": result.detection.japanese_chars,
            "kana_chars": result.detection.kana_chars,
            "kanji_chars": result.detection.kanji_chars,
        },
        "mode": mode,
        "engine": result.engine,
        "annotated": result.annotated,
        "tokens": token_payload,
        "ruby_count": result.validation.ruby_count,
        "warnings": list(result.warnings),
        "overrides_applied": list(result.overrides_applied),
        "dictionary": {
            "enabled": bool(result.dictionary_sources),
            "sources": list(result.dictionary_sources),
            "term_count": result.dictionary_term_count,
            "kanji_count": result.dictionary_kanji_count,
            "matches": list(result.dictionary_matches),
            "kanji_matches": list(result.dictionary_kanji_matches),
        },
    }
    if examples:
        payload["examples"] = examples
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _write_output(content: str, raw_path: str, *, overwrite: bool, create_parent: bool) -> Path:
    if raw_path == "-":
        print(content, end="")
        return Path("-")
    target = Path(raw_path).expanduser().resolve()
    if target.exists() and target.is_dir():
        raise BunomiError(f"输出路径是目录，请指定具体文件: {target}")
    if not target.parent.exists():
        if not create_parent:
            raise BunomiError(
                f"输出目录不存在: {target.parent}；确认目录后重试，或加 --create-parent"
            )
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise BunomiError(f"无法创建输出目录: {target.parent}: {exc}") from exc
    if target.exists() and not overwrite:
        raise BunomiError(f"输出文件已存在，为避免覆盖请换路径或加 --overwrite: {target}")
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
        mode = "romaji" if args.romaji else "hiragana"
        dictionary = None
        if args.dictionary_dir:
            try:
                dictionary = load_yomitan_dictionary(args.dictionary_dir)
            except YomitanDataError as exc:
                raise BunomiError(str(exc)) from exc
        result = annotate_text(
            source,
            mode=mode,
            engine_name=args.engine,
            force=args.force,
            use_overrides=not args.no_overrides,
            dictionary=dictionary,
        )
        if args.format == "markdown":
            rendered = result.annotated
        elif args.format == "html":
            rendered = _render_html(result.annotated)
        else:
            examples = None
            if args.sentences or args.sentence_links:
                if not (args.sentences and args.sentence_links):
                    raise BunomiError("--sentences 与 --sentence-links 必须同时提供")
                try:
                    bank = SentenceBank.from_tatoeba(
                        args.sentences, args.sentence_links
                    )
                except OSError as exc:
                    raise BunomiError(f"无法读取句库文件: {exc}") from exc
                examples = {}
                for token in result.tokens:
                    surface = token.orig.strip()
                    if not surface or surface in examples:
                        continue
                    hits = bank.lookup(surface)
                    if hits:
                        examples[surface] = [
                            {
                                "text": sentence.text,
                                "translations": [
                                    t.text
                                    for t in bank.translations(sentence.id)
                                ],
                            }
                            for sentence in hits[:3]
                        ]
            rendered = _render_json(
                result,
                mode,
                conjugations=args.conjugations,
                examples=examples,
            )
        if args.output:
            target = _write_output(
                rendered,
                args.output,
                overwrite=args.overwrite,
                create_parent=args.create_parent,
            )
            if target != Path("-") and not args.quiet:
                print(f"处理完成！已保存：{target}", file=sys.stderr)
        else:
            print(rendered, end="" if rendered.endswith("\n") else "\n")
        return 0
    except (BunomiError, EngineUnavailableError) as exc:
        print(f"bunomi: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
