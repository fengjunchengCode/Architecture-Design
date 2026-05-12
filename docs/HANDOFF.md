# 项目交接文档

## 1. 仓库定位

本仓库是面向 agent 的建筑设计工作流仓库，目标是把建筑方案工作拆成可持续执行的阶段：

- S0：项目档案初始化
- S1：区位与场地语义分析
- S2：DWG 地形图解析
- S3：任务书拆解与面积测算
- S4：甲方问题清单管理
- S5-S10：强排、CAD、SU、渲染、汇报文档、PPT 等后续阶段

当前已经落地的是：目录/schema、脚手架、文件盘点、校验、本地上传 UI，以及第一版 skill 系统骨架。Skill 系统采用“根 skill router + 阶段子 skill + shared 协议库”的结构。Python 脚本只做确定性工作；建筑语义理解、字段判断、低置信标记、pending questions 和正文写入由 agent 按 skill 完成。

历史背景可参考 `docs/planning/`，但它不是当前执行规范。若历史规划与 `AGENTS.md`、`_schema/`、`skills/` 或 `_tools/` 冲突，以当前权威入口为准。

续跑策略采用最小机制：只以 `record.md` 为准。只要 `record.md` 的 frontmatter 可解析、marker 成对且校验可运行，agent 就应从已有 marker 和 `completeness` 继续，不要因为缺少 `workflow_state.json`、`skill_runs.jsonl` 或外部平台状态而从 S0 重新开始。

## 2. 权威入口

新 agent 进入仓库后，优先读取以下文件：

```powershell
AGENTS.md
README.md
_schema/record.schema.md
_schema/folder.convention.md
_schema/folder.convention.yaml
SKILL.md
skills/_shared/*.md
skills/S0_project_intake/SKILL.md
skills/S1_site_analysis/SKILL.md
skills/S2_dwg_parse/SKILL.md
skills/S3_area_and_massing/SKILL.md
skills/S4_questions_summary/SKILL.md
skills/S9_report_outline/SKILL.md
_tools/*.py
_tools/init_project/*.py
_tools/uploader/README.md
```

默认不要读取 `docs/planning/`。只有用户明确要求查看历史背景、baseline 或步骤规划时才读取，并且只当作背景材料。

## 3. 核心真相与约束

唯一核心真相文件：

```text
projects/{项目代号}/05_output/record.md
```

Notion、Obsidian 或其他知识库以后只能作为投影，不作为核心数据源。不要把外部平台字段写入核心 schema；如需同步，后续放到 `integrations/` 或独立投影器。

`record.md` 的硬必填字段只有：

- `schema_version`
- `project.code`
- `project.name`

其他字段允许 `null` 或缺失。抽不到的信息进入 `pending_questions`；已有值但不确定的信息进入 `low_confidence_fields`。

每个 skill 只能改写自己的 marker 段。例如 S0 只能改：

```markdown
<!-- BEGIN:s0_parsed -->
...
<!-- END:s0_parsed -->
```

新增字段时必须先改 `_schema/record.schema.md`，再改工具和 skill。

## 4. 当前进度

仓库自检已通过：

```powershell
python _tools/selfcheck.py
```

本轮 skill 系统重构已完成第一版骨架：

- 新增根 router：`SKILL.md`
- 新增 shared 协议库：`skills/_shared/record_contract.md`、`marker_contract.md`、`folder_contract.md`、`confidence_contract.md`、`output_style.md`
- 新增阶段 SOP：`skills/S1_site_analysis/SKILL.md`、`skills/S2_dwg_parse/SKILL.md`、`skills/S3_area_and_massing/SKILL.md`、`skills/S4_questions_summary/SKILL.md`、`skills/S9_report_outline/SKILL.md`
- 更新 S0：`skills/S0_project_intake/SKILL.md` 增加标准 frontmatter，并引用 shared 协议
- 更新入口：`AGENTS.md`、`README.md`、`docs/agent.install.md`
- 更新自检：`_tools/selfcheck.py` 会检查新 skill 文件存在，并检查阶段 `SKILL.md` 的 `name` / `description` frontmatter

