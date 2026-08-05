---
name: japanese-translation
description: 共享日语翻译能力：把带或不带 ruby 注音的日语文本逐句翻译成目标语言，保持换行、空行分组、ruby 标注、标题与占位符，并支持多语言扩展。Use when a user asks to translate Japanese text, add a translation to Japanese learning material or lyrics, or when Bunomi/Utayomi need a line-preserving translation step. 默认简体中文，其他目标语言见 references/languages.md。
---

# Japanese Translation（共享翻译能力）

供 Bunomi、Utayomi 等日语类技能复用。不要在各自技能里维护另一套翻译规范；
翻译的输入/输出契约、语言约定和结构校验统一由本技能提供，调用方只负责自己的排版。

## 目标语言选择

1. 默认目标语言为简体中文（zh-CN）。
2. 翻译前先读 [references/languages.md](references/languages.md) 确认目标语言已注册。
3. 只翻译已注册的语言；未注册的语言先按“多语言扩展”流程添加，或明确告知用户当前不支持。
4. 用户未指定目标语言时，根据用户交流语言和文本用途判断；仍不确定时先询问，不要臆测。

## 输入与输出契约

输入可以是：

- 纯日语文本（Bunomi 学习文本、歌词正文）；
- 带 `<ruby>…<rt>…</rt></ruby>` 注音的日语文本；
- 含 Markdown 标题、空行分组、括号、`♪`、`[Chorus]` 等占位符的文本。

输出为与源文本结构一一对应的翻译：

- 逐句/逐行翻译，保持源文本的换行和空行分组；不合并、不拆分句子。
- 翻译行不重复标注 ruby；日语原文行由调用方保留并自行排版。
- 保留标题、占位符、和声标记、括号内容和未翻译的专名。
- 只输出翻译内容，不添加译注、赏析、摘要块或“处理结果”等自检说明。
- 每个目标语言的具体约定见 [references/zh-CN.md](references/zh-CN.md) 等语言文件。

## 工作流

1. 读取目标语言参考文件，确认标点、专名、语气等约定。
2. 逐句翻译成目标语言，保持一行对应一行。
3. 将翻译结果交给调用方（Bunomi 按对话格式、Utayomi 按“日语行 + 翻译行”排版）。
4. 运行结构校验：

   ```bash
   python3 scripts/validate_translation.py --source source.txt --translation translation.txt --paired
   ```

5. 修正校验报告中的错误；kana 警告按目标语言参考判断是否可接受，可接受时在对话中说明。

## 多语言扩展

新增目标语言步骤见 [references/languages.md](references/languages.md)：
注册语言代码 + 新建 `references/<code>.md` 约定文件 + 用校验脚本验证一次示例。

## 边界

- 不访问网络、不抓取外部翻译，只翻译用户提供或调用方传入的文本。
- 不代替 Bunomi 注音，不处理 Utayomi 的歌词清洗、标题识别和歌词排版。
- 专名和外来词按语言参考处理；歧义时保留原文并在对话中说明，不要臆造。
