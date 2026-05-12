# Skill 系统重构下一步计划

## 目标

把当前“AGENTS.md + 单个 S0 skill + schema/tool 约束”的早期形态，重构为接近 cheat-on-content 的 skill 系统：根 skill 负责总协议和路由，子 skill 负责阶段 SOP，shared references 存放稳定协议库，hooks 和派生状态文件负责执行约束。先写清 writing plans 和 prompt 契约，再开发脚本或重构目录。

当前核心真相仍然是 `projects/{项目代号}/05_output/record.md`。

## 实施状态（2026-05-12）

本计划的 Phase 1 和 Phase 2 已完成第一版 prompt/SOP 骨架：

- 已新增根 router：`SKILL.md`
- 已新增 shared references：`skills/_shared/*.md`
- 已新增 S1/S2/S3/S4/S9 子 skill SOP
- 已更新 S0，使其具备标准 skill frontmatter 并引用 shared references
- 已更新 `AGENTS.md`、`README.md`、`docs/agent.install.md`、`docs/HANDOFF.md`
- 已更新 `_tools/selfcheck.py`，让自检覆盖新 skill 文件和阶段 skill frontmatter

尚未开始 Phase 3/4/5：没有新增 `workflow_state.json` 写入器，没有开发 hooks，没有添加回归样例项目。

根据当前决策，短期不引入复杂自愈机制。续跑只依赖 `record.md`：frontmatter、`completeness`、`pending_questions`、`low_confidence_fields` 和各阶段 marker 足够让 agent 判断已经执行到哪一步。`workflow_state.json`、`skill_runs.jsonl` 如未来需要，只能作为可重建的辅助投影，不作为继续工作的前置条件。

## 为什么需要根 skill router

当前仓库已经有清晰的 schema、marker 和工具边界，但 agent 入口分散在 `AGENTS.md`、`_schema/*.md`、`skills/S0_project_intake/SKILL.md` 和 `_tools/*.py`。当后续加入 S1/S2/S3/S4/S9 后，如果每个 skill 独立解释规则，容易出现三类问题：

- 路由不一致：同一批资料到底该跑 S0、S1、S3a 还是 S4，取决于当前 agent 读到哪个文档。
- 写入边界漂移：每个 skill 都要重复记住“只写自己 marker”“frontmatter 遵守 schema”“Python 不做语义判断”。
- 上下文膨胀：每次执行都读完整 schema、folder 约定、所有 skill，后续阶段会越来越慢，也更容易误读历史规划材料。

根 skill router 的作用不是替代 `AGENTS.md`，而是把 agent 执行层的协议集中成一个可复用入口：

- 先判定任务类型、项目代号、当前阶段、资料是否满足 gate。
- 再按路由表加载最小必要子 skill 和 shared references。
- 最后给出执行前检查、允许写入范围、校验命令和失败处理。

## 建议目录

建议保留现有 `skills/S0_project_intake/`，新增根 skill 和 shared references。第一阶段先只写文档，不移动现有文件。

```text
skills/
  SKILL.md                        # 根 skill：总协议、路由器、执行前检查
  S0_project_intake/
    SKILL.md                      # 已存在：项目档案初始化
  S1_site_analysis/
    SKILL.md                      # 区位与周边分析 SOP
  S2_dwg_parse/
    SKILL.md                      # DWG/红线/地形解析 SOP
  S3_area_and_massing/
    SKILL.md                      # 面积测算 + 容积率/强排校核 SOP
  S4_questions_summary/
    SKILL.md                      # 待问问题归并与甲方话术 SOP
  S9_report_outline/
    SKILL.md                      # 汇报大纲与文档草稿 SOP
  _shared/
    record_contract.md            # record.md 读写协议摘要
    marker_contract.md            # marker 写入边界与幂等规则
    folder_contract.md            # 投递目录与 gate 摘要
    confidence_contract.md        # pending / low_confidence 判定标准
    output_style.md               # 建筑项目输出语气、表格、引用规则
```

