---
name: architecture-workflow
description: 建筑设计项目的总协议与主路由 skill。用于用户要求初始化项目、上传资料、执行 S0/S1/S2/S3/S4/S9、查看状态、判断下一步、整理甲方问题、按标准工作流推进建筑方案设计时。先读取项目 record/inventory/schema，按 gate 和路由表选择子 skill；本 skill 不直接写阶段正文。
---

# Architecture Workflow

本文件是仓库的主 skill，也是 agent 进入本项目后的总协议和路由器。`skills/*/SKILL.md` 都是阶段子 skill，不能替代本入口。

主 skill 只做四件事：

1. 判断用户意图和当前项目状态。
2. 检查 workflow gate、输入资料和可写范围。
3. 按路由表选择最小必要子 skill。
4. 明确执行模板、阻塞原因和写入后校验命令。

不要在本 skill 内直接写 `record.md` 的阶段正文。阶段正文只能由对应子 skill 写入自己的 marker 段。

## 必读顺序

进入任意项目工作前，按顺序读取：

1. `AGENTS.md`
2. `_schema/record.schema.md`
3. `_schema/folder.convention.md`
4. `skills/_shared/*.md` 中和当前任务有关的协议
5. 将要执行的子 skill，例如 `skills/S0_project_intake/SKILL.md`

默认不要读取 `docs/planning/`。只有用户明确要求查看历史背景、baseline、步骤规划时才读取。

## 不可妥协原则

1. `projects/{code}/05_output/record.md` 是唯一核心真相文件。
2. Notion、Obsidian、UI、inventory、派生状态文件都不能替代 `record.md`。
3. Python 只做确定性工作：脚手架、扫描、hash、校验、格式转换、机器报告。
4. Agent 做语义判断：资料归类、字段抽取、冲突判断、低置信标记、甲方问题、设计分析。
5. 区位图是 S0/S1 硬门槛。缺 `projects/{code}/02_site/区位图/` 文件时不得执行 S0/S1 解析。
6. 每个子 skill 只能写自己的 marker 段。跨段写入必须拒绝并重新路由。
7. 抽不到的信息进入 `pending_questions`；已有值但不确定进入 `low_confidence_fields`。
8. 新字段先改 `_schema/record.schema.md`，再改工具和 skill。

## 路由前检查

收到用户请求后先确认：

- 项目代号：来自用户输入，或从 `projects/*` 唯一候选推断；不唯一时先询问。
- `record.md` 是否存在：`projects/{code}/05_output/record.md`。
- 是否已有 `inventory.json`；需要时运行 `python _tools/inventory.py {code} --write`。
- 写入前后都要知道校验命令：`python _tools/validate_record.py {code}`。
- 用户要的是执行阶段、查看状态、计划下一步，还是解释规则。

## 文件读取策略

先相信 `inventory.json` 的 `read_policy`，不要让 agent 临时硬读二进制文件：

- `direct_text`：可作为文本读取，但仍需控制大小。
- `document_extract`：只能用明确的文档/PDF 提取器或渲染器，不读取原始二进制。
- `visual_asset`：先运行 `python _tools/vision_route.py {code} --write`，由工具自动路由到 `VISION_MODEL`；不要让用户手动切换 API 模型。未配置视觉模型时，读取 `05_output/vision/*.json` 的降级结果并写入 pending/low confidence。
- `legacy_word_conversion_required`：老 `.doc` 二进制文件只登记路径/hash。必须先转换为 `.docx`、PDF 或 TXT，才能进入语义抽取。
- `binary_index_only` / `unknown_index_only`：只登记路径、hash、文件名；没有专用解析器时不得推断正文。

正文提取优先使用 `python _tools/extract_text.py {文件路径}`。该工具会安全读取文本和 `.docx`，并对 `.doc` 明确返回 `conversion_required`。

视觉资料解析优先使用：

```powershell
python _tools/vision_route.py {项目代号} --write
```

该工具根据环境变量 `VISION_MODEL` 自动调用视觉模型并把结果写入 `05_output/vision/`。如果 `OPENAI_API_KEY` 或 `VISION_MODEL` 未配置，工具会写入降级 sidecar，S0 应继续推进并把地址、坐标、红线等缺口进入 `pending_questions`，而不是要求用户切换模型。

