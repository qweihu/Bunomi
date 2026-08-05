# Bunomi / Utayomi 共享翻译能力边界

更新日期：2026-08-05

## 当前结论

翻译能力已并入统一核心 `japanese-language-core`（Nihongo Core），不再单独维护：

- `japanese_language_core.translation`：逐句契约、结构校验、语言注册表、术语一致性；
- 技能 `japanese-translation`（源文件位于核心仓库 `skills/`）：Agent 工作流入口；
- 两种执行模式：Agent 模式（Agent 直接翻译，无需 API）与 BYO-LLM 模式
  （用户自带 OpenAI 兼容端点 base URL + model）。

core 不内置供应商、不打包密钥；无论谁执行翻译，输出都经过同一套
`validate_translation` 校验。

## 翻译核心包含

- `contract.py`：`TranslationUnit`、`TranslationResult`、`LanguageRegistry`；
- `validate.py`：行数配对、ruby 保真、HTML 卫生、占位符保留、假名漏译警告；
- `glossary.py`：术语一致性检查；
- `prompt.py` + `provider.py`：BYO-LLM prompt 构建与 OpenAI 兼容客户端；
- `data/languages.json`：机器可读语言注册表（zh-CN 默认、en 示例）；
- 技能 `references/`：Agent 使用的逐语言 Markdown 约定。

## 多语言扩展

按技能 `references/languages.md` 注册语言并新建约定文件，同时更新包内
`languages.json` 的机器可读副本；默认目标语言为简体中文。

## 边界与禁止

- 不抓取外部翻译；BYO-LLM 只调用用户显式配置的端点；
- 翻译能力不代替 Bunomi 注音；不处理 Utayomi 的歌词清洗、标题识别和排版；
- 不把翻译逻辑混入注音 CLI。
