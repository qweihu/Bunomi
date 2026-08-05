# Bunomi Codex Skill 触发测试清单

这份清单用于在实际 Codex 新会话中验证 Skill 是否被发现、显式调用和自然语言触发。测试使用隔离的
`codex exec --ephemeral --skip-git-repo-check -s read-only --json` 会话，结果记录在文档末尾。

## 前置条件

1. 已运行 `.venv/bin/python scripts/install_bunomi_skill.py`（Bunomi）和
   `japanese-language-core` 仓库的 `scripts/install_skill.py`（共享翻译技能），
   当前安装位置为 `/Users/qwei/.codex/skills/bunomi` 与 `/Users/qwei/.codex/skills/japanese-translation`；
   如果源文件有更新，使用 `--force` 重新安装。也可以传入 `--destination` 使用其他技能目录。
2. 重启 Codex 或新建会话，确保不是复用旧会话缓存；自动化回归可使用上面的 ephemeral 会话命令。
3. 确认 Bunomi 依赖安装完成，并能运行：

```bash
.venv/bin/bunomi "日本語を読む"
```

## 正向用例

| 用例 | 用户提示 | 期望 |
| --- | --- | --- |
| 显式调用 | `$bunomi 请给这段日语汉字标注平假名：日本語を読む` | 触发 Bunomi，直接呈现 ruby Markdown |
| 普通学习文本 | `请帮我读一下这段日语，给汉字加振假名：今日は生ビールを飲む。` | 触发 Bunomi，使用 Sudachi/审核规则 |
| 罗马音 | `用罗马音标注：君の名は。` | 触发 Bunomi 的 `--romaji` 流程 |
| 导出 | `把这段日语导出到我确认的 lesson.md` | 先确认完整路径，再使用 `--output` |
| 翻译学习文本 | `给这段日语加注音，并翻译成中文：明日は晴れる。` | 触发 Bunomi 注音，翻译交给 `$japanese-translation` |

## 负向和边界用例

| 用例 | 用户提示 | 期望 |
| --- | --- | --- |
| 歌词工作流 | `抓取这首歌，翻译歌词并按中日对照排版` | 交给歌词专用流程 |
| 中文文本 | `请给这段中文加日语读音：这是中文` | 不触发或明确拒绝误判 |
| 纯汉字歧义 | `日本語` | 触发后要求确认日语语境或使用 force |
| 非注音任务 | `帮我写一个 Python Web 服务` | 不触发 Bunomi |

## 记录项

- 实际触发的 Skill 名称。
- 是否调用了本地 `bunomi` CLI。
- 是否选择了 `sudachi`。
- 是否保留原文和换行。
- 是否在未确认路径时避免写文件。
- 歌词专用流程是否与 Bunomi 出现错误竞争。

只有正向、负向和冲突用例都符合预期，才能把“Codex Skill 触发测试”标记为通过。

## 2026-08-04 实际新会话记录

| 场景 | 结果 | 观察到的证据 |
| --- | --- | --- |
| Bunomi 自然语言正向 | 通过 | 新会话加载 `bunomi`，调用项目 `.venv/bin/python -m bunomi`，输出 `<ruby>今日<rt>きょう</rt></ruby>は...` |
| Bunomi 显式 `$bunomi` | 通过 | 新会话加载 `bunomi`，调用 `--format markdown`，`日本語を読む` 输出 `<ruby>日本語<rt>にほんご</rt></ruby>を<ruby>読<rt>よ</rt></ruby>む。` |
| 非注音任务 | 通过 | Python Web 服务请求未加载 Bunomi，也未调用注音 CLI |
| 歌词边界 | 通过 | 新会话加载歌词专用技能；明确要求共享引擎时返回 `<ruby>夢<rt>ゆめ</rt></ruby>...` |

显式 Bunomi 测试的线程 ID 为 `019fccff-5203-70d2-8b55-8a73fcc66bd0`；严格共享引擎回归的线程 ID 为
`019fcd05-7443-79a0-92c8-c1a1b5ba7a16`。测试过程中发现的系统 `python/python3` 依赖问题已修复：Bunomi
Skill 现在优先使用项目 `.venv/bin/python`，歌词专用技能明确要求发现可用虚拟环境并使用
`PYTHONPATH=/path/to/japanese-language-core/src ... --engine shared`，或直接使用已安装的
`japanese-language-core` 包。修复后重新安装了两个本地 Skill，并完成上述回归。
