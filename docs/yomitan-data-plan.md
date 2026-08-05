# Bunomi 的 Yomitan 数据接入方案

更新日期：2026-08-04

## 决策

Bunomi 先从 [yomidevs/jmdict-yomitan](https://github.com/yomidevs/jmdict-yomitan) 获取可复现的词典快照。这个仓库会自动发布适用于 Yomitan 的 JMdict、JMnedict 和 KANJIDIC 数据；Bunomi 使用这些数据做词语元数据、候选读音、人名补充和审计对照，不把 Yomitan 浏览器扩展本身当作运行时依赖。

Sudachi 仍然是默认的上下文分词和主读音引擎。词典读音与 Sudachi 不一致时，先记录差异并进入审计队列，不能静默覆盖。只有经过人工确认的短语才进入 `reading_overrides.json`。

## 第一批数据

| 资产 | 用途 | 状态 |
| --- | --- | --- |
| `JMdict_english_without_proper_names.zip` | 通用词条、读音、词性、释义、词形关系 | 默认获取 |
| `JMnedict.zip` | 人名、地名和其他专有名词 | 默认获取 |
| `KANJIDIC_english.zip` | 单汉字音读、训读、笔画和汉字信息 | 默认获取 |
| `JMdict_forms.zip` | 词形归一化和活用候选 | 默认获取 |
| `JMdict_english_with_examples.zip` | 例句和学习卡片 | 按需获取 |

词频、音调和真人音频不假设由上述快照提供。它们作为后续可插拔数据源单独管理，避免把“Yomitan 支持某类信息”误认为“JMdict release 已包含该信息”。

## 获取与版本管理

```bash
.venv/bin/python scripts/fetch_yomitan_data.py --list
.venv/bin/python scripts/fetch_yomitan_data.py --extract
.venv/bin/python scripts/fetch_yomitan_data.py \
  --asset JMdict_english_without_proper_names.zip \
  --asset JMnedict.zip \
  --asset KANJIDIC_english.zip
```

脚本通过 GitHub Releases API 解析最新 release，不猜测版本号；下载后写入 `var/yomitan/manifest.json`，记录 release tag、下载地址、字节数、获取时间和 SHA-256。原始归档和解压内容不进入 Python package，也不应提交到仓库。

网络不可用、资产名称变化或下载失败时，命令必须失败并保留已有缓存，不应使用未经登记的临时词典。

## 内部数据边界

### 读取引擎层

- Sudachi：决定文本如何切词以及当前语境下的基础读音。
- PyKakasi/Fugashi：兼容回退和罗马音支持。
- 审核覆盖规则：只处理已经复核的短语、人名或歌词表达。

### 词典增强层

将 Yomitan 词条归一化为内部记录：

```json
{
  "source": "jmdict-yomitan",
  "release_tag": "2026-07-31",
  "term": "降り止む",
  "reading": "ふりやむ",
  "forms": [],
  "definitions": [],
  "tags": [],
  "sequence": null
}
```

当前 JSON 已提供 `dictionary_matches`、候选标签、`kanji_info` 和 `reading_status`；`frequency` 已在 KANJIDIC 单字记录中提供。词频词典、`pitch_accent`、释义正文和例句仍作为可选数据源增量接入，Markdown 默认保持简洁，只输出振假名。

## 与之前任务的关系

这次接入不改变既有主线：

1. 保留日语检测，纯汉字输入仍然需要用户确认。
2. 保留 Sudachi 上下文引擎和 `降り止む` 等审核规则。
3. 保留 Markdown、HTML、JSON 三种输出。
4. 保留显式输出路径、父目录创建和覆盖保护。
5. 把词典记录接到共享引擎的元数据接口，供多个应用共用，而不是各自解析词典。
6. 后续 Agent 只读取 JSON 元数据，不在对话中重新猜读音。

## 分阶段实现

### 阶段 A：可复现获取（已完成）

- 固定上游仓库和 release API。
- 下载默认资产。
- 保存 manifest 和 SHA-256。
- 不把第三方词典打进安装包。

### 阶段 B：词典索引（已完成基础版）

- 已解析 Yomitan `index.json` 和 term bank。
- 已建立本地只读索引，并支持从单个词典目录或 `var/yomitan/extracted` 加载。
- 已支持按表面词和读音做候选对照，包含 JMnedict 中以定义数组保存的人名读音。
- 已解析 KANJIDIC 单字音读、训读、标签、英文释义、频度、笔画数和其他引用字段。
- 已在 JSON 中报告词典是否启用、来源标题、term 数量、KANJIDIC 数量、词典命中、候选读音、候选标签、`reading_status` 和是否与引擎读音一致。
- `scripts/audit_yomitan_data.py` 会校验 manifest 的 SHA-256、format 3、四类默认资产和基本词条样本。
- `scripts/audit_reading_disagreements.py` 会按标准语料输出主引擎与 Yomitan 候选读音的差异，不自动把差异写成覆盖规则。

### 阶段 C：审计增强

- 已对 Sudachi、Yomitan 词典和人工规则做差异报告；当前 JSON 已提供 term/kanji 审计基础数据。
- 已加入人名、多音字、地名和歌词短语标准语料；后续继续扩充长文本覆盖。
- 只有有证据的覆盖才可阻断生产审计。

### 阶段 D：学习与 Agent 能力

- 词性、释义、词频、音调和例句的可选展示。
- Anki/学习卡片导出。
- HTML 中点击词语查看词典信息。
- 未来再接入 OCR、音频和更重的上下文模型。

## 许可证与隐私

- 每次获取都保存上游地址、release tag 和 SHA-256。
- 保留 JMdict、JMnedict、KANJIDIC 及具体词典文件的上游许可说明。
- 只参考 Yomitan 的数据格式和公开数据，不复制 Yomitan 的 GPL 代码到 Bunomi。
- 页面 URL、截图和用户文本属于用户内容；当前 MVP 不自动抓取或上传这些内容。
