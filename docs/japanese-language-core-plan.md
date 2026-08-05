# japanese-language-core 统一核心方案

更新日期：2026-08-05

## 1. 背景与目标

Bunomi 与 Utayomi 需要共享两类日语能力：读音（注音）与翻译。当前状态：

- `japanese-reading-core`（独立仓库，v0.1.0）提供读音引擎，两个应用已通过 git pin 依赖；
- 翻译能力刚抽成技能 `japanese-translation`，源文件暂放在 Bunomi 仓库，边界不一致。

目标：把两个能力合并进一个统一核心仓库，翻译与读音地位对等，作为可独立开关的能力；
并预留后续能力（词典、语法、词汇管理）的扩展空间。

## 2. 命名与品牌

- 仓库/包名：`japanese-language-core`（GitHub 已改名为
  https://github.com/qweihu/japanese-language-core，包名 `japanese_language_core`）；
- 品牌名：**Nihongo Core（日本語コア）**，用于 README 标题、UI 展示名、文档封面；
- 搜索视角：包名保留 `japanese` token（跨语言学习者与开发者在 PyPI/GitHub 的通用搜索词），
  品牌用 `nihongo`（日语圈内有辨识度，短）；
- 技能名 `japanese-translation`、`bunomi`、`utayomi` 不变。

## 3. 能力进入核心的判断标准

只有同时满足以下四条，能力才放进 core：

1. **确定性、可测试、可版本化**：不依赖 LLM 拍脑袋（纯 LLM 能力留在 Agent 层）；
2. **至少两个消费方复用**：Bunomi / Utayomi / 未来应用；
3. **不绑定产品层**：不碰歌词清洗、UI、账号、云服务；
4. **接口小、契约稳定**：像 `ReadingToken` 一样可以被审计和版本化。

## 4. 能力地图

### Phase 1：随本次迁移落地

优先级说明：**reading 与 translation 同为第一优先级，随迁移一并落地**，不设先后；
translation 的契约、语言参考与校验脚本已实现，迁移时直接编入
`japanese_language_core.translation`。

| 能力 | 核心层内容 | 现状 |
| --- | --- | --- |
| reading | 分词 + 上下文读音 + 假名归一 | 已有，迁入 `japanese_language_core.reading` |
| translation | 逐句契约 + 结构校验 + 语言注册表 | 新写，`japanese_language_core.translation` |
| kana/romaji 工具 | 假名↔罗马音、全半角归一 | 扩展 `to_hiragana` |
| 结构契约 | ruby / 行 / 占位符通用校验 | 从翻译校验中抽象 |

### Phase 2：短期值得做

| 能力 | 核心层内容 | 借鉴来源 |
| --- | --- | --- |
| 词典与词汇接口 | 词条查询、活用归一（辞書形）、JLPT/常用度标签 | Yomitan 词典模型、Bunomi Yomitan 集成 |
| 助词与语法标注 | 助词、常见语法型（〜ている 等）模式识别 | Yomitan tag/PoS 体系、JMDict PoS |
| 术语与词汇管理 | 翻译术语一致性检查（glossary） | 翻译契约扩展 |
| 词形变化 | 辞書形 ↔ て形/ない形/た形 归一 | Yomitan deinflector 思想 |

### Phase 3：可选

- JLPT 难度分析与生词提取；
- 导出契约（Anki 卡片、JSON/Markdown 规范）；
- 通用文本归一化（全半角、HTML 实体、空白）；
- 声调（pitch accent）数据契约。

### 明确不进 core

- 实际翻译（LLM 层）；
- 歌词抓取/清洗、站点流程（Utayomi 产品层）；
- TTS 音频、视觉渲染、UI、用户数据与云服务。

## 5. 接口与数据模型

### 已稳定（reading）

```python
from japanese_language_core.reading import ReadingToken, create_engine
```

`ReadingToken(orig, hira, hepburn)` 与 `ReadingEngine.tokens(text)` 契约保持不变，
通过兼容垫片 `japanese_reading_core` 在过渡期继续可用。

### 新增（translation）

