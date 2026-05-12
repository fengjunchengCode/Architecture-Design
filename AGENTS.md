# Agent 工作流入口

## 总原则

本仓库面向 agent 使用。仓库可以被 clone 到任意目录，所有脚本必须从自身位置推导仓库根目录，不得假设 `~/Architecture`。

`projects/{项目代号}/05_output/record.md` 是唯一核心真相文件。Notion、Obsidian 或其他知识库只能作为后续可选投影，不作为核心数据源。

Python 脚本只做确定性工作：初始化目录、扫描文件、计算 hash、校验 YAML/frontmatter、检查 S0 区位图门槛、生成机器可读报告。建筑语义理解、冲突判断、低置信标记、pending questions 和正文写入由 agent 按 skill 完成。

## 首次进入仓库

1. 运行依赖安装：

```powershell
python -m pip install -r requirements.txt
```

2. 运行自检：

```powershell
python _tools/selfcheck.py
```

3. 读取核心契约：

- `_schema/record.schema.md`
- `_schema/folder.convention.md`
- `skills/S0_project_intake/SKILL.md`

## 新项目初始化

1. 创建项目骨架：

```powershell
python _tools/init_project/scaffold.py 26-SZ-NSXX --type school --name "深圳南山某小学"
```

2. 确认用户已放置资料。区位图是 S0 硬门槛，至少需要一个文件位于：

```text
projects/{项目代号}/02_site/区位图/
```

3. 运行文件盘点：

```powershell
python _tools/inventory.py 26-SZ-NSXX --require-s0-ready
```

4. 执行 S0 skill：读取 inventory、原始资料和 schema，由 agent 更新 `record.md` 与 `parse_log.md`。无法确认的信息进入 `pending_questions`；已有值但不确定的信息进入 `low_confidence_fields`。

5. 写入后校验：

```powershell
python _tools/validate_record.py 26-SZ-NSXX
```

## 写入约束

- 每个 skill 只能改写自己 marker 之间的正文段。
- YAML frontmatter 字段必须遵守 `_schema/record.schema.md`。
- 新字段先改 schema，再改工具和 skill。
- 不要把外部平台字段写入核心 schema。外部同步以后放到 `integrations/` 或独立投影器。
