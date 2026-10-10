# Bunomi

**[English](README.md) | [简体中文](README.zh-CN.md) | [日本語](README.ja.md)**

An **Agent-facing Japanese furigana skill**: it decides whether input looks
like Japanese, adds validated `<ruby>` hiragana/romaji readings to kanji, and
verifies the result before export. The repository itself is the skill (root
`SKILL.md`); the CLI is the deterministic engine behind it.

## What it is

- **Skill layer**: root `SKILL.md` / `PROMPT.md` for Codex, Claude and other
  agents; `package.json` is the skill metadata.
- **Engine layer**: local CLI (`bunomi`) + Python package for deterministic
  readings (Sudachi through the shared core), ruby rendering and safe export.
  The optional PyKakasi comparison engine is installed separately because its
  GPL-3.0 dependency chain is not part of Bunomi's normal runtime.
- **Boundary**: lyric acquisition, translation and layout belong to dedicated
  lyric skills and the shared `$japanese-translation` skill; Bunomi only
  annotates.

<p align="center">
  <img src="screenshot/en/hiragana.png" alt="Hiragana furigana" width="720">
  <br><sub>Hiragana furigana: contextual readings (降り止む → ふりやむ) with okurigana outside ruby</sub>
</p>

## For agents

Install into the Codex default skill directory (add `--force` when the skill
already exists):

```bash
.venv/bin/python scripts/install_bunomi_skill.py
```

Agents reference `$bunomi` and follow the `SKILL.md` workflow; environments
without a skill framework can use `PROMPT.md` directly.

<p align="center">
  <img src="screenshot/en/flow.png" alt="Workflow" width="720">
  <br><sub>Workflow: input → detection → annotation → validation → output/export</sub>
</p>

## For developers (CLI)

The CLI provides deterministic furigana for ordinary Japanese text.

    echo "日本語を読む" | .venv/bin/bunomi
    .venv/bin/bunomi "日本語を読む" --romaji
    .venv/bin/bunomi "日本語を読む" --format html
    .venv/bin/bunomi --file lesson.txt

Text and stdin print Ruby content to stdout. File input writes a timestamped
sibling file and defaults to HTML; it never overwrites the source. Use
--format markdown or --format html to choose a format. Detection is a
conservative script heuristic: text without kana, or with fewer than one kana
per four Han characters, is rejected as ambiguous. It cannot distinguish
Chinese from Japanese Han spans or split such mixed passages automatically.
If the user explicitly confirms that Han-only text is Japanese, pass
`--assume-japanese` and preserve its warning. Translation, lyric search, and
lyric-specific layout belong to other skills.

## Translation

Bunomi only annotates ordinary Japanese text. Translation is a separate
workflow provided by the shared $japanese-translation skill from
[japanese-language-core](https://github.com/qweihu/japanese-language-core).
It is not part of Bunomi output.

## Development install

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

Installation pulls `japanese-language-core` pinned at `v0.4.0` with its
`[reading]` extra, so the reading engines are installed with Bunomi. For local
development of both repositories:

```bash
git clone https://github.com/qweihu/japanese-language-core.git ../japanese-language-core
.venv/bin/python -m pip install -e "../japanese-language-core[reading]"
.venv/bin/python -m pip install -e . --no-deps
```

## Testing

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
.venv/bin/python scripts/production_audit.py
```

The production audit additionally checks skill structure, golden readings,
CLI formats, Japanese detection and export safety; golden cases live in
`tests/fixtures/golden_cases.json`. See
[docs/production-audit.md](docs/production-audit.md) for the latest results.

## Project structure

    SKILL.md       Agent instructions for ordinary Japanese annotation
    PROMPT.md      Standalone prompt for agents without Skill support
    src/bunomi/    Detection, shared reading adapter, ruby rendering, validation and CLI
    scripts/       Skill installer
    tests/         Unit tests and production audit

## Shared language core

Bunomi reuses the reading API from
[japanese-language-core](https://github.com/qweihu/japanese-language-core).
The shared core owns Japanese reading and general language contracts; Bunomi
owns ordinary-text detection, ruby presentation, and its Agent workflow.

MIT License
