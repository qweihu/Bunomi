# Bunomi 生产级审计记录

审计日期：2026-08-04

## 结论

当前本地工程审计已通过。需要注意：这仍然不是 OpenAI 官方认证；它表示项目级质量门槛和本地 Codex
Skill 触发矩阵已经通过。

## 已执行项目

| 检查项 | 结果 | 证据 |
| --- | --- | --- |
| Skill 结构校验 | 通过 | `quick_validate.py` 输出 `Skill is valid!` |
| 单元测试 | 通过 | 15/15 tests passed |
| CLI 格式 | 通过 | Markdown、HTML、JSON |
| 日语检测 | 通过 | 日语、混合、中文/英文拒绝 |
| 导出安全 | 通过 | 目录确认、创建父目录、覆盖保护 |
| 全新环境安装 | 通过 | 临时 Python 3.13 环境安装 Sudachi 依赖并运行成功 |
| 标准答案语料 | 通过 | 人名、地名、多音字、活用和歌词式样本均通过 |
| Utayomi 交叉验证 | 已完成 | 同一复合词上确认 Bunomi 与旧 Utayomi 输出差异 |
| Yomitan 数据快照 | 已完成 | release `2026-08-04`，4 个资产，manifest 含 SHA-256 |
| Yomitan term/kanji-bank 索引 | 已完成 | 可选 `--dictionary-dir`，JSON 提供候选读音、标签和 KANJIDIC 单字信息 |
| Yomitan 快照完整性审计 | 已完成 | `scripts/audit_yomitan_data.py` 校验 SHA-256、format 3 和基本词条样本 |
| 主引擎/词典差异审计 | 已完成 | `scripts/audit_reading_disagreements.py` 输出候选读音、标签和 release 来源 |
| 共享引擎 wheel/安装冒烟 | 已完成 | wheel 含 `japanese_reading_core`，临时安装后可用 Sudachi 保持原文和读音 |
| 独立 japanese-language-core wheel | 已完成 | 独立 distribution 构建成功，并在只安装该 wheel 的 Utayomi 临时环境中运行通过 |
| Utayomi 共享引擎契约 | 已完成 | 本地 Utayomi 19/19 tests passed；`auto/shared/legacy`、legacy 转义和安全保存边界已验证 |
| Skill 安装冒烟 | 已完成 | Bunomi 已安装到 `/Users/qwei/.codex/skills/bunomi` 并通过 quick_validate；Utayomi 也已同步共享引擎运行时说明 |
| Codex 新会话触发 | 通过 | Bunomi 自然语言、显式 `$bunomi`、非注音负向和 Utayomi 歌词边界均在隔离新会话中验证 |

生产审计脚本结果：`30/30 checks passed`。该脚本不要求被忽略的 Yomitan 缓存存在；本地缓存另由 `scripts/audit_yomitan_data.py` 校验，结果为 release `2026-08-04`、1,608,772 条 term 和 10,384 条 kanji。差异报告当前发现 1 条需人工复核的候选冲突：`愛し` 的古语候选 `はし`，没有自动写入覆盖规则。

## 已解决的准确性问题

`降り止む` 的 PyKakasi 基线曾输出错误读法。现在自动模式使用 Sudachi 上下文引擎，并保留 `context-furiyamu` 审核规则，输出为 `ふりやむ`；命中的规则 ID 会出现在 JSON 的 `overrides_applied` 中。

## 重跑方式

```bash
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python scripts/production_audit.py
.venv/bin/python scripts/production_audit.py --json
```

标准样本位于 `tests/fixtures/golden_cases.json`。修复读音引擎或增加经过审核的上下文规则后，重新运行审计；当前本地 blocking 样本均已通过。

## 尚未完成或持续推进的项目

1. 持续扩充人名、地名、多音字、歌词化表达和长文本语料，并按需增加词频、释义、音调等可选数据源。
2. 后续发布新版本时，继续对 `japanese-language-core` 的标签、依赖范围和两个应用的兼容矩阵做回归验证。
