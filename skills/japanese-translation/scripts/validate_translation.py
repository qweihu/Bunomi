#!/usr/bin/env python3
"""Validate a line-preserving Japanese translation against its source text.

Checks:
1. Paired mode: the number of non-empty translation lines equals the number of
   non-empty source lines.
2. Source fidelity: when the source contains ruby tags, stripping ruby/rt from
   each source line must reproduce the original Japanese text.
3. Output hygiene: the translation contains no HTML other than ruby/rt, and
   ruby/rt tags are balanced.
4. Kana warning: translation lines containing hiragana/katakana are reported
   (usually an untranslated fragment; may be acceptable for quoted terms).

Exit status: 0 = OK, 1 = structural errors, 3 = only warnings (with
--strict-warnings).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path


RUBY_RE = re.compile(r"<ruby>(.*?)<rt>(.*?)</rt></ruby>", re.S)
TAG_RE = re.compile(r"<[^>]+>")
KANA_RE = re.compile(r"[\u3041-\u3096\u30a1-\u30f6\uff66-\uff9d]")


def read_lines(path: str) -> list[str]:
    if path == "-":
        return sys.stdin.read().splitlines()
    return Path(path).read_text(encoding="utf-8").splitlines()


def strip_ruby(line: str) -> str:
    return TAG_RE.sub("", RUBY_RE.sub(r"\1", line))


def check_balanced_tags(line: str, label: str, errors: list[str]) -> None:
    for tag in ("ruby", "rt"):
        opens = len(re.findall(rf"<{tag}>", line))
        closes = len(re.findall(rf"</{tag}>", line))
        if opens != closes:
            errors.append(f"{label}: <{tag}> 标签不平衡（开 {opens} / 闭 {closes}）")


def check_no_foreign_html(line: str, label: str, errors: list[str]) -> None:
    for tag in TAG_RE.findall(line):
        name = tag.lstrip("</").rstrip(">").split()[0]
        if name not in {"ruby", "rt"}:
            errors.append(f"{label}: 出现非 ruby/rt 的 HTML 标签 {tag}")


def check_source_fidelity(source_lines: list[str], errors: list[str]) -> None:
    for idx, line in enumerate(source_lines, start=1):
        if "<ruby>" not in line:
            continue
        stripped = strip_ruby(line)
        expected = RUBY_RE.sub(r"\1", line)
        if stripped != expected:
            errors.append(f"源行 {idx}: ruby 剥离后与原文不一致")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", help="源日语文本文件（- 表示 stdin）")
    parser.add_argument("--translation", required=True, help="翻译文本文件（- 表示 stdin）")
    parser.add_argument("--paired", action="store_true", help="要求翻译行数与源行数一致")
    parser.add_argument("--no-kana-warn", action="store_true", help="关闭假名漏译警告")
    parser.add_argument("--strict-warnings", action="store_true", help="存在警告时退出码为 3")
    args = parser.parse_args(argv)

    errors: list[str] = []
    warnings: list[str] = []

    translation = read_lines(args.translation)
    source = read_lines(args.source) if args.source else None

    for idx, line in enumerate(translation, start=1):
        label = f"翻译行 {idx}"
        check_balanced_tags(line, label, errors)
        check_no_foreign_html(line, label, errors)
        if not args.no_kana_warn:
            kana = KANA_RE.findall(line)
            if kana:
                warnings.append(f"{label}: 出现假名 {len(kana)} 处，可能是漏译（专名/引用除外）")

    if source is not None:
        check_source_fidelity(source, errors)
        if args.paired:
            src_content = [ln for ln in source if ln.strip()]
            tgt_content = [ln for ln in translation if ln.strip()]
            if len(src_content) != len(tgt_content):
                errors.append(
                    f"行数不匹配：源 {len(src_content)} 行，翻译 {len(tgt_content)} 行"
                )

    for err in errors:
        print(f"[错误] {err}", file=sys.stderr)
    for warn in warnings:
        print(f"[警告] {warn}")

    if errors:
        print(f"校验失败：{len(errors)} 个错误，{len(warnings)} 个警告", file=sys.stderr)
        return 1
    if warnings and args.strict_warnings:
        print(f"校验通过（含警告）：{len(warnings)} 个警告")
        return 3
    print(f"校验通过：{len(translation)} 行翻译，{len(warnings)} 个警告")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