这仍是 prompt/SOP 层重构，尚未开发 hooks、workflow_state 写入器或新 Python 工具。

当前工作树存在一个未跟踪项目目录：

```text
projects/26-BQ-PARK/
```

该目录包含真实项目资料和输出占位，当前 `git status --short` 显示为未跟踪。不要在不确认的情况下提交整个项目资料目录，尤其是 DWG、照片、甲方文档等二进制或业务数据。

`26-BQ-PARK` 当前状态：

- 项目名：巴青县城西口袋公园建设项目
- 项目类型：`park`
- `record.md` 已由脚手架创建
- S0 区位图 gate 已满足
- S0 语义解析尚未执行
- `record.md` 校验无 fatal，仅有 `brief.summary` 缺失 warning

当前资料盘点结果：

- `01_briefing/`：1 个 `.doc` 需求文件
- `02_site/区位图/`：3 张区位图
- `02_site/地形图/`：2 个 `.dwg`，另有 `.dwl` / `.dwl2` 锁文件
- `02_site/现场照片/`：13 张现场照片
- `03_references/`：0
- `04_chat/`：0

已生成：

```text
projects/26-BQ-PARK/.uploader.yaml
projects/26-BQ-PARK/05_output/record.md
projects/26-BQ-PARK/05_output/inventory.json
```

尚未生成：

```text
projects/26-BQ-PARK/05_output/parse_log.md
projects/26-BQ-PARK/05_output/汇报文档.md
```

## 5. 不应提交的数据

默认不要提交以下内容，除非主 agent 或用户明确确认：

```text
projects/26-BQ-PARK/01_briefing/*
projects/26-BQ-PARK/02_site/**/*
projects/26-BQ-PARK/03_references/*
projects/26-BQ-PARK/04_chat/*
```

原因：这些是甲方资料、现场照片、DWG、锁文件或项目业务数据。`record.md` 是核心真相文件，按仓库设计应保留，但当前整个项目目录仍未跟踪，是否纳入版本控制需要主 agent 确认。

如果只提交本轮 writing plans 产物，提交范围应限制为：

```text
docs/HANDOFF.md
docs/SKILL_SYSTEM_PLAN.md
```

如果提交本轮 skill 系统重构，还应加入：

```text
AGENTS.md
README.md
docs/agent.install.md
_tools/selfcheck.py
SKILL.md
skills/_shared/*.md
skills/S0_project_intake/SKILL.md
skills/S1_site_analysis/SKILL.md
skills/S2_dwg_parse/SKILL.md
skills/S3_area_and_massing/SKILL.md
skills/S4_questions_summary/SKILL.md
skills/S9_report_outline/SKILL.md
```

不要顺手提交 `projects/26-BQ-PARK/` 的真实项目资料。

## 6. 安装与自检

首次进入仓库后执行：

```powershell
python -m pip install -r requirements.txt
python _tools/selfcheck.py
```

依赖目前只有：

```text
PyYAML>=6.0
```

自检会确认 Python 版本、PyYAML、schema、工具脚本、上传 UI 静态文件、根 router、shared 协议和阶段 skill 是否存在；同时检查阶段 skill frontmatter，并编译核心 Python 脚本。

## 7. 新项目初始化

创建项目骨架：

```powershell
python _tools/init_project/scaffold.py 26-SZ-NSXX --type school --name "深圳南山某小学"
```

项目代号格式：

```text
{YY}-{CITY2_3}-{ABBR}
```

示例：

```text
26-SZ-NSXX
26-BJ-LFGY
26-BQ-PARK
```

脚手架会创建标准目录、`05_output/record.md` 和项目级 `.uploader.yaml`。如果项目已存在，需要显式使用 `--resume`，且脚手架不会覆盖已有 `record.md`。

## 8. 上传 UI

启动本地上传 UI：