```python
from japanese_language_core.translation import (
    TranslationUnit,       # 源行、翻译行、元数据
    TranslationResult,     # 语言对、行列表、警告/错误
    LanguageRegistry,      # 语言代码 → 约定文件、校验策略
    validate_translation,  # 行数配对、ruby 保真、HTML 卫生、假名漏译
)
```

CLI：`python -m japanese_language_core.translation validate --source … --translation … --paired`

### 翻译执行模式（translation 的接入方式）

翻译本身由大模型执行；core **不内置、不捆绑任何模型或密钥**，只保证契约与校验。
两种消费模式：

1. **Agent 模式（默认）**：技能 `japanese-translation` 指导 Codex 等 Agent 直接完成
   翻译，Agent 即翻译执行者；core 提供契约、语言约定与校验，不需要任何 API 配置。
2. **自带模型模式（BYO-LLM）**：开发者/用户自带兼容 OpenAI Chat Completions 的端点
   （base URL + model + api key），core 提供 `Translator` 协议与客户端实现，把语言
   约定注入 prompt，翻译后走同一套 `validate_translation` 校验。

```python
class Translator(Protocol):
    def translate(self, units, source_lang, target_lang, conventions) -> TranslationResult: ...

# Agent 模式：Agent 是执行者，该类作为契约占位，不发起网络调用
class AgentTranslator: ...

# BYO-LLM 模式：通过 base_url/model/api_key 配置（环境变量或构造参数）
class OpenAICompatibleTranslator: ...
```

设计约束：

- core 不内置默认供应商、不打包任何密钥；配置只来自用户（构造参数/环境变量）；
- 语言约定（references/zh-CN.md 等）同时供 Agent（Markdown 参考）与机器客户端
  （prompt 模板）使用，需要时可提供机器可读副本；
- 无论翻译由谁执行，输出都经过同一套校验，保证契约一致。

### 未来（Phase 2 预留方向）

`DictionaryLookup`、`Deinflector`、`FrequencyTag`、`PitchAccent` 等接口
以同样的"小接口 + 契约测试"方式加入，不预设占位模块。

## 6. 借鉴 Yomitan（详见研究结论）

核心借鉴点：词典数据模型（term/kanji/tag/meta bank）、活用形还原思想、
读音-汉字对齐（furigana distribution）、频率/常用度元数据、声调数据、
Anki 导出契约、离线优先与词典可选插件哲学。

许可注意：Yomitan 本体为 AGPL-3.0，借鉴**格式与算法思想**可以；
直接移植其代码进 MIT 核心前必须做许可评估。格式（JSON schema、数据模型）作为事实标准可对齐。

## 7. 迁移计划

1. 本地目录 `japanese-reading-core` → `japanese-language-core`，git remote 指向新 URL；
2. 包结构改为 `japanese_language_core.reading` / `.translation`；
3. `pyproject.toml`：包名改为 `japanese-language-core`，optional-dependencies：
   `reading`（Sudachi/Fugashi/PyKakasi）、`translation`（纯标准库）、`all`；
   `__init__.py` 不 import 重模块，按需导入；
4. 保留 `japanese_reading_core` 兼容垫片（re-export），过渡期后移除；
5. 更新 README（Nihongo Core 品牌、去掉 "not a translation system"、双语/三语）、
   LICENSE、契约测试、发布 tag（v0.2.0 或按新包名 v0.1.0）；
6. 技能源 `skills/japanese-translation` 迁入本仓库；
7. 更新消费方：Bunomi `pyproject.toml`、Utayomi `requirements.txt`、
   Bunomi 文档与安装脚本、Utayomi README；
8. 更新 Bunomi `.venv` 的 editable 安装指向，跑全量测试；
9. 本方案文档迁入新仓库 `docs/`。

## 8. 待决策项

- Phase 2 能力优先级（词典接口 vs 助词语法 vs 术语管理）；
- BYO-LLM 客户端是否随 Phase 1 一起实现，还是先只定义 `Translator` 协议；
- 兼容垫片保留时长；
- 新包是否发布到 PyPI（目前以 GitHub tag 依赖为主）。