后续如需要 Codex/Claude 双端兼容，可再增加 bridge 文件，但不要在第一阶段引入。

## 子 skill 拆分

建议按照 `record.schema.md` 中已经存在的 marker 和解锁条件拆分，不先发明新阶段。

| 子 skill | 写入范围 | 主要输入 | 输出 |
| --- | --- | --- | --- |
| S0_project_intake | `s0_parsed` + frontmatter | inventory、brief、区位图、聊天、参考案例 | 初始化字段、文件索引、pending、low_confidence、parse_log |
| S1_site_analysis | `s1_site_analysis` | 区位图、地址/坐标、现场照片、S0 摘要 | 周边路网、入口建议、500m/1000m 场地判断 |
| S2_dwg_parse | `s2_dwg_parse` | DWG/PDF 红线、地形资料、inventory | 地块几何、面积、形状、高差、可疑点 |
| S3_area_and_massing | `s3_area_calc` | brief、project.type 模板、site.area_sqm、规范依据 | 面积需求表、容积率校核、强排初判 |
| S4_questions_summary | `s4_questions_summary` | frontmatter pending_questions、低置信字段、各阶段正文 | 甲方问题清单、分类、优先级、提问话术 |
| S9_report_outline | `s9_report_outline`，可另写 `05_output/汇报文档.md` | S1/S3/S4、风格偏好、参考案例 | 汇报大纲、六段式文档草稿 |

S3 建议先合并为一个 skill，内部区分 `S3a 面积需求测算` 和 `S3b 容积率/强排校核`。原因是现有 schema 只有一个 `s3_area_calc` marker，拆成两个 skill 会先引入 marker 和 validate 变更，不适合第一轮。

## 状态文件设计（暂不实施）

当前不优先开发状态文件。续跑以 `record.md` 为准，避免 agent 因为缺少派生状态而被迫从头执行。

状态文件如果未来引入，只做执行约束和派生状态，不存核心建筑语义，不替代 `record.md`。它必须可以从 `record.md`、`inventory.json` 和校验结果重新生成；删除状态文件不应造成任何项目事实丢失。

未来如确实需要，可选格式如下：

```text
projects/{项目代号}/05_output/
  workflow_state.json             # 派生状态：最近一次路由、gate、校验结果；可重建
  skill_runs.jsonl                 # 每次 skill 执行记录，一行一个事件
```

`workflow_state.json` 可选字段：

```yaml
schema_version: "1.0"
project_code: "26-SZ-NSXX"
record_sha1: "..."
inventory_sha1: "..."
last_router_decision:
  selected_skill: "S1_site_analysis"
  reason: "s0_parsed 已完成，且 site.address 存在"
  blocked: false
gates:
  s0_ready: true
  record_valid: true
  marker_writable: "s1_site_analysis"
last_validation:
  command: "python _tools/validate_record.py 26-SZ-NSXX --json"
  fatal: 0
  warn: 2
  checked_at: "2026-05-12T18:00:00+08:00"
```

`skill_runs.jsonl` 可选每行记录：

```json
{"ts":"2026-05-12T18:00:00+08:00","skill":"S0","action":"write","files":["05_output/record.md","05_output/parse_log.md"],"validate_exit":0}
```

这些文件可以由 hook 或轻量工具生成，但当前不开发写入器。Codex 场景下不能假设 Claude Code hooks 存在，所以根 skill 必须只依赖 `record.md` 完成续跑判断。

## 路由表

根 skill 的路由顺序建议从硬 gate 到用户意图，再到 `completeness.ready_for`。