```powershell
python _tools/uploader/server.py
```

默认访问：

```text
http://127.0.0.1:8765
```

上传 UI 负责：

- 创建或打开项目
- 上传资料到标准目录
- 检查 S0 区位图 gate
- 运行 `inventory.py`
- 运行 `validate_record.py`

上传 UI 不负责语义解析。真正的 S0 解析仍由 agent 按 `skills/S0_project_intake/SKILL.md` 执行。

## 9. 执行 S0

S0 硬门槛：

```text
projects/{项目代号}/02_site/区位图/
```

至少存在一个 `png`、`jpg`、`jpeg` 或 `pdf` 文件。缺失时不得进入 S0 解析。

先运行盘点：

```powershell
python _tools/inventory.py {项目代号} --require-s0-ready --write
```

然后由 agent 先读取 `SKILL.md` 做路由，再执行 S0 skill：

1. 读取 `_schema/record.schema.md`、`_schema/folder.convention.md` 和 `skills/S0_project_intake/SKILL.md`。
2. 读取 `05_output/inventory.json` 和原始资料。
3. 抽取项目名称、甲方、类型、规模、地址、风格偏好、功能需求。
4. 无法确认的信息写入 `pending_questions`。
5. 已有值但不确定的信息写入 `low_confidence_fields`。
6. 更新 `files_indexed`、`completeness.ready_for` 和 `completeness.blocked`。
7. 只改写 `s0_parsed` marker 段。
8. 写入或追写 `05_output/parse_log.md`。
9. 校验：

```powershell
python _tools/validate_record.py {项目代号}
```

对当前项目可直接执行：

```powershell
python _tools/inventory.py 26-BQ-PARK --require-s0-ready --write
python _tools/validate_record.py 26-BQ-PARK
```

随后进入 S0 语义解析。注意当前 `record.md` 的 blocked 仍写着“尚未投递区位图”，这是脚手架占位状态；实际 inventory 已显示 `s0_ready: true`，S0 执行时应修正 `completeness`。

## 10. 文件夹约定摘要

标准项目结构：

```text
projects/{项目代号}/
├── 01_briefing/
├── 02_site/
│   ├── 区位图/
│   ├── 地形图/
│   └── 现场照片/
├── 03_references/
├── 04_chat/
└── 05_output/
    ├── record.md
    ├── parse_log.md
    └── 汇报文档.md
```

关键规则：

- 项目文件夹名必须等于 `record.md` 中的 `project.code`
- 区位图是 S0 和 S1 的全局硬门槛
- DWG 不阻塞 S0，但会影响 S2 和 S3b
- `05_output/` 是 agent 输出区，人不应手工随意改
- 上传助手会按规则处理文件名，但 S0 不要求用户文件名完全标准

## 11. 下一步建议

当前最直接的下一步是用新的根 router 对 `26-BQ-PARK` 执行 S0：

1. 确认用户允许 agent 阅读 `26-BQ-PARK` 的项目资料。
2. 运行 `inventory.py --require-s0-ready --write` 更新盘点。
3. 按 S0 skill 读取需求文档、区位图、现场照片和 DWG 文件清单。
4. 更新 `record.md` frontmatter、`s0_parsed` marker 段和 `parse_log.md`。
5. 运行 `validate_record.py 26-BQ-PARK`。
6. 由主 agent 决定哪些输出可以提交，哪些项目资料继续留在本地。

需要主 agent 合并校对的点：

- 是否把 `projects/26-BQ-PARK/05_output/record.md` 纳入版本控制。
- 是否需要将 DWG、照片、甲方文档排除在普通 Git 提交之外，或改用 Git LFS。
- `26-BQ-PARK` 的 `.doc` 需求文件是否需要转换为可稳定解析的 `.docx`、`.pdf` 或 `.md`。
- `record.md` 的 `stage` 在 S0 完成后应从 `待放置文件` 更新为更准确的阶段。
- `parse_log.md` 的格式是否需要补充更具体模板。
