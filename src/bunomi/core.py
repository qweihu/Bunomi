"""Deterministic Japanese detection, furigana rendering, and validation.

The reading engine is isolated from rendering. The reusable
``japanese_language_core.reading`` package owns Fugashi/Sudachi/PyKakasi
adapters; this module owns Bunomi-specific detection, ruby rendering, and
validation.
"""

from __future__ import annotations

from dataclasses import dataclass
import html
import re
from typing import Iterable

from japanese_language_core.reading import (
    EngineUnavailableError,
    ReadingEngine,
    ReadingEngineError,
    ReadingToken,
    PykakasiEngine,
    SudachiEngine,
    align_reading,
    create_engine,
)


KANJI_RE = re.compile(r"[一-龯々〆ヵヶ\u3400-\u4dbf\U00020000-\U0002ffff]")
HIRAGANA_RE = re.compile(r"[ぁ-ゖヷ-ヺ]")
KATAKANA_RE = re.compile(r"[ァ-ヺヽヾー]")
RUBY_RE = re.compile(r"<ruby>(.*?)<rt>(.*?)</rt></ruby>", re.DOTALL)
JAPANESE_PUNCTUATION = set("。、，．！？「」『』【】〈〉《》〔〕・〜～…；：")


class BunomiError(RuntimeError):
    """Base class for user-facing Bunomi errors."""


class JapaneseDetectionError(BunomiError):
    """Raised when input does not look like Japanese text."""


@dataclass(frozen=True)
class DetectionResult:
    """A conservative language/script classification for user input."""

    label: str
    score: float
    japanese_chars: int
    kana_chars: int
    kanji_chars: int
    non_japanese_letters: int

    @property
    def is_japanese(self) -> bool:
        return self.label in {"ja", "mixed"}


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    ruby_count: int
    unannotated_kanji: str
    errors: tuple[str, ...] = ()


@dataclass(frozen=True)
class AnnotationResult:
    source: str
    annotated: str
    detection: DetectionResult
    validation: ValidationResult
    warnings: tuple[str, ...] = ()
    engine: str = ""
    tokens: tuple[ReadingToken, ...] = ()
    overrides_applied: tuple[str, ...] = ()


def is_kanji(char: str) -> bool:
    return bool(char) and bool(KANJI_RE.fullmatch(char))


def has_kanji(text: str) -> bool:
    return any(is_kanji(char) for char in text)


def has_japanese_script(text: str) -> bool:
    return any(
        is_kanji(char)
        or bool(HIRAGANA_RE.fullmatch(char))
        or bool(KATAKANA_RE.fullmatch(char))
        for char in text
    )


def _is_kana(char: str) -> bool:
    return bool(HIRAGANA_RE.fullmatch(char) or KATAKANA_RE.fullmatch(char))


def detect_language(text: str) -> DetectionResult:
    """Classify text without claiming that CJK-only text is Japanese.

    Kana is required because common punctuation and Han characters are
    shared with Chinese. For inputs with at least four Han characters, kana
    must make up at least one quarter of the Han count; sparse-kana text is
    ambiguous. This is a script heuristic, not language identification, and
    cannot separate Chinese and Japanese spans that share Han characters.
    A lower-level caller with known context may use ``force=True``; the CLI
    does not expose that escape hatch.
    """

    japanese_chars = 0
    kana_chars = 0
    kanji_chars = 0
    non_japanese_letters = 0
    meaningful_chars = 0
    punctuation_chars = 0

    for char in text:
        if char.isspace():
            continue
        if is_kanji(char):
            japanese_chars += 1
            kanji_chars += 1
            meaningful_chars += 1
        elif _is_kana(char):
            japanese_chars += 1
            kana_chars += 1
            meaningful_chars += 1
        elif char in JAPANESE_PUNCTUATION:
            japanese_chars += 1
            punctuation_chars += 1
        elif char.isalpha() or char.isdigit():
            non_japanese_letters += 1
            meaningful_chars += 1

    if not text.strip():
        return DetectionResult("empty", 0.0, 0, 0, 0, 0)
    if japanese_chars == 0:
        return DetectionResult("non-ja", 0.0, 0, 0, 0, non_japanese_letters)

    score = japanese_chars / max(meaningful_chars + punctuation_chars, 1)
    sparse_kana = kanji_chars >= 4 and kana_chars * 4 < kanji_chars
    if kana_chars == 0 or sparse_kana:
        label = "ambiguous"
    elif score >= 0.6:
        label = "ja"
    elif score >= 0.25:
        label = "mixed"
    else:
        label = "non-ja"
    return DetectionResult(
        label,
        round(min(score, 1.0), 4),
        japanese_chars,
        kana_chars,
        kanji_chars,
        non_japanese_letters,
    )


