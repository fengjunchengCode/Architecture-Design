---
name: s0-project-intake
description: 建筑设计工作流 S0 项目档案初始化。用于用户要求创建新项目、投递资料后执行资料盘点、检查区位图 gate、从任务书/区位图/现场照片/聊天记录抽取项目基础字段、初始化 record.md、生成 pending_questions 和 low_confidence_fields 时。只写 record.md 的 s0_parsed marker。
---

# S0 项目档案初始化

## 目标

把一个新建筑设计项目从“资料投递状态”推进到可被后续 S1-S10 使用的 `record.md`。S0 由 agent 主导，Python 只提供目录、文件、hash、校验等确定性结果。

## 共享协议

执行前先读取：

- `SKILL.md`
- `skills/_shared/record_contract.md`
- `skills/_shared/marker_contract.md`
- `skills/_shared/folder_contract.md`
- `skills/_shared/confidence_contract.md`
- `skills/_shared/output_style.md`

如本文与共享协议冲突，以共享协议和 `_schema/record.schema.md` 为准。

## 输入

- `_schema/record.schema.md`
- `_schema/folder.convention.md`
- `projects/{项目代号}/01_briefing/`
- `projects/{项目代号}/02_site/区位图/`
- `projects/{项目代号}/02_site/地形图/`
- `projects/{项目代号}/02_site/现场照片/`
- `projects/{项目代号}/03_references/`
- `projects/{项目代号}/04_chat/`

## 硬门槛

`02_site/区位图/` 至少存在一张 `png`、`jpg`、`jpeg` 或 `pdf`。缺失时不得进入 S0 解析，只能输出缺失提示。

检查命令：

```powershell
python _tools/inventory.py {项目代号} --require-s0-ready --write
```

## Agent 职责

- 阅读 inventory 输出和原始资料。
- 判断文件属于任务书、区位图、地形图、现场照片、参考案例还是聊天记录。
- 从资料中抽取项目名称、甲方、类型、规模、地址、风格偏好、功能需求。
- 判断字段置信度。
- 发现缺失信息并生成 `pending_questions`。
- 将已知但不确定的信息写入 `low_confidence_fields`。
- 更新 `completeness.ready_for` 和 `completeness.blocked`。
- 改写 `<!-- BEGIN:s0_parsed -->` 与 `<!-- END:s0_parsed -->` 之间内容。

## 文件读取策略

S0 必须先看 `inventory.json` 中每个文件的 `read_policy`：

- `direct_text` 文件可以读取文本内容。
- `document_extract` 文件只能通过明确的 PDF/DOCX 提取器或渲染器读取。
- `visual_asset` 文件用视觉方式理解，不做二进制文本探测。
- `legacy_word_conversion_required` 的 `.doc` 文件不得直接读取、不得用 `strings`/裸 `cat`/临时 `textract` 兜底。只记录路径、hash、文件名，并要求转换为 `.docx`、PDF 或 TXT 后再抽取正文。
- `binary_index_only` 和 `unknown_index_only` 只作为文件事实登记，不能推断正文。

正文提取优先使用 `python _tools/extract_text.py {文件路径}`。该工具只处理安全文本和 `.docx`，遇到 `.doc` 会返回 `conversion_required`。

如果 S0 的任务书只有 `.doc`，可以从文件名、聊天记录、区位图和其他文本资料生成最小 `brief.summary`；正文无法确认的信息进入 `pending_questions`，并在 `parse_log.md` 说明“任务书正文需转换后解析”。

## Python 工具职责

- `scaffold.py`：创建目录与空 `record.md`。
- `inventory.py`：扫描文件、计算 hash、判断区位图门槛、标注文件读取策略和转换需求。
- `extract_text.py`：安全提取文本和 `.docx` 正文；遇到 `.doc` 时明确要求转换。
- `validate_record.py`：校验 frontmatter、marker、枚举和项目文件夹一致性。

Python 不负责建筑语义判断，不强制要求用户文件名完全标准。

## 输出

- `projects/{项目代号}/05_output/record.md`
- `projects/{项目代号}/05_output/parse_log.md`
- 可选：`projects/{项目代号}/05_output/inventory.json`

## 写入规则

- 只改写 `s0_parsed` marker 段。
- YAML frontmatter 必须符合 `_schema/record.schema.md`。
- 抽不到的字段不要编造，进入 `pending_questions`。
- 有值但不确定，进入 `low_confidence_fields`。
- 写入后必须运行：

```powershell
python _tools/validate_record.py {项目代号}
```
