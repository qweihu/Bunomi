---
name: bunomi
description: 为普通日语学习文本中的汉字生成可校验的平假名或罗马音振假名，并支持 Markdown、HTML、JSON 输出和用户确认后的安全导出。Use when a user asks to read Japanese kanji, add furigana, annotate ordinary Japanese text, or integrate Japanese ruby output into an Agent conversation. Defer translation to the shared japanese-translation skill; defer lyric retrieval and lyric-specific layout workflows to dedicated lyric skills.
---

# Bunomi

Use Bunomi for ordinary Japanese learning text. Keep lyric retrieval, lyric translation, and song-specific Markdown layout in dedicated lyric skills so the skills do not compete for the same request.

## 翻译请求

用户要求给注音结果添加翻译时，使用共享技能 `$japanese-translation`：它提供逐句翻译契约、
目标语言约定（默认简体中文，可扩展）和结构校验脚本。Bunomi 负责注音与校验，翻译由该共享
能力完成，排版由用户偏好和调用方决定；不要在本技能内另建一套翻译规范。

## Core workflow

Use the repository CLI as the deterministic reading engine. Do not guess Japanese readings in the Agent when the CLI is available.

1. Preserve the user's text, line breaks, punctuation, and non-Japanese fragments.
2. Use hiragana by default. Use `--romaji` only when the user explicitly requests romaji.
3. Keep `--engine auto` unless the user asks for a specific backend; automatic mode prefers Sudachi context readings and falls back to PyKakasi when unavailable.
4. Keep audited phrase overrides enabled. Use `--no-overrides` only for debugging and disclose that it may reduce reading accuracy.
5. From the Bunomi project root, prefer `.venv/bin/python -m bunomi` when that interpreter exists; use `PYTHONPATH=src python3 -m bunomi` only as a fallback. Pipe text to the CLI or use `--file`; inspect its exit status and validation errors.
6. Present the Markdown result directly in the conversation unless the user requests a file.
7. Export only to a path the user supplied or explicitly confirmed. Pass `--output`; do not invent a random directory or filename.

The project may use Yomitan/JMdict release data as a local dictionary-enrichment
layer. Treat it as evidence and metadata, not as a replacement for Sudachi
context segmentation. When dictionary metadata is available, preserve its
source and release tag in JSON and report disagreements instead of silently
changing the reading. Do not fetch URLs, upload user text, or bundle third-party
dictionary archives unless the user explicitly requests that workflow.

The reusable engine is published from the separate
`qweihu/japanese-reading-core` repository; install that package when another
application needs the same reading contract. Keep Bunomi's
detection, ruby rendering, and export policy in the application layer.

## CLI

From the project root, use:

```bash
.venv/bin/python -m bunomi "日本語を読む"
cat input.txt | .venv/bin/python -m bunomi
.venv/bin/python -m bunomi --file input.txt --romaji
.venv/bin/python -m bunomi "雨が降り止むまでは帰れない" --engine sudachi
.venv/bin/python -m bunomi --dictionary-dir var/yomitan/extracted --format json "山田太郎は東京へ行く。"
```

If `.venv/bin/python` is unavailable, replace it with
`PYTHONPATH=src python3` after confirming that the active Python environment
has the dependencies from `requirements.txt`.

Use `--format markdown` for chat-ready output, `--format html` for a minimal browser document, and `--format json` for structured Agent integration.
Use `--dictionary-dir` only when a local Yomitan cache exists and JSON audit metadata is needed; it does not change the default Markdown reading.

## Safety and failure handling

- Treat `ambiguous` input (CJK without kana or Japanese punctuation) as untrusted; ask the user to confirm it is Japanese or use `--force` only when context makes that certain.
- Treat `mixed` input as valid but tell the user that non-Japanese text was preserved.
- Do not use `--force` silently.
- Do not write a file without `--output`.
- Do not use `--overwrite` unless the user explicitly asks to replace the existing file.
- Do not use `--create-parent` unless the user has confirmed that creating the directory is acceptable.
- If the preferred interpreter reports missing dependencies, check for the project `.venv` before installing anything. If no usable environment exists, tell the user to install `requirements.txt`; do not substitute model-guessed readings.

## Output contract

The default format is plain Markdown containing HTML ruby elements such as:

```text
<ruby>日本語<rt>にほんご</rt></ruby>を読む
```

The CLI validates that ruby tags are balanced, the source text is preserved, and no kanji remains outside a ruby element. JSON output reports the selected engine, audited override IDs, and—when `--dictionary-dir` is supplied—Yomitan source titles, indexed term/KANJIDIC counts, candidate readings, candidate tags, single-kanji information, and explicit reading agreement/status. Translation is provided by the shared `$japanese-translation` skill; URL scraping, lyrics cleanup, and visual styling remain separate Agent capabilities and are not part of the core annotation command.

Yomitan data acquisition is a separate reproducible operation:

```bash
.venv/bin/python scripts/fetch_yomitan_data.py --extract
```

It writes third-party archives and a versioned manifest under `var/yomitan/`;
do not treat that cache as part of the Skill runtime or commit it to the
repository. See `docs/yomitan-data-plan.md` before adding a new dictionary
source.
