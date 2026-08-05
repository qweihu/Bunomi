# Bunomi

Bunomi 是面向日语初学者的本地振假名工具：判断输入是否像日语，为日语汉字添加 `<ruby>` 平假名读音，并在导出前校验结果。

## 开发安装

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .
```

安装过程会从公开的 [japanese-language-core](https://github.com/qweihu/japanese-language-core)
仓库获取固定的 `v0.2.0` 共享核心（读取能力需要 `[reading]` 扩展）。两个仓库本地联调时，也可以使用：

```bash
.venv/bin/python -m pip install -e "/Users/qwei/Coding/japanese-language-core[reading]"
.venv/bin/python -m pip install -e . --no-deps
```

## CLI 示例

```bash
echo "夢ならばどれほどよかったでしょう" | .venv/bin/bunomi
.venv/bin/bunomi --file lesson.txt --format html
.venv/bin/bunomi "日本語を読む" --output ./exports/lesson.md --create-parent
.venv/bin/bunomi "雨が降り止むまでは帰れない" --engine sudachi
```

默认只输出到终端。导出必须使用明确的 `--output`，已有文件必须显式加 `--overwrite`。

默认 `--engine auto` 优先使用 Sudachi 上下文引擎；`--engine pykakasi` 可用于兼容回退。经过审核的短语规则默认启用，可用 `--no-overrides` 做诊断对比。

```text
处理完成！已保存：/absolute/path/lesson.md
```

## 测试

```bash
PYTHONPATH=src python3 -m unittest discover -s tests -v
.venv/bin/python scripts/production_audit.py
```

将项目 Skill 安装到 Codex 默认目录（已有安装需显式加 `--force`）：

```bash
.venv/bin/python scripts/install_bunomi_skill.py
```

共享翻译技能从 [japanese-language-core](https://github.com/qweihu/japanese-language-core)
仓库安装：

```bash
git clone https://github.com/qweihu/japanese-language-core.git
python3 scripts/install_skill.py --force
```

生产审计会额外运行 Skill 结构校验、真实注音标准答案、CLI 格式、日语检测和导出安全测试；标准答案位于 `tests/fixtures/golden_cases.json`。
当前审计结论见 [docs/production-audit.md](docs/production-audit.md)。

## 项目结构

```text
docs/requirements.md       # MVP 需求与验收标准
docs/reference-utayomi.md  # 本地 Utayomi 参考记录
docs/shared-translation-capability.md # 共享翻译能力边界
docs/yomitan-data-plan.md  # Yomitan 词典来源、版本和审计接入方案
src/bunomi/core.py         # 检测、引擎适配、ruby 渲染、校验
src/bunomi/engine.py       # 共享核心读取能力的入口（japanese_language_core.reading）
src/bunomi/cli.py          # CLI 与安全导出
skills/bunomi/SKILL.md     # 给 Agent 使用的项目内 skill
scripts/fetch_yomitan_data.py # 获取并登记 Yomitan 词典快照
scripts/audit_yomitan_data.py  # 校验快照完整性和基本索引样本
scripts/audit_reading_disagreements.py # 输出主引擎与词典候选的差异
scripts/install_bunomi_skill.py # 可重复安装 Bunomi Skill
tests/test_core.py         # 无外部服务的核心测试
```

详细边界见 [docs/requirements.md](docs/requirements.md)。

## Yomitan 词典快照

Bunomi 将 Yomitan/JMdict 数据作为词典增强和审计来源，Sudachi 仍负责默认的上下文读音。需要获取数据时运行：

```bash
.venv/bin/python scripts/fetch_yomitan_data.py --extract
.venv/bin/python scripts/audit_yomitan_data.py
.venv/bin/python scripts/audit_reading_disagreements.py
```

共享引擎的源码、测试和 distribution 元数据现在位于独立仓库：

```bash
python3 -m pip wheel --no-deps /Users/qwei/Coding/japanese-language-core -w dist/shared-engine
```

数据保存在被忽略的 `var/yomitan/`，版本、来源和 SHA-256 位于 `manifest.json`。完整方案见 [docs/yomitan-data-plan.md](docs/yomitan-data-plan.md)。

Bunomi 与 Utayomi 的共享边界见 [docs/shared-reading-engine.md](docs/shared-reading-engine.md)
与 [docs/shared-translation-capability.md](docs/shared-translation-capability.md)。
