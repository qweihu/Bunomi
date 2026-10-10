# Bunomi

**普通日语文本的注音 Skill**

Bunomi 适合处理日语句子、文章、教材、聊天内容等普通文本。它会给汉字加上平假名，默认生成 HTML；Bunomi 流程只负责注音。

## 你可以怎么用

直接告诉 Agent：

```text
请给这段日语加平假名：
日本語を読む
```

默认结果是 HTML。你也可以继续说：

- “改成罗马音”；
- “导出 Markdown”。


## 它处理什么

- 普通日语文本的平假名注音；
- 用户明确要求时的罗马音；
- 日语检测和注音结果校验；
- 默认 HTML，按需 Markdown；
- 保留原文、换行、标点和非日语内容。

它不负责抓取歌词、清洗歌词网页、制作课程或生成学习卡片。

## 命令行用法

```bash
# 直接输入文本：输出带 Ruby 的内容
echo "日本語を読む" | .venv/bin/bunomi

# 生成 HTML
.venv/bin/bunomi "日本語を読む" --format html

# 生成罗马音
.venv/bin/bunomi "日本語を読む" --romaji

# 处理文件：在原文件同目录生成带时间戳的新 HTML
.venv/bin/bunomi --file lesson.txt
```

直接输入时结果输出到终端；处理文件时不会覆盖原文件，例如：

```text
lesson.YYYYMMDD-HHMMSS.html
```

命令行只保留日常使用需要的选项，不需要选择引擎、词典、例句、活用或输出路径。

日语判断是保守的文字脚本启发式：不含假名，或假名少于汉字数四分之一的文本，
会被判为信号不足。它无法区分中日共用汉字的具体语种，也不会自动切分中日混合段落；
遇到这类文本时，请先提供明确的日语部分。用户明确确认纯汉字文本是日语后，才可使用
`--assume-japanese`，并保留命令的警告。

## 安装

需要 Python 3.10+。

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -e .

# 安装为 Agent Skill
.venv/bin/python scripts/install_bunomi_skill.py
```

Bunomi 安装时会自动安装固定在 `v0.4.0` 的共享核心及其 `[reading]` 读音依赖。
共享核心由 [japanese-language-core](https://github.com/qweihu/japanese-language-core) 提供。
PyKakasi 仅作可选对照引擎，不在 Bunomi 默认安装中；它的 GPL-3.0 依赖链需要单独安装。

## 和共享核心的关系

Bunomi 是面向 Agent 的应用层 Skill，负责“普通文本注音”这件事。

共享核心是独立的通用库，保留词典、例句、活用和翻译校验等能力，供其他应用按需使用。Bunomi 的用户流程只使用日语读音能力。

## 开发与测试

```bash
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/production_audit.py
```

当前测试和生产审计会检查注音、Ruby 完整性、原文保留、文件时间戳输出和 Skill 结构。

## 项目结构

```text
SKILL.md                 # Agent 使用的 Skill 说明
PROMPT.md                # 没有 Skill 框架时使用的提示词
src/bunomi/cli.py        # 简化后的命令行入口
src/bunomi/core.py       # 日语检测、注音和校验
scripts/install_bunomi_skill.py # 安装 Skill
tests/                   # 本地回归测试
```

MIT License
