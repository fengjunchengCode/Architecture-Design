# Agent 工作流入口

## 总原则

本仓库面向 agent 使用。仓库可以被 clone 到任意目录，所有脚本必须从自身位置推导仓库根目录，不得假设 `~/Architecture`。

`projects/{项目代号}/05_output/record.md` 是唯一核心真相文件。Notion、Obsidian 或其他知识库只能作为后续可选投影，不作为核心数据源。

Python 脚本只做确定性工作：初始化目录、扫描文件、计算 hash、校验 YAML/frontmatter、检查 S0 区位图门槛、生成机器可读报告。建筑语义理解、冲突判断、低置信标记、pending questions 和正文写入由 agent 按 skill 完成。

文件读取必须遵守 `inventory.json` 的 `read_policy`。正文提取优先使用 `python _tools/extract_text.py {文件路径}`。老 `.doc` 二进制文件只登记路径/hash/文件名，必须先转换为 `.docx`、PDF 或 TXT 后再做语义解析；不得用 `strings`、裸 `cat`、裸 `Read` 或临时 `textract` 探测作为兜底。

图片资料（`visual_asset`，如 JPG/PNG 区位图、现场照片）必须通过 `python _tools/vision_route.py {项目代号} --write` 自动路由到配置的视觉模型。支持多种 provider（OpenAI、Anthropic、Google），通过 `VISION_PROVIDER` 环境变量选择。不得要求用户手动切换 API 模型；若视觉模型未配置，则读取 `05_output/vision/` 降级 sidecar，并把地址、坐标、红线等缺口写入 `pending_questions` 或 `low_confidence_fields`。

## 上下文边界

默认只读取以下权威入口：

- `AGENTS.md`
- `README.md`
- `SKILL.md`
- `_schema/record.schema.md`
- `_schema/folder.convention.md`
- `_schema/folder.convention.yaml`
- `skills/_shared/*.md`
- `skills/*/SKILL.md`
- `_tools/*.py` 与 `_tools/init_project/*.py`

`docs/planning/` 是历史规划与讨论材料，只在用户明确要求“查看背景、历史规划、baseline、步骤规划”时读取。不要把其中内容当作当前执行规范；如与 `_schema/`、`skills/` 或本文件冲突，以当前权威入口为准。

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
- `SKILL.md`
- `skills/S0_project_intake/SKILL.md`

后续阶段默认先由 `SKILL.md` 做路由，再读取对应子 skill。根 skill 只负责总协议、gate 和路由，不直接写 `record.md` 阶段正文。

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

也可以启动本地上传 UI 完成资料投递：

```powershell
python _tools/uploader/server.py
```

默认访问 `http://127.0.0.1:8765`。

4. 执行 S0 skill：读取 inventory、原始资料和 schema，由 agent 更新 `record.md` 与 `parse_log.md`。无法确认的信息进入 `pending_questions`；已有值但不确定的信息进入 `low_confidence_fields`。

5. 写入后校验：

```powershell
python _tools/validate_record.py 26-SZ-NSXX
```

## 续跑原则

续跑以 `record.md` 为准。已有 marker 内容代表该阶段已有结果，agent 不得因为缺少额外状态文件而从 S0 重新开始。

进入已有项目时，先读 `record.md` frontmatter、各阶段 marker、`completeness.ready_for` 和 `completeness.blocked`，再决定是补充当前阶段、重跑某个阶段，还是进入下一阶段。

## 写入约束

- 每个 skill 只能改写自己 marker 之间的正文段。
- 根 skill `SKILL.md` 不写阶段正文，只做路由和执行前检查。
- YAML frontmatter 字段必须遵守 `_schema/record.schema.md`。
- 新字段先改 schema，再改工具和 skill。
- 不要把外部平台字段写入核心 schema。外部同步以后放到 `integrations/` 或独立投影器。
