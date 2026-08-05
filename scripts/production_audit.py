#!/usr/bin/env python3
"""Run Bunomi's repeatable production-readiness audit.

The audit intentionally compares real engine output with a small, reviewed
golden corpus. A passing unit test suite is not enough if a contextual reading
is wrong, so blocking golden mismatches fail this command.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
FIXTURE_PATH = ROOT / "tests" / "fixtures" / "golden_cases.json"
sys.path.insert(0, str(ROOT / "src"))


def locate_validator() -> Path | None:
    codex_home = Path(os.environ.get("CODEX_HOME", Path.home() / ".codex"))
    candidates = [
        Path(os.environ["BUNOMI_SKILL_VALIDATOR"])
        if os.environ.get("BUNOMI_SKILL_VALIDATOR")
        else None,
        codex_home / "skills/.system/skill-creator/scripts/quick_validate.py",
        Path("/Users/qwei/.codex/skills/.system/skill-creator/scripts/quick_validate.py"),
    ]
    return next((candidate for candidate in candidates if candidate and candidate.exists()), None)


def run_command(command: list[str], *, cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    environment = dict(os.environ)
    source_path = str(ROOT / "src")
    environment["PYTHONPATH"] = source_path + (os.pathsep + environment["PYTHONPATH"] if environment.get("PYTHONPATH") else "")
    return subprocess.run(command, cwd=cwd, env=environment, text=True, capture_output=True)


def find_validator_python() -> str:
    """Use an interpreter that has the validator's optional YAML dependency."""

    candidates = [sys.executable, shutil.which("python3"), shutil.which("python")]
    for candidate in candidates:
        if not candidate:
            continue
        probe = subprocess.run([candidate, "-c", "import yaml"], capture_output=True, text=True)
        if probe.returncode == 0:
            return candidate
    return sys.executable


def check(name: str, passed: bool, detail: str) -> tuple[str, bool, str]:
    return name, passed, detail


def run_audit() -> list[tuple[str, bool, str]]:
    results: list[tuple[str, bool, str]] = []

    validator_path = locate_validator()
    if validator_path:
        validator = run_command([find_validator_python(), str(validator_path), str(ROOT)])
        results.append(check("skill-structure", validator.returncode == 0, validator.stdout.strip() or validator.stderr.strip()))
    else:
        results.append(check("skill-structure", False, "skill-creator quick_validate.py is not available"))

    unit = run_command([sys.executable, "-m", "unittest", "discover", "-s", "tests"])
    results.append(check("unit-and-cli-tests", unit.returncode == 0, unit.stdout.strip() or unit.stderr.strip()))

    try:
        from bunomi.core import BunomiError, annotate_text
    except ImportError as exc:
        results.append(check("real-engine-import", False, str(exc)))
        return results

    cases = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    for case in cases:
        case_id = case["id"]
        try:
            result = annotate_text(case["input"])
            if "expected_error" in case:
                results.append(check(case_id, False, "expected an error but annotation succeeded"))
                continue
            detail_parts = []
            passed = result.detection.label == case["expected_label"]
            if not passed:
                detail_parts.append(f"label={result.detection.label!r}, expected={case['expected_label']!r}")
            if result.annotated != case["expected_output"]:
                passed = False
                detail_parts.append(f"output={result.annotated!r}, expected={case['expected_output']!r}")
            if case.get("expected_warning") and not result.warnings:
                passed = False
                detail_parts.append("expected a mixed-input warning")
            results.append(check(case_id, passed, "; ".join(detail_parts) or "matched reviewed output"))
        except BunomiError as exc:
            if "expected_error" in case:
                passed = case["expected_error"] in str(exc)
                results.append(check(case_id, passed, str(exc)))
            else:
                results.append(check(case_id, False, f"unexpected error: {exc}"))

    for case in cases:
        if "expected_error" not in case:
            continue
        case_id = case["id"]
        cli = run_command([sys.executable, "-m", "bunomi", case["input"]])
        passed = cli.returncode != 0 and case["expected_error"] in cli.stderr
        results.append(check(f"cli-{case_id}", passed, cli.stderr.strip() or "expected CLI error"))

    sudachi_cli = run_command([sys.executable, "-m", "bunomi", "降り止む", "--engine", "sudachi", "--format", "json"])
    sudachi_engine_ok = sudachi_cli.returncode == 0 and '"engine": "sudachi"' in sudachi_cli.stdout
    results.append(check("engine-sudachi-selection", sudachi_engine_ok, sudachi_cli.stdout.strip() or sudachi_cli.stderr.strip()))
    pykakasi_cli = run_command([sys.executable, "-m", "bunomi", "日本語", "--force", "--engine", "pykakasi", "--format", "json"])
    pykakasi_engine_ok = pykakasi_cli.returncode == 0 and '"engine": "pykakasi"' in pykakasi_cli.stdout
    results.append(check("engine-pykakasi-fallback", pykakasi_engine_ok, pykakasi_cli.stdout.strip() or pykakasi_cli.stderr.strip()))

    with tempfile.TemporaryDirectory(prefix="bunomi-audit-") as temp_directory:
        temp_root = Path(temp_directory)
        skill_target = temp_root / "codex" / "skills" / "bunomi"
        skill_install = run_command(
            [
                sys.executable,
                str(ROOT / "scripts" / "install_bunomi_skill.py"),
                "--destination",
                str(skill_target),
            ]
        )
        results.append(
            check(
                "skill-install-smoke",
                skill_install.returncode == 0
                and (skill_target / "SKILL.md").is_file()
                and (skill_target / "agents" / "openai.yaml").is_file(),
                skill_install.stdout.strip() or skill_install.stderr.strip(),
            )
        )
        output_path = temp_root / "nested" / "lesson.md"
        no_parent = run_command([sys.executable, "-m", "bunomi", "日本語を読む", "--output", str(output_path)])
        results.append(check("export-parent-guard", no_parent.returncode == 2 and not output_path.exists(), no_parent.stderr.strip()))
        create_parent = run_command(
            [sys.executable, "-m", "bunomi", "日本語を読む", "--output", str(output_path), "--create-parent"]
        )
        results.append(check("export-create-parent", create_parent.returncode == 0 and output_path.exists(), create_parent.stderr.strip()))
        no_overwrite = run_command([sys.executable, "-m", "bunomi", "日本語を読む", "--output", str(output_path)])
        results.append(check("export-overwrite-guard", no_overwrite.returncode == 2, no_overwrite.stderr.strip()))

    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Run Bunomi's production-readiness audit")
    parser.add_argument("--json", action="store_true", help="输出机器可读 JSON")
    args = parser.parse_args()
    results = run_audit()
    if args.json:
        print(json.dumps([{"name": n, "passed": p, "detail": d} for n, p, d in results], ensure_ascii=False, indent=2))
    else:
        for name, passed, detail in results:
            status = "PASS" if passed else "FAIL"
            print(f"[{status}] {name}: {detail}")
        passed_count = sum(passed for _, passed, _ in results)
        print(f"\n结果: {passed_count}/{len(results)} checks passed")
    return 0 if all(passed for _, passed, _ in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