禁止把 `strings`、裸 `cat`、裸 `Read`、临时 `textract` 探测作为 `.doc` 的兜底解析流程。若 `01_briefing/` 里只有 `.doc`，S0 可以从文件名和其他资料提取有限信息，并把“任务书正文需转换”写入 `pending_questions` 或 `parse_log.md`。

## 最小续跑机制

本项目不依赖复杂自愈状态机。续跑只以 `record.md` 为准：

1. 进入已有项目时，先读取 `projects/{code}/05_output/record.md`，不要默认从 S0 重新执行。
2. 通过 frontmatter 的 `completeness.ready_for`、`completeness.blocked`、`pending_questions`、`low_confidence_fields` 判断当前状态。
3. 通过各 marker 是否已有有效正文判断阶段是否已经执行。
4. 如果目标阶段 marker 已有内容，先说明“检测到已有结果”，再判断是继续补充、基于新增资料重跑本阶段，还是进入下一阶段。
5. 重跑某一阶段时，只重写该阶段自己的 marker，并保留其他阶段结果。
6. 只有 `record.md` 缺失、marker 结构损坏且无法修复、或用户明确要求重新开始时，才从初始化/S0 重新进入。

不要因为缺少 `workflow_state.json`、`skill_runs.jsonl`、外部数据库或 Notion 状态而强制从头执行。这些文件如果未来出现，也只能是从 `record.md` 重建的辅助投影。

## 路由表

| 用户意图 / 状态 | 子 skill | 前置检查 | 阻塞处理 |
|---|---|---|---|
| 新建项目、初始化骨架、创建目录 | `S0_project_intake` | project code 合法；项目不存在或允许 resume | 只做 scaffold，不做语义解析 |
| 上传资料、启动 UI、运行 inventory | `S0_project_intake` | 仓库自检通过 | 只做投递和确定性检查 |
| 解析资料、建立项目档案、执行 S0 | `S0_project_intake` | `inventory --require-s0-ready` 通过 | 缺区位图时停止，列缺失项 |
| 区位、周边、入口、500m/1000m 场地分析 | `S1_site_analysis` | 有区位图；`site.address` 或 `site.coords` 至少其一 | 缺位置时转 S4 问题清单 |
| DWG、红线、地形、面积、形状几何解析 | `S2_dwg_parse` | `02_site/地形图/` 有 DWG/PDF/红线资料 | 缺资料时写 blocked，不伪造面积 |
| 任务书拆解、面积测算、容积率/强排初判 | `S3_area_and_massing` | 有 `brief.summary` 或类型模板关键信息；强排需要 `site.area_sqm` | 面积缺失时只做 S3a，S3b 标阻塞 |
| 甲方问题清单、低置信字段归并 | `S4_questions_summary` | 无硬前置 | 任意阶段可跑，只读各阶段结果 |
| 汇报大纲、汇报文档草稿 | `S9_report_outline` | S1/S3 至少有有效正文 | 前置不足时转 S4 或列缺口 |
| 用户问“下一步/状态/进度” | 本 router + 只读状态检查 | 读 `record.md`、inventory、validation | 给出下一步，不直接写正文 |

## 执行模板

路由到子 skill 前，先明确：

```text
项目：{code}
选择 skill：{skill}
选择原因：{reason}
将读取：{inputs}
允许写入：{marker/files}
阻塞项：{blocked_or_none}
写入后校验：python _tools/validate_record.py {code}
```

## 共享协议

按需要读取：

- `skills/_shared/record_contract.md`：`record.md`、frontmatter、真相源边界。
- `skills/_shared/marker_contract.md`：marker 写入范围和幂等规则。
- `skills/_shared/folder_contract.md`：目录、上传、S0 gate。
- `skills/_shared/confidence_contract.md`：pending/low confidence 判定。
- `skills/_shared/output_style.md`：建筑分析输出格式。

## 拒绝规则

- 用户要求跳过区位图执行 S0/S1：拒绝，先补区位图。
- 用户要求直接写后续阶段但前置 marker 缺失：拒绝或转 S4 列阻塞项。
- 用户要求把推测值当确定字段：拒绝，写低置信或 pending。
- 用户要求修改非当前 skill marker：拒绝，说明应路由到哪个 skill。
- 用户要求把 Notion/Obsidian 当核心数据源：拒绝，最多作为投影。