def _escape(value: str) -> str:
    return html.escape(value, quote=False)


def _ruby(surface: str, reading: str) -> str:
    if not surface or not reading:
        return _escape(surface)
    return f"<ruby>{_escape(surface)}<rt>{_escape(reading)}</rt></ruby>"


def render_token(token: ReadingToken, mode: str = "hiragana") -> str:
    """Render one engine token as escaped text or a ruby element."""

    if mode not in {"hiragana", "romaji"}:
        raise ValueError("mode must be 'hiragana' or 'romaji'")
    if mode == "romaji":
        if has_japanese_script(token.orig) and token.hepburn:
            return _ruby(token.orig, token.hepburn)
        return _escape(token.orig)
    reading = token.hira
    if not has_kanji(token.orig) or not reading:
        return _escape(token.orig)

    parts = align_reading(token.orig, reading)
    if any(has_kanji(surface) and not part_reading for surface, part_reading in parts):
        parts = [(token.orig, reading)]
    return "".join(
        _ruby(surface, part_reading)
        if part_reading and has_kanji(surface)
        else _escape(surface)
        for surface, part_reading in parts
    )


def validate_annotation(source: str, annotated: str) -> ValidationResult:
    """Check tag balance, source preservation, and unannotated kanji."""

    errors: list[str] = []
    ruby_count = len(RUBY_RE.findall(annotated))
    if annotated.count("<ruby>") != annotated.count("</ruby>"):
        errors.append("ruby 标签未闭合")
    if annotated.count("<rt>") != annotated.count("</rt>"):
        errors.append("rt 标签未闭合")

    without_ruby = RUBY_RE.sub(lambda match: match.group(1), annotated)
    plain = html.unescape(without_ruby)
    if plain != source:
        errors.append("标注结果改变了原始文本")

    unannotated = "".join(char for char in RUBY_RE.sub("", annotated) if is_kanji(char))
    if unannotated:
        errors.append(f"存在未标注汉字: {unannotated}")
    return ValidationResult(not errors, ruby_count, unannotated, tuple(errors))


def _tokens_with_overrides(
    text: str,
    engine: ReadingEngine,
    overrides,
) -> Iterable[ReadingToken]:
    if not overrides:
        yield from engine.tokens(text)
        return
    cursor = 0
    while cursor < len(text):
        matching = next((item for item in overrides if text.startswith(item.phrase, cursor)), None)
        if matching:
            yield ReadingToken(matching.phrase, matching.reading, matching.romaji)
            cursor += len(matching.phrase)
            continue
        next_positions = [text.find(item.phrase, cursor + 1) for item in overrides]
        next_positions = [position for position in next_positions if position >= 0]
        end = min(next_positions) if next_positions else len(text)
        yield from engine.tokens(text[cursor:end])
        cursor = end


def annotate_text(
    text: str,
    *,
    mode: str = "hiragana",
    engine: ReadingEngine | None = None,
    engine_name: str = "auto",
    force: bool = False,
    use_overrides: bool = True,
) -> AnnotationResult:
    """Annotate text and validate the result before returning it."""

    detection = detect_language(text)
    if detection.label == "empty":
        raise JapaneseDetectionError("没有输入内容")
    if not force and detection.label in {"non-ja", "ambiguous"}:
        if detection.label == "ambiguous":
            raise JapaneseDetectionError(
                "日语信号不足，无法可靠判断输入是否为日语；请提供明确的日语文本"
            )
        raise JapaneseDetectionError("输入不像日语文本，请检查内容")
    try:
        active_engine = engine or create_engine(engine_name)
        overrides = ()
        if use_overrides:
            from .rules import load_reading_overrides

            overrides = load_reading_overrides()
        active_tokens = tuple(_tokens_with_overrides(text, active_engine, overrides))
    except ReadingEngineError as exc:
        raise BunomiError(str(exc)) from exc
    annotated = "".join(render_token(token, mode) for token in active_tokens)
    validation = validate_annotation(text, annotated)
    if not validation.ok:
        raise BunomiError("注音结果校验失败: " + "；".join(validation.errors))
    warnings: list[str] = []
    if detection.label == "mixed":
        warnings.append("输入包含非日语内容，已原样保留并只标注日语片段")
    if force and detection.label in {"non-ja", "ambiguous"}:
        warnings.append("已绕过日语检测，请确认汉字读音属于日语")
    applied = tuple(item.id for item in overrides if item.phrase in text)
    return AnnotationResult(
        text,
        annotated,
        detection,
        validation,
        tuple(warnings),
        getattr(active_engine, "name", active_engine.__class__.__name__),
        tuple(active_tokens),
        applied,
    )
