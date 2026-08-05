"""Bunomi: Japanese furigana annotation for learners."""

from .core import (
    AnnotationResult,
    DetectionResult,
    PykakasiEngine,
    ReadingToken,
    SudachiEngine,
    annotate_text,
    create_engine,
    detect_language,
    validate_annotation,
)
from .yomitan import (
    YomitanDataError,
    YomitanDictionary,
    YomitanKanji,
    YomitanMatch,
    YomitanTerm,
    load_yomitan_dictionary,
)

__all__ = [
    "AnnotationResult",
    "DetectionResult",
    "PykakasiEngine",
    "ReadingToken",
    "SudachiEngine",
    "annotate_text",
    "create_engine",
    "detect_language",
    "validate_annotation",
    "YomitanDataError",
    "YomitanDictionary",
    "YomitanKanji",
    "YomitanMatch",
    "YomitanTerm",
    "load_yomitan_dictionary",
]

__version__ = "0.1.0"
