# _schema/record.schema.md · 真相文件字段权威定义

<aside>
🎯

**定位**：这是 `record.md` 的**字段宪法**。所有 skill 在读写 [record.md](http://record.md) 前必须遵循本文档定义的字段名、类型、必填规则、`brief` 类型模板。新增字段先改这里，再改实现。

**版本**：schema_version `1.0`

**配套文档**：`_schema/folder.convention.md`、`AGENTS.md`、`skills/S0_project_intake/SKILL.md`

</aside>

## 一、设计原则（强约束 vs 软约束）

<aside>
🦴

**通用骨架 = 强约束**

`project` / `site` / `style_preferences` / `pending_questions` / `low_confidence_fields` / `completeness` / `files_indexed` —— 字段名、类型固定，所有项目都一样。

</aside>

<aside>
🧩

**`brief` = 软约束**

按 `project.type` 加载推荐字段模板（见第三节）。抽不到 → 进 `pending_questions`。**绝不报错、绝不阻塞**。

</aside>

<aside>
⚠️

**只有 3 个字段是真正必填**：`schema_version` / `project.code` / `project.name`。其他全部允许 `null` 或缺失。

</aside>

## 二、通用骨架字段定义

### 2.1 顶层 `schema_version`

| **字段** | **类型** | **必填** | **说明** |
| --- | --- | --- | --- |
| `schema_version` | string | ✅ | 当前固定 `"1.0"`。升版本时 agent 自动跑迁移脚本 |

### 2.2 `project`（项目元信息）

| **字段** | **类型** | **必填** | **说明 / 取值** |
| --- | --- | --- | --- |
| `project.code` | string | ✅ | 主键，= `projects/{code}` 项目文件夹名。格式 `{YY}-{CITY2_3}-{ABBR}`，如 `26-SZ-NSXX` |
| `project.name` | string | ✅ | 工作名即可，可与正式名不同 |
| `project.client` | string | null | — | 甲方名称 |
| `project.type` | enum | null | — | 见第三节 11 种类型；未确定填 `"unknown"` |
| `project.scale` | string | null | — | 一句话描述规模，如 "新建公立小学 36 班" |
| `project.stage` | enum | null | — | `待放置文件` / `需求确认` / `强排` / `CAD` / `SU` / `渲染` / `汇报` / `已交付` |
| `project.updated_at` | ISO datetime | 自动 | 每次 skill 写入时由 agent 自动更新 |

#### 项目代号格式规范

```jsx
{YY}-{CITY2_3}-{ABBR}
  YY    = 年份后两位（项目立项年），例：26
  CITY2_3 = 城市 2-3 位字母代码（汉语拼音首字母），例：SZ / BJ / SH / GZ
  ABBR  = 项目简称（2-6 字母），例：NSXX（南山小学）
例：26-SZ-NSXX / 26-BJ-LFGY（朝阳某公园）/ 26-SZ-JJ（街角）
```

### 2.3 `site`（场地约束）

<aside>
📍

**核心理念**：场地是「物理事实」，所有项目都有；但具体数值可能未知（待 DWG 解析、待甲方提供红线图等）—— 全部允许 null。

</aside>

| **字段** | **类型** | **说明** | **来源 skill** |
| --- | --- | --- | --- |
| `site.address` | string | null | 项目地址（文字） | S0 抽 brief 或 S0 反查区位图 |
| `site.coords` | [lng, lat] | null | WGS84 经纬度 | S0 高德反查 |
| `site.area_sqm` | number | null | 地块面积 (㎡) | **S2 DWG 解析**（S0 不算） |
| `site.far_max` | number | null | 容积率上限 | S0 抽 brief |
| `site.height_limit_m` | number | null | 限高 (m) | S0 抽 brief |
| `site.setback` | string | null | 退线要求（自由文本，含多向退线） | S0 抽 brief |
| `site.has_elevation_diff` | boolean | null | 是否有显著高差 | S2 DWG 解析（S0 不判断） |
| `site.boundary_shape` | enum | null | `规则矩形` / `L形` / `异形` / `狭长` / 等 | S2 DWG 解析 |

### 2.4 `style_preferences`（风格偏好）

| **字段** | **类型** | **说明** |
| --- | --- | --- |
| `style_preferences.keywords` | string[] | null | 风格关键词，如 `["现代", "活力", "儿童尺度"]` |
| `style_preferences.references` | string[] | null | 参考案例文件名清单（来自 `03_references/`） |
| `style_preferences.client_raw_quotes` | string[] | null | 甲方原话片段（沟通记录摘取），供 S9 写作引用 |

### 2.5 `pending_questions`（一等公民 —— 待问甲方/待人工补的字段）

<aside>
❓

**这是渐进信息流的核心**。字段抽取不阻塞，所有抽不到的字段全部进这里；文件准入由 `_schema/folder.convention.md` 的 gate 控制。

</aside>

```yaml
pending_questions:
  - id: q001                      # 字符串，q + 三位序号；同项目内唯一
    field: site.area_sqm          # 关联的 YAML 字段路径（dot notation）
    question: "地块面积请提供 DWG 或文字描述"
    raised_by: S0                 # 谁提的：S0/S1/S2/S3/.../用户
    status: 待问                  # 待问 / 已问 / 已答 / 已归档
    answer: null                  # 甲方回复（已答后填）
    answered_at: null             # ISO datetime
```

| **子字段** | **类型** | **必填** | **说明** |
| --- | --- | --- | --- |
| `id` | string | ✅ | `q{NNN}` 项目内唯一 |
| `field` | string | null | — | 关联的 YAML 字段路径，便于答复后自动 patch 回去；非字段类问题可 null |
| `question` | string | ✅ | 给甲方看的提问（LLM 已润色） |
| `raised_by` | enum | ✅ | `S0` / `S1` / `S2` / `S3` / `S4` / `S9` / `用户` |
| `status` | enum | ✅ | `待问` / `已问` / `已答` / `已归档` |
| `answer` | string | null | — | 甲方回复原文（status=已答 后填） |
| `answered_at` | ISO datetime | null | — | — |

### 2.6 `low_confidence_fields`（低置信字段标记）

```yaml
low_confidence_fields:
  - field: site.address           # 字段路径
    reason: "仅从区位图 OCR 反查，建议人工复核"
```

**与 `pending_questions` 的区别**：

- `pending_questions` = **没有值**，要问甲方
- `low_confidence_fields` = **已经填了值，但不确定**，要人工/下游 skill 复核

### 2.7 `completeness`（完成度健康度）

<aside>
📊

**作用**：动态计算「当前 [record.md](http://record.md) 能解锁哪些下游 skill」。每个 skill 启动前先读这个，并在本地展示为进度与阻塞清单。

</aside>

```yaml
completeness:
  filled_required_pct: 60                           # 0-100，骨架字段填充率
  ready_for: [S4]                                   # 可立即跑的 skill 列表
  blocked:
    - { skill: S1, reason: "site.address 待人工确认" }
    - { skill: S3, reason: "brief 信息不足，需补 budget" }
```

#### 各 skill 的解锁条件（建议默认值，可在 skill 实现里覆盖）

| **Skill** | **必要前置字段** | **可选但建议** |
| --- | --- | --- |
| S0 项目档案初始化 | `02_site/区位图/` 至少 1 张 | `01_briefing/brief.*`、`04_chat/*` |
| S1 区位分析 | `02_site/区位图/` 至少 1 张；`site.address` 或 `site.coords` 至少其一 | `02_site/现场照片/` |
| S2 DWG 解析 | `02_site/地形图/*.dwg` 文件存在 | — |
| S3a 面积需求测算 | `brief.summary`  • 至少 1 项功能数据（按 type 模板） | `site.far_max` |
| S3b 容积率/强排校核 | `site.area_sqm` | `site.far_max` |
| S4 问题清单 | 无（任何阶段都能跑） | — |
| S9 汇报文档 | `s1_site_analysis`  • `s3_area_calc` 段已写 | `style_preferences.references` ≥ 1 |

### 2.8 `files_indexed`（文件指纹表）

```yaml
files_indexed:
  - path: 01_briefing/brief.docx
    sha1: "abc123..."
    parsed_at: 2026-05-12T09:30:00+08:00
    parsed_by: S0
```

**用途**：增量解析判断 —— S0 重跑时跳过已解析且 hash 未变的文件。

## 三、`brief` 类型模板库（软约束）

<aside>
🧩

**用法**：S0 / S3 解析 brief 时，根据 `project.type` 加载对应模板，**优先尝试抽取模板中的字段**；抽不到 → 进 `pending_questions`。模板字段全部 optional，绝不报错。

</aside>

### 3.0 通用 brief 字段（所有 type 共享）

| **字段** | **类型** | **说明** |
| --- | --- | --- |
| `brief.summary` | string | **推荐必填**。一句话项目目标；信息严重不足时也至少写一句 |
| `brief.budget` | string | null | 预算（可定性，如 "低/中/高" 或定量 "800 万"） |
| `brief.budget_level` | enum | null | `低` / `中` / `高` —— 街角/景观等定性场景用 |
| `brief.deadline` | ISO date | null | 汇报截止日期 |
| `brief.special_constraints` | string[] | null | 甲方特殊要求清单 |

### 3.1 类型模板对照表

| **`project.type`** | **推荐字段（agent 优先抽）** | **典型 pending_questions** |
| --- | --- | --- |
| `school` | `user_count: {students, staff}` · `programs[]: {name, count, area_per_unit_sqm}` · `special_facilities[]`（食堂/宿舍/报告厅）· `class_count` | 学生人数？班级数？是否含食堂宿舍？ |
| `residential` | `total_units` · `unit_types[]: {type, area_sqm, ratio_pct}` · `amenities[]` · `parking_ratio` | 总户数？户型配比？配套？ |
| `commercial` | `retail_mix[]` · `office_area_sqm` · `parking_ratio` · `anchor_tenants[]` | 业态构成？车位比？主力店？ |
| `park` | `functional_zones[]: {name, area_sqm, intent}` · `vegetation_strategy` · `paving` · `facilities[]` · `target_visitor_flow` | 主要功能分区？预算等级？乔木策略？ |
| `street_scape` | `existing_situation` · `target_state` · `immutable_elements[]`（古树/管线/历史构件）· `budget_level` | 现状问题？改造目标？不可动元素？ |
| `renovation` | `existing_type` · `existing_problems[]` · `preservation_requirements[]` · `structural_constraints` | 现状问题？保留要求？结构约束？ |
| `hospital` | `beds` · `departments[]` · `programs[]` · `flow_separation`（医患分流要求） | 床位数？科室构成？分流要求？ |
| `cultural` | `audience_capacity` · `collection`（藏品概述）· `programs[]` · `acoustics_requirement` | 容纳人数？藏品规模？声学要求？ |
| `industrial` | `production_lines[]` · `cargo_flow` · `net_height_m` · `load_requirement` | 工艺？物流？净高？荷载？ |
| `cultural_tourism` | `nodes[]: {name, function}` · `visitor_flow` · `hero_features[]` · `phasing` | 主要节点？预期客流？分期？ |
| `unknown` | 仅 `summary` | 类型未确定 / 信息严重不足兜底 |

### 3.2 类型模板：完整 YAML 示例

#### school

```yaml
brief:
  summary: "南山区新建 36 班公立小学，约 1800 学生"
  user_count: { students: 1800, staff: 120 }
  class_count: 36
  programs:
    - { name: "普通教室", count: 36, area_per_unit_sqm: 70 }
    - { name: "实验室", count: 6, area_per_unit_sqm: 96 }
    - { name: "专用教室", count: 12, area_per_unit_sqm: 70 }
  special_facilities: ["报告厅 400 座", "食堂", "风雨操场", "宿舍 6 班"]
```

#### park

```yaml
brief:
  summary: "朝阳区 1.5 公顷社区公园，主题为城市绿洲"
  functional_zones:
    - { name: "入口广场", area_sqm: 800, intent: "集散+标识" }
    - { name: "儿童活动区", area_sqm: 1200, intent: "3-12 岁分龄" }
    - { name: "林荫休闲区", area_sqm: 6000, intent: "乔木+座椅" }
  vegetation_strategy: "以本土乔木为骨架，地被以耐旱多年生草本为主"
  paving: "透水砖 + 木栈道"
  facilities: ["公共厕所", "管理用房", "无障碍坡道"]
  budget_level: 中
```

#### street_scape（极简启动示例）

```yaml
brief:
  summary: "甲方希望把街角改造成市民休憩空间，其他全部待定"
  # 以下全部进 pending_questions 等甲方回复
pending_questions:
  - { id: q001, field: site.area_sqm,         question: "用地范围请提供红线图或文字", raised_by: S0, status: 待问 }
  - { id: q002, field: brief.budget_level,    question: "预算等级（低/中/高）？",       raised_by: S0, status: 待问 }
  - { id: q003, field: brief.target_state,    question: "希望解决的问题或达到的目标？",  raised_by: S0, status: 待问 }
  - { id: q004, field: brief.immutable_elements, question: "现状不可动元素（古树/管线/...）？", raised_by: S0, status: 待问 }
completeness:
  filled_required_pct: 15
  ready_for: []
  blocked:
    - { skill: ALL, reason: "信息严重不足，先发 pending_questions 给甲方收答复" }
```

### 3.3 新增 type 的流程

1. 在第 3.1 节表格加一行
2. 在第 3.2 节补一个完整 YAML 示例
3. 同步更新 `_schema/folder.convention.md`（如该 type 有特殊文件夹要求）
4. 同步更新 S0 prompt（让它认识新 type）
5. 升 `schema_version`（minor 升级，如 `1.0` → `1.1`）

## 四、Markdown body 章节 marker 规范

<aside>
📌

**铁律**：每个 skill 只能重写自己 marker 之间的内容，不得跨段写。重跑幂等。

</aside>

### 4.1 完整 marker 列表

```markdown
<!-- BEGIN:s0_parsed -->
... S0 写：抽取摘要、文件清单、⚠️ 字段说明、引用甲方原话 ...
<!-- END:s0_parsed -->

<!-- BEGIN:s1_site_analysis -->
... S1 写：周边路网描述、500m/1000m 业态、主次入口建议、高德地图截图引用 ...
<!-- END:s1_site_analysis -->

<!-- BEGIN:s2_dwg_parse -->
... S2 写：地块几何参数表、边界点坐标、形状语义、高差描述 ...
<!-- END:s2_dwg_parse -->

<!-- BEGIN:s3_area_calc -->
... S3 写：面积需求测算表、规范依据；如已知 site.area_sqm，再写容积率/强排校核 ...
<!-- END:s3_area_calc -->

<!-- BEGIN:s4_questions_summary -->
... S4 写：当前未答问题分类汇总、提问话术草稿 ...
<!-- END:s4_questions_summary -->

<!-- BEGIN:s9_report_outline -->
... S9 写：6 段汇报文档大纲（仅大纲，正文在 05_output/汇报文档.md）...
<!-- END:s9_report_outline -->
```

### 4.2 写入规则

- marker 标签**永远成对存在**，即使内容为空也保留占位（S0 脚手架阶段写入）
- 占位时段内容 = `_pending: 等 S{N} 写入_`
- agent 重写自己段时，必须完整替换 `BEGIN ... END` 之间所有内容（不能局部 patch）
- 跨段引用：S9 读 s1/s3 段时**只读不写**

## 五、字段验证规则

<aside>
🔒

每次 skill 写入后跑一次校验，失败则报错并 git 不提交。

</aside>

### 5.1 硬规则（违反则 reject）

1. `schema_version` 必须等于 `"1.0"`
2. `project.code` 必须匹配正则 `^\d{2}-[A-Z]{2,3}-[A-Za-z0-9]{2,8}$`
3. `project.code` 必须等于 `record.md` 所属项目根目录名，即 `projects/{code}`
4. `project.name` 不能为空字符串
5. `pending_questions[].id` 项目内唯一
6. 所有 marker 必须刚好成对出现

### 5.2 软规则（仅 warning，不阻塞）

- `brief.summary` 缺失 → warning（推荐必填）
- `project.type` = `unknown` → warning（建议尽快确定）
- `low_confidence_fields` 数量 > 5 → warning（建议人工集中复核）
- `pending_questions[].status = 待问` 超过 7 天 → warning（甲方沟通滞后）

## 六、版本演进策略

| **版本变化** | **触发条件** | **迁移** |
| --- | --- | --- |
| patch（1.0 → 1.0.1） | 仅文档/注释/示例修改 | 无需迁移 |
| minor（1.0 → 1.1） | 新增 optional 字段 / 新增 type 模板 | 老 [record.md](http://record.md) 自动兼容 |
| major（1.0 → 2.0） | 修改 / 删除字段 / 改字段类型 | 跑 `_tools/migrate_schema.py`，每个项目 git diff 审查 |

## 七、完整 YAML 参考（school 示例，所有骨架字段都填）

```yaml
---
schema_version: "1.0"
project:
  code: "26-SZ-NSXX"
  name: "深圳南山某小学"
  client: "南山区教育局"
  type: "school"
  scale: "新建公立小学，36 班"
  stage: "需求确认"
  updated_at: 2026-05-12T10:30:00+08:00
site:
  address: "深圳市南山区学府路与文心二路交口"
  coords: [113.9341, 22.5396]
  area_sqm: null                  # 留给 S2
  far_max: 1.2
  height_limit_m: 24
  setback: "北退道路红线 5m，东退用地红线 3m"
  has_elevation_diff: null
  boundary_shape: null
style_preferences:
  keywords: ["现代", "活力", "儿童尺度"]
  references: ["case_A_嘉里小学.jpg", "case_B_深外香蜜.jpg"]
  client_raw_quotes:
    - "希望像嘉里小学那样的感觉"
    - "避免大体量呆板"
brief:
  summary: "南山区新建 36 班公立小学，约 1800 学生"
  budget: "约 2.4 亿"
  deadline: 2026-08-15
  user_count: { students: 1800, staff: 120 }
  class_count: 36
  programs:
    - { name: "普通教室", count: 36, area_per_unit_sqm: 70 }
    - { name: "实验室", count: 6, area_per_unit_sqm: 96 }
    - { name: "专用教室", count: 12, area_per_unit_sqm: 70 }
  special_facilities: ["报告厅 400 座", "食堂", "风雨操场", "宿舍 6 班"]
  special_constraints: ["地下不可设教学空间", "宿舍需独立分区"]
pending_questions:
  - id: q001
    field: site.area_sqm
    question: "地块面积请提供 DWG 或文字描述"
    raised_by: S0
    status: 待问
    answer: null
    answered_at: null
low_confidence_fields:
  - field: site.address
    reason: "仅从区位图 OCR 反查，建议人工核对门牌"
completeness:
  filled_required_pct: 65
  ready_for: [S4]
  blocked:
    - { skill: S1, reason: "site.address 待人工确认" }
    - { skill: S2, reason: "02_site/地形图/ 无 DWG 文件" }
    - { skill: S3, reason: "site.area_sqm 未知，无法核算容积率" }
files_indexed:
  - path: 01_briefing/brief.docx
    sha1: "abc123def456..."
    parsed_at: 2026-05-12T09:30:00+08:00
    parsed_by: S0
  - path: 02_site/区位图/location_1km.png
    sha1: "def456abc789..."
    parsed_at: 2026-05-12T09:32:00+08:00
    parsed_by: S0
---

# 项目档案：26-SZ-NSXX 深圳南山某小学

<!-- BEGIN:s0_parsed -->
## 自动解析摘要（S0）
agent 写入摘要 ...
<!-- END:s0_parsed -->

<!-- BEGIN:s1_site_analysis -->
_pending: 等 S1 写入_
<!-- END:s1_site_analysis -->

<!-- BEGIN:s2_dwg_parse -->
_pending: 等 S2 写入_
<!-- END:s2_dwg_parse -->

<!-- BEGIN:s3_area_calc -->
_pending: 等 S3 写入_
<!-- END:s3_area_calc -->

<!-- BEGIN:s4_questions_summary -->
_pending: 等 S4 写入_
<!-- END:s4_questions_summary -->

<!-- BEGIN:s9_report_outline -->
_pending: 等 S9 写入_
<!-- END:s9_report_outline -->
```

---

<aside>
🔗

**配套文件**（仓库内）：

- `_schema/folder.convention.md` —— 文件夹命名 + 投递助手必填项配置（下一步创建）
- `CLAUDE.md` —— Claude Code 系统提示，让 agent 启动时自动 load 本 schema（下一步创建）
- `_tools/validate_record.py` —— 字段验证脚本实现（MVP 后写）
- `_tools/migrate_schema.py` —— 跨版本迁移脚本（major 升级时写）
</aside>
