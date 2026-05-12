# S0 项目档案初始化

## 目标

把一个新建筑设计项目从“资料投递状态”推进到可被后续 S1-S10 使用的 `record.md`。S0 由 agent 主导，Python 只提供目录、文件、hash、校验等确定性结果。

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

## Python 工具职责

- `scaffold.py`：创建目录与空 `record.md`。
- `inventory.py`：扫描文件、计算 hash、判断区位图门槛。
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
