# Bunomi / Utayomi 共享语言核心边界

更新日期：2026-08-05

## 当前结论

读音与翻译能力统一收进独立仓库 `japanese-language-core`（品牌 Nihongo Core），
Bunomi 与 Utayomi 都不再各自维护共享能力实现：

- 读音：`japanese_language_core.reading`（分词 + 上下文读音 + 假名/罗马音 +
  furigana 对齐 + 活用形还原）。
- 翻译：`japanese_language_core.translation`（逐句契约、校验、语言注册表、
  术语一致性；Agent 模式或 BYO-LLM）。
- 词典/语法/导出：`dictionary`、`grammar`、`export` 作为同一核心的其他能力。

两个应用仍分别保留自己的产品层：Bunomi 负责注音校验与导出，Utayomi 负责
歌词清洗、标题识别与中日对照排版。

## 读音契约（不变）

`ReadingToken` 与 `ReadingEngine.tokens(text)` 契约保持不变：

```python
from japanese_language_core.reading import ReadingToken, create_engine

engine = create_engine("auto")
tokens = tuple(engine.tokens("雨が降り止む"))
assert "".join(token.orig for token in tokens) == "雨が降り止む"
```

读音优先级不变：Sudachi 上下文读音优先，PyKakasi 回退；Yomitan/JMdict 只提供
候选与审计证据；审核过的短语规则可覆盖基础结果。消费方直接使用
`japanese_language_core.reading` 命名空间，不保留旧包名。

## 安装

```bash
python3 -m pip install "japanese-language-core[reading] @ git+https://github.com/qweihu/japanese-language-core.git@v0.2.0"
```

`[translation]` 仅需标准库；两个应用各自在 `pyproject.toml` / `requirements.txt`
固定版本依赖。

## 独立发行

独立仓库包含 `src/japanese_language_core/`、测试、`pyproject.toml` 与 MIT 许可证；
Bunomi 与 Utayomi 通过固定版本 tag 依赖它，不再复制引擎源码。发行时保留：

- `ReadingToken` 和 `ReadingEngine` 协议；
- Sudachi/PyKakasi 适配器及依赖版本锁定；
- 原文保真和读音字段的契约测试；
- translation 的逐句契约与校验测试；
