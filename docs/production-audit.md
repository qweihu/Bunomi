# Bunomi 生产级审计记录

审计日期：2026-10-10 17:47:51 +08:00

## 结论

当前本地工程审计已通过：生产审计脚本 29/29 checks、单元测试 17/17。需要注意：这不是 OpenAI 官方认证，也不代表对所有日语文本的读音准确率承诺；它只表示项目级检查和本地可重复样例通过。

## 已执行项目

| 检查项 | 结果 | 证据 |
| --- | --- | --- |
| Skill 结构校验 | 通过 | `quick_validate.py` 输出 `Skill is valid!` |
| 单元测试 | 通过 | 17/17 tests passed |
| CLI 默认入口 | 通过 | 直接文本 Ruby 输出、HTML 输出、文件时间戳输出 |
| 日语检测 | 通过 | 有假名的日语、混合文本、中文/英文拒绝；纯汉字默认拒绝，显式确认后继续并警告 |
| 文件输出安全 | 通过 | 源文件同目录生成时间戳副本，不覆盖源文件 |
| 全新环境安装 | 通过 | 临时 Python 3.13 环境安装 Sudachi 依赖并运行成功 |
| 标准答案语料 | 通过 | 人名、地名、多音字、活用和歌词式样本均通过 |
| 共享引擎交叉验证 | 已完成 | 同一复合词上确认共享引擎与旧实现输出差异 |
| 共享引擎 wheel/安装冒烟 | 已完成 | wheel 含 `japanese_reading_core`，临时安装后可用 Sudachi 保持原文和读音 |
| 独立 japanese-language-core wheel | 已完成 | 独立 distribution 构建成功，并在只安装该 wheel 的临时环境中运行通过 |
| 共享引擎契约 | 已完成 | 应用层不再暴露引擎选择；核心读音和原文保留测试继续验证 |
| Skill 安装冒烟 | 已完成 | 安装到临时 Codex Skill 目录并通过 quick_validate |
| Codex 新会话触发 | 通过 | Bunomi 自然语言、显式 `$bunomi` 与负向用例均在隔离新会话中验证 |

生产审计脚本现在只检查 Skill 结构、核心读音、应用 CLI 和安全的时间戳文件输出；词典、例句和活用能力由 `japanese-language-core` 独立维护。当前金样例数量有限，仍需扩大人工复核覆盖；不得把 29/29 checks 解读为统计意义上的准确率。

## 已解决的准确性问题

`降り止む` 仍通过共享上下文引擎和审核规则处理，输出为 `ふりやむ`。应用层不再要求用户选择 Sudachi、PyKakasi 或其他引擎。

## 重跑方式

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/production_audit.py
.venv/bin/python scripts/production_audit.py --json
```

标准样本位于 `tests/fixtures/golden_cases.json`。修复读音引擎或增加经过审核的上下文规则后，重新运行审计；当前本地 blocking 样本均已通过。

## 尚未完成或持续推进的项目

1. 持续扩充人名、地名、多音字、歌词化表达和长文本语料，并按需增加词频、释义、音调等可选数据源。
2. 发布 Core `v0.4.0` 后，继续对版本标签、依赖范围和 Bunomi/Utayomi 的兼容矩阵做回归验证；标签发布前使用本地源码验证。
