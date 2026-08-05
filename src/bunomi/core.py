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
    create_engine,
    to_hiragana,
)

_to_hiragana = to_hiragana


KANJI_RE = re.compile(r"[一-龯々〆ヵヶ\u3400-\u4dbf\U00020000-\U0002ffff]")
HIRAGANA_RE = re.compile(r"[ぁ-ゖヷ-ヺ]")
KATAKANA_RE = re.compile(r"[ァ-ヺヽヾー]")
KANA_RUN_RE = re.compile(r"[ぁ-ゖァ-ヺヽヾー]+")
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
    dictionary_matches: tuple[dict[str, object], ...] = ()
    dictionary_sources: tuple[str, ...] = ()
    dictionary_term_count: int = 0
    dictionary_kanji_count: int = 0
    dictionary_kanji_matches: tuple[dict[str, object], ...] = ()


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

    A kana or Japanese punctuation signal is required for a confident Japanese
    classification. This avoids silently annotating Chinese text with a
    Japanese dictionary reading. Callers can explicitly override this with
    ``force=True`` at the CLI layer when the context is known.
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
    if kana_chars == 0 and punctuation_chars == 0:
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


def _render_hiragana_token(token: ReadingToken) -> str:
    surface = token.orig
    reading = _to_hiragana(token.hira)
    if not has_kanji(surface):
        return _escape(surface)
    if not reading:
        return _escape(surface)

    # Align kana runs in the surface with the same runs in the reading. This
    # keeps okurigana outside ruby, e.g. 食べる -> <ruby>食<rt>た</rt></ruby>べる.
    kana_runs = list(KANA_RUN_RE.finditer(surface))
    if not kana_runs:
        return _ruby(surface, reading)

    pieces: list[str] = []
    surface_cursor = 0
    reading_cursor = 0
    for kana_match in kana_runs:
        before = surface[surface_cursor : kana_match.start()]
        if before:
            if has_kanji(before):
                kana_hint = _to_hiragana(kana_match.group(0))
                reading_index = reading.find(kana_hint, reading_cursor)
                while reading_index >= 0 and reading_index <= reading_cursor:
                    reading_index = reading.find(kana_hint, reading_index + 1)
                # A repeated kana can occur at the beginning of a reading,
                # e.g. 歌う -> うたう. When a kanji precedes the kana, the
                # first occurrence cannot be the okurigana boundary; choose
                # a later occurrence or fall back to a whole-word ruby.
                if reading_index < 0 or reading_index <= reading_cursor:
                    return _ruby(surface, reading)
                pieces.append(_ruby(before, reading[reading_cursor:reading_index]))
                reading_cursor = reading_index
            else:
                pieces.append(_escape(before))
        kana_text = kana_match.group(0)
        pieces.append(_escape(kana_text))
        kana_hint = _to_hiragana(kana_text)
        if reading.startswith(kana_hint, reading_cursor):
            reading_cursor += len(kana_hint)
        else:
            reading_index = reading.find(kana_hint, reading_cursor)
            if reading_index < 0:
                return _ruby(surface, reading)
            reading_cursor = reading_index + len(kana_hint)
        surface_cursor = kana_match.end()

    after = surface[surface_cursor:]
    if after:
        if has_kanji(after):
            if reading_cursor >= len(reading):
                return _ruby(surface, reading)
            pieces.append(_ruby(after, reading[reading_cursor:]))
        else:
            pieces.append(_escape(after))
    if not pieces:
        return _ruby(surface, reading)
    return "".join(pieces)


def render_token(token: ReadingToken, mode: str = "hiragana") -> str:
    """Render one engine token as escaped text or a ruby element."""

    if mode not in {"hiragana", "romaji"}:
        raise ValueError("mode must be 'hiragana' or 'romaji'")
    if mode == "romaji":
        if has_japanese_script(token.orig) and token.hepburn:
            return _ruby(token.orig, token.hepburn)
        return _escape(token.orig)
    return _render_hiragana_token(token)


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
    dictionary=None,
) -> AnnotationResult:
    """Annotate text and validate the result before returning it."""

    detection = detect_language(text)
    if detection.label == "empty":
        raise JapaneseDetectionError("没有输入内容")
    if not force and detection.label in {"non-ja", "ambiguous"}:
        if detection.label == "ambiguous":
            raise JapaneseDetectionError(
                "输入只有汉字，无法可靠判断是日语；确认是日语后请使用 --force"
            )
        raise JapaneseDetectionError("输入不像日语文本，请检查内容或使用 --force")
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
    dictionary_matches: tuple[dict[str, object], ...] = ()
    dictionary_sources: tuple[str, ...] = ()
    dictionary_term_count = 0
    dictionary_kanji_count = 0
    dictionary_kanji_matches: tuple[dict[str, object], ...] = ()
    if dictionary is not None:
        dictionary_sources = tuple(getattr(dictionary, "sources", ()))
        dictionary_term_count = int(getattr(dictionary, "term_count", 0))
        dictionary_kanji_count = int(getattr(dictionary, "kanji_count", 0))
        matches = []
        for token in active_tokens:
            if not token.hira or not token.orig or not has_kanji(token.orig):
                continue
            match = dictionary.audit(token.orig, _to_hiragana(token.hira))
            if match is not None:
                matches.append(match.as_dict())
        dictionary_matches = tuple(matches)
        kanji_matches: list[dict[str, object]] = []
        seen_kanji: set[tuple[str, str]] = set()
        for token in active_tokens:
            for character in token.orig:
                if not has_kanji(character):
                    continue
                for item in dictionary.kanji_lookup(character):
                    key = (item.source, item.character)
                    if key in seen_kanji:
                        continue
                    seen_kanji.add(key)
                    kanji_matches.append(item.as_dict())
        dictionary_kanji_matches = tuple(kanji_matches)
    return AnnotationResult(
        text,
        annotated,
        detection,
        validation,
        tuple(warnings),
        getattr(active_engine, "name", active_engine.__class__.__name__),
        tuple(active_tokens),
        applied,
        dictionary_matches,
        dictionary_sources,
        dictionary_term_count,
        dictionary_kanji_count,
        dictionary_kanji_matches,
    )
