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
]

__version__ = "0.1.0"