| 用户意图 / 当前状态 | 路由到 | 前置检查 | 阻塞处理 |
| --- | --- | --- | --- |
| 新建项目、初始化骨架 | S0_project_intake 的脚手架流程 | project code 合法、项目不存在或允许 resume | 提示运行 scaffold，不写语义 |
| 已放资料，要求解析/建档 | S0_project_intake | `inventory --require-s0-ready` 通过 | 缺区位图时只输出缺失清单 |
| 要做区位、周边、入口分析 | S1_site_analysis | 有区位图；`site.address` 或 `site.coords` 至少其一 | 缺位置则转 S4 生成待问问题 |
| 要解析地形、红线、DWG | S2_dwg_parse | `02_site/地形图/*.dwg` 或可读红线资料存在 | 缺 DWG 时写 blocked，不伪造面积 |
| 要算面积、功能、强排 | S3_area_and_massing | `brief.summary` 或类型模板关键字段；强排需 `site.area_sqm` | 面积缺失时只做 S3a，并把 S3b 阻塞写清 |
| 要整理甲方问题 | S4_questions_summary | 无硬前置 | 任何阶段可跑，只读各阶段结果 |
| 要写汇报大纲/文档 | S9_report_outline | S1 和 S3 至少有有效正文 | 前置不足时转 S4 或列缺口 |
| 用户没有指定阶段 | `SKILL.md` 根 skill | 读取 `completeness.ready_for` 和 `blocked` | 给出下一步建议，不直接跨阶段写入 |

## 适合 hooks 的规则

hooks 适合做确定性、快速、低争议的约束，不适合做建筑语义判断。

建议先做这些：

- 写入前 hook：禁止 skill 改写非自己 marker 段。
- 写入后 hook：自动运行 `python _tools/validate_record.py {code}`。
- 提交前 hook：检查所有 `projects/*/05_output/record.md` marker 成对、frontmatter 可解析。
- 文件投递 hook：运行 `inventory.py --json`，更新派生 inventory 或提示区位图缺失。
- schema 变更 hook：如果改 `_schema/record.schema.md`，提醒同步 `validate_record.py`、scaffold 和相关 skill prompt。

不建议 hooks 做这些：

- 判断建筑风格是否准确。
- 判断甲方真实意图。
- 自动决定低置信字段。
- 自动补写 `pending_questions.question` 的自然语言内容。
- 自动修改核心 schema 字段。

## 哪些先写 prompt

按 cheat-on-content 的范式，先写 writing plans 和 prompt 契约，再开发工具。当前仓库尤其需要先写以下 prompt：

1. 根 skill router prompt：如何判断项目代号、读取哪些入口、如何选择子 skill、什么时候只给阻塞提示。
2. marker 写入 prompt：统一要求“完整替换自己 marker 内正文，不局部 patch，不跨段写”。
3. pending / low_confidence prompt：明确“无值进入 pending，有值但不确定进入 low_confidence”，附典型建筑场景例子。
4. S1 prompt：区位图、地址、现场照片如何转成区位分析，哪些信息必须标注来源或低置信。
5. S2 prompt：DWG/PDF/红线资料如何区分确定性几何与 agent 语义描述，面积类字段何时可写入 frontmatter。
6. S3 prompt：不同 `project.type` 的面积测算模板、规范依据引用方式、S3a/S3b 阻塞边界。
7. S4 prompt：如何把 pending 问题去重、分组、转成甲方可回答的话术。
8. S9 prompt：汇报大纲结构、只读 S1/S3、不把外部平台字段写回 schema。

Python 工具开发应排在这些 prompt 稳定之后。

## 分阶段实施步骤

### Phase 0：冻结契约与写作计划

- 完成本文件。
- 由主 agent 合并另一个 worker 的交接文档，统一术语：root skill、router、shared references、hooks、state。
- 明确第一轮只新增文档，不移动现有 `S0_project_intake`。

验收：

- `docs/SKILL_SYSTEM_PLAN.md` 能让新 agent 理解重构目标和边界。
- 没有修改现有 schema、skill、脚本。

### Phase 1：写根 skill 和 shared references（已完成第一版）

- 新增 `SKILL.md`。
- 新增 `skills/_shared/*.md` 五个协议文件。
- 根 skill 只路由和约束，不做任何阶段正文写入。
- `AGENTS.md` 增加一行推荐入口，但不改变核心真相原则。

