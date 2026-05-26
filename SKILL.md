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

## 开发改动守则

当用户要求修改代码、工具、UI、schema、skill 或文档时，先读取 `skills/_shared/development_contract.md`。该契约要求：

- 先澄清目标、假设和验收标准。
- 优先最小可行改动，不添加未要求的功能。
- 精准修改，避免顺手重构无关代码。
- 每个改动都要有验证闭环。

如果用户指出实现方向不符合要求，agent 应先暂停继续实现，回到需求和成功标准，不要沿着旧方案继续堆功能。

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
- `visual_asset`：优先由当前主对话模型读取，前提是当前模型/运行环境具备视觉输入能力。若主模型无视觉能力、需要批量 sidecar，或由 UI/脚本无人值守运行，则运行 `python _tools/vision_route.py {code} --write` 路由到配置的视觉 provider。两者都不可用时，读取 `05_output/vision/*.json` 的降级结果并写入 pending/low confidence。
- `legacy_word_conversion_required`：老 `.doc` 二进制文件只登记路径/hash。必须先转换为 `.docx`、PDF 或 TXT，才能进入语义抽取。
- `binary_index_only` / `unknown_index_only`：只登记路径、hash、文件名；没有专用解析器时不得推断正文。

正文提取优先使用 `python _tools/extract_text.py {文件路径}`。该工具会安全读取文本和 `.docx`，并对 `.doc` 明确返回 `conversion_required`。

DWG/DXF 地形资料进入 S2 时，先使用确定性 CAD 工具链：

```powershell
python _tools/dwg_probe.py {项目代号} --json --write
```

该工具会自动检测 `ezdxf` 与 ODA File Converter；缺少依赖时返回 `install_guidance`，agent 应先按指引安装或配置后重跑。手动 CAD 导出 DXF 只作为自动转换失败后的降级方案。

S1 区位与外部关系分析优先使用确定性高德上下文工具：

```powershell
python _tools/amap_context.py {项目代号} --write
```

如果用户已提供高德坐标拾取器坐标：

```powershell
python _tools/amap_context.py {项目代号} --location "经度,纬度" --write
```

该工具读取 `.env` 中的 `AMAP_WEBSERVICE_KEY`，调用高德 Web Service 生成 `05_output/amap/s1_map_context.json`。若 key 或定位线索缺失，S1 不得编造道路、POI、水系或入口关系，只能写阻塞和待补问题。

坐标和控制点优先通过本地上传 UI 的“空间定位”面板录入。该面板提供高德坐标拾取器链接，可写入 `05_output/amap/s1_map_context.json` 和 `05_output/amap/control_points.json`；不要只把坐标留在对话历史中。

视觉资料解析策略：

1. 当前主对话模型具备视觉能力时，可以直接读取 `visual_asset`，但必须记录来源文件、观察结论和置信度。
2. 当前主模型无视觉能力、需要批量可复跑 sidecar、或 UI/脚本无人值守运行时，使用：

```powershell
python _tools/vision_route.py {项目代号} --write
```

硬规则：如果主模型无视觉能力，且 `vision_route.py` 返回 `vision_model_not_configured`、`vision_api_error` 或 provider `status=error`，agent 必须把图片语义视为未知，只读取 `05_output/vision/*.json` 降级 sidecar，并把地址、坐标、红线、现场条件等写入 `pending_questions` / `low_confidence_fields`。不得要求用户 `/model` 切换来补读图片。

该工具支持多种视觉 provider（OpenAI、Anthropic、Google），根据环境变量自动选择或由 `VISION_PROVIDER` 指定。如果视觉 provider 未配置，工具会写入降级 sidecar；是否还能继续视觉解析取决于当前主模型是否具备视觉能力。

查看可用 provider 状态：

```powershell
python _tools/vision_route.py --list-providers
```

禁止把 `strings`、裸 `cat`、裸 `Read`、临时 `textract` 探测作为 `.doc` 的兜底解析流程。若 `01_briefing/` 里只有 `.doc`，S0 可以从文件名和其他资料提取有限信息，并把“任务书正文需转换”写入 `pending_questions` 或 `parse_log.md`。

## S1/S2 协作原则

S1 和 S2 是两个清晰阶段，不新增 S1.5，也不拆成 a/b/c：

