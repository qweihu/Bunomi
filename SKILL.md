---
name: bunomi
description: Use when the user provides ordinary Japanese text and wants furigana or kana readings. Default output is a self-contained HTML result with hiragana readings. Do not translate within Bunomi; do not use for lyrics or lyric-specific cleanup and layout; use Utayomi for that.
---

# Bunomi

Use Bunomi for ordinary Japanese text supplied by the user. It is a focused
annotation skill, not a lesson generator and not a lyric workflow.

## Default behavior

- Add validated hiragana furigana.
- Return a self-contained HTML result by default.
- Preserve source text, line breaks, punctuation, non-Japanese fragments and
  meaningful blank-line groups.
- Detection is a conservative script heuristic: text without kana, or with
  fewer than one kana per four Han characters, is rejected as ambiguous.
- It cannot distinguish Chinese from Japanese Han spans or split such mixed
  passages automatically. Ask for the Japanese portion when the language is
  unclear; do not claim the tool segmented it.
- If the user explicitly confirms that an ambiguous Han-only passage is
  Japanese, use `--assume-japanese` and report the CLI warning with the result.
- Validate Ruby balance, source preservation and reading coverage before
  returning the result.

Do not ask the user to choose an engine, dictionary, intermediate format or
output path. The local deterministic engine and shared translation contract
are implementation details.

## Explicit options

Honor these only when the user asks for them:

- **Romaji**: render readings in Hepburn romaji instead of hiragana.
- **Markdown**: export the same result as Markdown instead of HTML.

After returning HTML, briefly tell the user that Markdown or romaji can be requested if needed.

## Boundaries

- Use only text supplied by the user; do not fetch URLs or lyrics.
- If the input is clearly lyrics or asks for lyric-specific cleaning/layout,
  use `$utayomi` instead.
- If the reading engine cannot validate the input, report the error; do not
  guess readings in the Agent.
- Do not add translation to Bunomi output. If the user separately requests translation, hand that part to the shared `$japanese-translation` skill.

## Runtime

When a deterministic check is needed, run the Bunomi CLI from this project.
Direct text, positional text and stdin produce Ruby content on stdout. A file
input produces a new timestamped sibling result file; the CLI chooses HTML by
default for file input. Do not expose internal engine or path flags in the
normal Agent workflow.
