"""Read-only access to locally cached Yomitan dictionary banks.

Format parsing is delegated to ``japanese_language_core.dictionary`` (which
reads both zip bundles and extracted directories). This module keeps Bunomi's
audit semantics and merges multiple dictionary directories into one index.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from japanese_language_core.dictionary import (
    NameEntry,
    YomitanDictionary as CoreDictionary,
)
from japanese_language_core.dictionary.jmnedict import readings_of


class YomitanDataError(RuntimeError):
    """Raised when a local Yomitan dictionary cache is invalid."""


def _normalize_reading(value: str) -> str:
    """Compare kana readings independent of hiragana/katakana choice."""

    normalized: list[str] = []
    for char in value:
        codepoint = ord(char)
        if 0x30A1 <= codepoint <= 0x30F6:
            normalized.append(chr(codepoint - 0x60))
        else:
            normalized.append(char)
    return "".join(normalized)


@dataclass(frozen=True)
class YomitanTerm:
    source: str
    term: str
    reading: str
    score: int
    sequence: int | None
    definition_count: int
    definition_tags: tuple[str, ...] = ()
    rules: tuple[str, ...] = ()
    term_tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class YomitanMatch:
    surface: str
    engine_reading: str
    candidate_readings: tuple[str, ...]
    sources: tuple[str, ...]
    exact_reading_match: bool
    candidate_count: int
    candidate_tags: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "surface": self.surface,
            "engine_reading": self.engine_reading,
            "candidate_readings": list(self.candidate_readings),
            "sources": list(self.sources),
            "exact_reading_match": self.exact_reading_match,
            "reading_agreement": self.exact_reading_match,
            "reading_status": "match" if self.exact_reading_match else "candidate-disagrees",
            "candidate_count": self.candidate_count,
            "candidate_tags": list(self.candidate_tags),
        }


@dataclass(frozen=True)
class YomitanKanji:
    """A KANJIDIC character record published in Yomitan format."""

    source: str
    character: str
    onyomi: tuple[str, ...]
    kunyomi: tuple[str, ...]
    meanings: tuple[str, ...]
    tags: tuple[str, ...]
    frequency: int | None
    stroke_count: int | None
    references: tuple[tuple[str, str], ...]

    def as_dict(self) -> dict[str, Any]:
        return {
            "character": self.character,
            "source": self.source,
            "onyomi": list(self.onyomi),
            "kunyomi": list(self.kunyomi),
            "meanings": list(self.meanings),
            "tags": list(self.tags),
            "frequency": self.frequency,
            "stroke_count": self.stroke_count,
            "references": dict(self.references),
        }


class YomitanDictionary:
    """A read-only index of Yomitan term banks (Bunomi audit facade)."""

    def __init__(
        self,
        terms: tuple[YomitanTerm, ...],
        sources: tuple[str, ...],
        kanji: tuple[YomitanKanji, ...] = (),
        names: dict[str, tuple[NameEntry, ...]] | None = None,
    ) -> None:
        self._terms = terms
        self._kanji = kanji
        self._sources = sources
        self._names = names or {}
        by_term: dict[str, list[YomitanTerm]] = {}
        for item in terms:
            by_term.setdefault(item.term, []).append(item)
        self._by_term = {key: tuple(value) for key, value in by_term.items()}
        by_character: dict[str, list[YomitanKanji]] = {}
        for item in kanji:
            by_character.setdefault(item.character, []).append(item)
        self._by_character = {
            key: tuple(value) for key, value in by_character.items()
        }

    @property
    def sources(self) -> tuple[str, ...]:
        return self._sources

    @property
    def term_count(self) -> int:
        return len(self._terms)

    @property
    def kanji_count(self) -> int:
        return len(self._kanji)

    def lookup(self, term: str) -> tuple[YomitanTerm, ...]:
        return self._by_term.get(term, ())

    def kanji_lookup(self, character: str) -> tuple[YomitanKanji, ...]:
        return self._by_character.get(character, ())

    def lookup_names(self, expression: str) -> tuple[NameEntry, ...]:
        return self._names.get(expression, ())

    def audit(self, surface: str, engine_reading: str) -> YomitanMatch | None:
        candidates = self.lookup(surface)
        if not candidates:
            return None
        readings = tuple(dict.fromkeys(item.reading for item in candidates if item.reading))
        sources = tuple(dict.fromkeys(item.source for item in candidates))
        candidate_tags = tuple(
            dict.fromkeys(
                tag
                for item in candidates
                for tag in (*item.definition_tags, *item.term_tags)
                if tag
            )
        )
        return YomitanMatch(
            surface=surface,
            engine_reading=engine_reading,
            candidate_readings=readings,
            sources=sources,
            exact_reading_match=any(
                _normalize_reading(reading) == _normalize_reading(engine_reading)
                for reading in readings
            ),
            candidate_count=len(candidates),
            candidate_tags=candidate_tags,
        )


def _dictionary_dirs(root: Path) -> tuple[Path, ...]:
    if not root.exists() or not root.is_dir():
        raise YomitanDataError(f"Yomitan 词典目录不存在: {root}")
    if (root / "index.json").exists():
        return (root,)
    directories = tuple(
        sorted(
            path
            for path in root.iterdir()
            if path.is_dir() and (path / "index.json").exists()
        )
    )
    if not directories:
        raise YomitanDataError(f"目录中没有找到 Yomitan index.json: {root}")
    return directories


def load_yomitan_dictionary(root: str | Path) -> YomitanDictionary:
    """Load and merge all Yomitan dictionaries below ``root``."""

    root_path = Path(root).expanduser().resolve()
    terms: list[YomitanTerm] = []
    kanji: list[YomitanKanji] = []
    sources: list[str] = []
    names: dict[str, tuple[NameEntry, ...]] = {}
    for directory in _dictionary_dirs(root_path):
        core = CoreDictionary(directory)
        source = core.index.title or directory.name
        if source not in sources:
            sources.append(source)
        for expression in core.all_expressions():
            for entry in core.lookup_terms(expression):
                candidates = (
                    (entry.reading,) if entry.reading else readings_of(entry)
                )
                for reading in candidates:
                    terms.append(
                        YomitanTerm(
                            source=entry.source or source,
                            term=entry.expression,
                            reading=reading,
                            score=entry.score,
                            sequence=entry.sequence,
                            definition_count=len(entry.definitions),
                            definition_tags=tuple(entry.tags),
                            rules=tuple(entry.rules),
                            term_tags=(),
                        )
                    )
            hits = core.lookup_names(expression)
            if hits:
                names[expression] = tuple(hits)
        for character in core.all_characters():
            for item in core.lookup_kanji(character):
                strokes = item.stats.get("strokes")
                frequency = item.frequency.value if item.frequency else None
                if frequency is None and item.stats.get("freq") is not None:
                    try:
                        frequency = int(item.stats["freq"])
                    except (TypeError, ValueError):
                        frequency = None
                kanji.append(
                    YomitanKanji(
                        source=item.source or source,
                        character=item.character,
                        onyomi=tuple(item.onyomi),
                        kunyomi=tuple(item.kunyomi),
                        meanings=tuple(item.meanings),
                        tags=tuple(item.tags),
                        frequency=frequency,
                        stroke_count=int(strokes) if strokes is not None else None,
                        references=tuple(
                            sorted(
                                (str(key), str(value))
                                for key, value in item.stats.items()
                            )
                        ),
                    )
                )
    if not terms and not kanji:
        raise YomitanDataError(f"Yomitan 词典没有 term bank 或 kanji bank: {root_path}")
    return YomitanDictionary(tuple(terms), tuple(sources), tuple(kanji), names)
