#!/usr/bin/env python3
"""Produce an auditable report of engine/Yomitan reading disagreements."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ROOT = ROOT / "var" / "yomitan" / "extracted"
DEFAULT_FIXTURE = ROOT / "tests" / "fixtures" / "golden_cases.json"
sys.path.insert(0, str(ROOT / "src"))


def _read_json(path: Path) -> Any:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"无法读取 JSON: {path}: {exc}") from exc


def build_report(dictionary_root: Path, fixture_path: Path) -> dict[str, Any]:
    from bunomi.core import BunomiError, annotate_text
    from bunomi.yomitan import load_yomitan_dictionary

    dictionary = load_yomitan_dictionary(dictionary_root)
    cases = _read_json(fixture_path)
    if not isinstance(cases, list):
        raise RuntimeError(f"标准语料必须是数组: {fixture_path}")

    disagreements: list[dict[str, Any]] = []
    processed = 0
    skipped = 0
    for case in cases:
        if not isinstance(case, dict) or "input" not in case:
            raise RuntimeError(f"标准语料存在无效条目: {fixture_path}")
        if "expected_error" in case:
            skipped += 1
            continue
        processed += 1
        try:
            result = annotate_text(
                str(case["input"]),
                dictionary=dictionary,
                force=True,
            )
        except BunomiError as exc:
            raise RuntimeError(f"标准语料无法注音 {case.get('id')}: {exc}") from exc
        for match in result.dictionary_matches:
            if match.get("reading_status") != "match":
                disagreements.append(
                    {
                        "case_id": case.get("id"),
                        "surface": match.get("surface"),
                        "engine_reading": match.get("engine_reading"),
                        "candidate_readings": match.get("candidate_readings", []),
                        "candidate_tags": match.get("candidate_tags", []),
                        "sources": match.get("sources", []),
                        "reading_status": match.get("reading_status"),
                    }
                )

    manifest_path = dictionary_root.parent / "manifest.json"
    manifest = _read_json(manifest_path) if manifest_path.is_file() else {}
    return {
        "release_tag": manifest.get("release_tag"),
        "dictionary_sources": list(dictionary.sources),
        "term_count": dictionary.term_count,
        "kanji_count": dictionary.kanji_count,
        "processed_cases": processed,
        "skipped_cases": skipped,
        "disagreement_count": len(disagreements),
        "disagreements": disagreements,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="审计主引擎与 Yomitan 候选读音的差异")
    parser.add_argument("--dictionary-dir", type=Path, default=DEFAULT_ROOT)
    parser.add_argument("--fixture", type=Path, default=DEFAULT_FIXTURE)
    parser.add_argument("--fail-on-disagreement", action="store_true")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(argv)
    try:
        report = build_report(
            args.dictionary_dir.expanduser().resolve(),
            args.fixture.expanduser().resolve(),
        )
    except (OSError, RuntimeError) as exc:
        print(f"audit_reading_disagreements: {exc}", file=sys.stderr)
        return 2

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(
            f"reading audit: release={report['release_tag']}, "
            f"cases={report['processed_cases']}, "
            f"disagreements={report['disagreement_count']}"
        )
        for item in report["disagreements"]:
            print(
                f"- {item['case_id']}: {item['surface']} "
                f"{item['engine_reading']} vs {', '.join(item['candidate_readings'])}"
            )
    if args.fail_on_disagreement and report["disagreement_count"]:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