验收：

- 给定“解析新项目”能路由到 S0。
- 给定“整理问题清单”能路由到 S4。
- 根 skill 明确默认不读取 `docs/planning/`。

### Phase 2：补齐子 skill prompt（已完成第一版）

- 新增 S1、S2、S3、S4、S9 的 `SKILL.md`。
- 每个子 skill 包含：目标、输入、硬门槛、允许写入范围、输出格式、校验命令、失败处理。
- S0 只做轻量补充：引用 shared references，避免重复长规则。

验收：

- 每个子 skill 都能说明自己可写 marker。
- 每个子 skill 都引用同一套 pending/low_confidence 规则。
- 不新增未被 schema 支持的 marker。

### Phase 3：暂缓状态文件，先强化 record.md 续跑

- 不急于定义或开发 `workflow_state.json`、`skill_runs.jsonl`、`_tools/workflow_state.py`。
- 根 skill 和 marker 协议已明确：续跑只依赖 `record.md`、marker、`completeness` 和校验结果。
- 后续如确实需要状态文件，只能作为可删除、可重建的辅助投影，不得成为继续工作的前置条件。

验收：

- 删除或缺失任何状态文件后，agent 仍能从 `record.md` 判断已完成阶段并继续。
- `validate_record.py` 仍是核心校验入口。

### Phase 4：hooks

- 先做本地 pre-commit 或 agent 执行前后 hooks 文档。
- 再开发最小 hooks：marker 范围检查、validate_record 自动运行、schema 变更提醒。
- hook 失败必须给出明确修复命令。

验收：

- 跨 marker 修改会被拦截或明确报警。
- record 校验失败不能静默通过。
- hooks 不调用 LLM，不做语义判断。

### Phase 5：回归样例

- 建一个最小测试项目，如 `26-SZ-NSXX`。
- 覆盖三种路径：缺区位图阻塞、S0 成功写入、S4 任意阶段可运行。
- 再增加一个 DWG 缺失但 S3a 可运行的样例。

验收：

- 新 agent 按根 skill 能完成同样路径。
- 所有新增工具和文档都能从自身位置推导仓库根目录。
- `python _tools/selfcheck.py` 和 `python _tools/validate_record.py {code}` 通过。

## 验收标准

- 入口清晰：agent 默认先读 `AGENTS.md`，再用 `SKILL.md` 路由。
- 边界清晰：schema 是字段权威，record 是核心真相，shared references 是协议摘要，状态文件是派生执行状态。
- 阶段清晰：S0/S1/S2/S3/S4/S9 各自只写自己的 marker。
- 工具清晰：Python 只做确定性工作，不做建筑语义理解。
- 失败清晰：缺资料、低置信、schema 失败、marker 越界都有固定处理方式。
- 可回归：至少有一个示例项目能跑通 scaffold、inventory、S0、validate。

## 风险

- 过早移动 S0 文件会破坏现有 `selfcheck.py` 和 AGENTS 快速入口。
- 状态文件如果写入项目语义，会和 `record.md` 竞争真相源。
- hooks 如果过强，会阻碍 agent 在早期探索 prompt。
- 子 skill 如果先写实现、不先写 prompt，会把规则散落到脚本里。
- S3a/S3b 如果急着拆两个 marker，需要同步 schema、validate、scaffold，改动面过大。

## 暂不做事项

- 不接 Notion、Obsidian 或其他外部平台投影。
- 不改 `record.schema.md` 的字段结构。
- 不新增 S5-S8 阶段。
- 不把建筑规范库做成自动判定引擎。
- 不开发 DWG 复杂解析器。
- 不重构 uploader UI。
- 不把 `docs/planning/` 作为当前执行规范。
- 不要求用户文件名完全标准化后才能启动。

## 下一步建议

主 agent 合并交接文档后，先审一次术语和目录命名，再进入 Phase 1。第一批可交付物应是根 skill prompt 和 `_shared` 协议库，而不是脚本改造。