- S1 负责外部关系：地址/坐标证据、周边道路、水系、POI、到达方向、入口候选和设计影响。
- S2 负责场地几何：DWG/DXF/PDF 红线、边界形状、尺寸、面积、高差、图层语义和可绘制底图资产。
- 两个阶段不强制串行。已有 S1 时，S2 可以读取 `s1_external_context`；已有 S2 时，S1 可以读取 `s2_site_geometry`。
- 精确入口判断需要同时满足外部地图关系和 CAD 配准。只有地址或中心点时，S1 输出“入口候选”；只有 CAD 红线时，S2 输出“边界几何”；二者未配准前不得声称主入口属于某条红线边。
- 地图与 CAD 的关系统一用 `registration_state` 表达：`no_location`、`map_located`、`cad_aligned`。这是状态，不是新阶段。

## 最小续跑机制

本项目不依赖复杂自愈状态机。续跑只以 `record.md` 为准：

1. 进入已有项目时，先读取 `projects/{code}/05_output/record.md`，不要默认从 S0 重新执行。
2. 通过 frontmatter 的 `completeness.ready_for`、`completeness.blocked`、`pending_questions`、`low_confidence_fields` 判断当前状态。
3. 通过各 marker 是否已有有效正文判断阶段是否已经执行。
4. 如果目标阶段 marker 已有内容，先说明“检测到已有结果”，再判断是继续补充、基于新增资料重跑本阶段，还是进入下一阶段。
5. 重跑某一阶段时，只重写该阶段自己的 marker，并保留其他阶段结果。
6. 只有 `record.md` 缺失、marker 结构损坏且无法修复、或用户明确要求重新开始时，才从初始化/S0 重新进入。

不要因为缺少 `workflow_state.json`、`skill_runs.jsonl`、外部数据库或 Notion 状态而强制从头执行。这些文件如果未来出现，也只能是从 `record.md` 重建的辅助投影。

### S10 状态补充扫描

agent 报状态时除 `ready_for` / `blocked` 外，扫文件系统判断 drawing 进度：

- `projects/{code}/05_output/style/style_spec.json` 存在且 `approved_at` 非空 → "风格已锁"
- `projects/{code}/05_output/drawings/svg/` 非空 → 列已出图种
- 任一缺 + ready_for 包含 S9 → 建议先转 S10

drawing 状态**不**进 record.md frontmatter，仅作为 agent 报告的辅助信息。

## 路由表

| 用户意图 / 状态 | 子 skill | 前置检查 | 阻塞处理 |
|---|---|---|---|
| 新建项目、初始化骨架、创建目录 | `S0_project_intake` | project code 合法；项目不存在或允许 resume | 只做 scaffold，不做语义解析 |
| 上传资料、启动 UI、运行 inventory | `S0_project_intake` | 仓库自检通过 | 只做投递和确定性检查 |
| 解析资料、建立项目档案、执行 S0 | `S0_project_intake` | `inventory --require-s0-ready` 通过 | 缺区位图时停止，列缺失项 |
| 区位、周边、到达方向、入口候选、500m/1000m 外部关系 | `S1_site_analysis` | 有区位图；至少有地址、坐标、地图链接或可识别地名/道路线索之一 | 缺定位线索时写 blocked 和待补问题 |
| CAD、红线、地形、面积、尺寸、高差、边界资产与控制点候选 | `S2_dwg_parse` | `02_site/地形图/` 有 DWG/DXF/PDF/红线资料 | 缺资料时写 blocked，不伪造面积 |
| 任务书拆解、面积测算、容积率/强排初判 | `S3_area_and_massing` | 有 `brief.summary` 或类型模板关键信息；强排需要 `site.area_sqm` | 面积缺失时只做已知任务拆解，并标注强排阻塞 |
| 甲方问题清单、低置信字段归并 | `S4_questions_summary` | 无硬前置 | 任意阶段可跑，只读各阶段结果 |
| 汇报大纲、汇报文档草稿 | `S9_report_outline` | S1/S3 至少有有效正文 | 前置不足时转 S4 或列缺口 |
| 出技术图、PPT 用图、确定项目设计风格、画功能分区/交通组织/景观/消防/竖向等 | `S10_technical_drawings` | 至少 S1 完成；项目有底图 | 没 style_spec 走风格协商；已 approved 走 task_pack 出图 |
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
