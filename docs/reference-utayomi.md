# Utayomi 参考记录

参考目录：`/Users/qwei/Coding/utayomi/`

## 可复用部分

- `scripts/utayomi_core.py` 使用 `fugashi.Tagger()`、`unidic-lite` 和 `pykakasi`。
- 通过词法分词减少大模型直接猜读音的风险。
- 使用 `<ruby>原文<rt>读音</rt></ruby>`，可以被 Markdown 渲染器和浏览器直接展示。
- `--romaji` 是清晰易用的 CLI 参数。
- `SKILL.md` 把本地确定性脚本和 Agent 翻译/排版能力组合起来。

## Bunomi 的调整

- Utayomi 的 legacy 路径曾在平假名模式下把含送假名的完整片段包进 ruby，例如把 `踏み込む` 作为一个表面片段处理；现在 legacy 和共享路径都复用 kana-run 对齐，优先把送假名留在 ruby 外。
- Utayomi 现在通过 `scripts/save_markdown.py` 要求用户确认完整绝对路径，并显式控制父目录创建和覆盖；Bunomi 继续使用显式 `--output` 策略。
- Utayomi 的输入检测只判断是否出现日文字符；Bunomi 对“只有汉字”的中日文歧义单独分类，避免误处理中文。
- Utayomi 的核心脚本直接打印结果；Bunomi 增加可编程结果对象和 JSON 输出，便于 Agent 集成及校验。
- Bunomi 优先把连续的日文片段交给 PyKakasi，以保留 `日本語 -> にほんご` 这类复合词上下文；只有转换无法保真时，才退回 Fugashi 分词后的逐词转换。
- Bunomi 现已将 SudachiPy + sudachidict-core 作为自动模式的首选上下文引擎，PyKakasi 路径仍保留为显式回退；特殊短语通过 `src/bunomi/data/reading_overrides.json` 审核和记录。

## 参考边界

Utayomi 还包含歌词翻译、网页歌词清洗和特定站点流程。这些能力不放入 Bunomi 的注音核心，后续可作为独立 Agent 工作流添加。

## 交叉验证记录

在相同输入 `雨が降り止むまでは帰れない` 上运行两个项目：

- Bunomi（Sudachi + 审核规则）：`降 → ふ`、`止 → や`。
- Utayomi legacy 基线（Fugashi + PyKakasi）：`降り → おり`、`止む → とむ`；当前默认共享模式与 Bunomi 一致。

这确认了共享引擎的必要性：Bunomi 现在提供可随 wheel 安装的 `japanese_reading_core` 包，`bunomi.engine` 只是兼容入口。Utayomi 本地注音核心现已增加 `--engine auto/shared/legacy`：默认优先共享引擎，回退会明确报警，旧版实现保留为显式兼容模式；歌词清洗、翻译、排版和用户确认路径保存流程没有被合并。跨项目契约测试已覆盖 `降り止む`、重复送假名、legacy 转义和 auto 优先级。
