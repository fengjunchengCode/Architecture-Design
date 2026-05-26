# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-26 Claude → Codex：Wave Skill-Integration GO（S10 嵌入 + 自动触发）

### 背景

Drawing/Style 协议（`docs/style_spec_negotiation.md`、`docs/agent_drawing_protocol.md`）目前**完全独立**，没挂进 SKILL 工作流，触发方式悬空。用户决定按"方案 A + 自动触发"集成：

- 新建 `skills/S10_technical_drawings/SKILL.md` 作 drawing 工作流的薄路由层
- 现有 skill（S9 / S3）在执行过程中自动 chain 到 S10，不依赖用户主动喊"出图"
- 主 SKILL.md 路由表加 1 行作快速通道兜底
- **不动** `_schema/record.schema.md` / `inventory.json` / validator —— drawing 产物全是文件，状态用文件存在性自证

### 任务清单（codex 实施）

4 个文件改动，全部一次性提交。

---

#### Patch 1：新建 `skills/S10_technical_drawings/SKILL.md`

完整内容如下（直接落盘，不要改动）：

````markdown
---
name: s10-technical-drawings
description: 建筑设计工作流 S10 技术图。用于出方案图、汇报图、PPT 用图、确定项目设计风格、画功能分区/交通组织/消防流线/景观分析/竖向分析等图种时；也是 S9 检测到缺图时被自动 chain 到的下游 skill。本 skill 不写 record.md marker，产物全部为文件。
---

# S10 技术图

## 目标

为项目建立设计风格（`style_spec.json` + `style_card.svg`）和按需出技术图（SVG → PNG/PDF）。本 skill 不写 record.md 任何 marker；全部产物以文件形式存在 `05_output/style/` 和 `05_output/drawings/`。

## 必读

- `SKILL.md`（主）
- 本 SKILL
- `docs/style_spec_negotiation.md` —— 风格 7 阶段协议
- `docs/agent_drawing_protocol.md` —— task_pack 到 SVG 协议
- `docs/reference_pdfs/page_index.json` —— 参考 PDF 同类页索引
- `skills/_shared/development_contract.md`
- 项目 `record.md` 的 `s1_site_analysis` / `s2_dwg_parse` marker（仅作 context）

## 输入

- 项目代号
- 用户当前意图（风格协商 / 出某张图 / 反馈调整 / 被上游 skill chain）
- 现有文件状态：`05_output/style/`、`05_output/drawings/`
- `record.md` frontmatter（`completeness`、`ready_for`）

## 前置条件

| 前置 | 缺失时 |
|---|---|
| S1 marker 有有效正文 | 路由回 S1，"先完成场地分析再出图" |
| 项目至少有一张底图（`05_output/drawings/base/*` 有文件） | 提示用户去工作台上传 |
| `record.md` 存在 | 路由 S0 |

S2（CAD 对齐）**不**作硬前置 —— 出图只依赖底图。

## 入口分流

S10 启动后先扫描项目状态，决定内部分支：

```text
1. 读 05_output/style/style_spec.json
   - 不存在 或 approved_at == null
     → Branch A：style_spec_negotiation.md Stage 0-6
   - approved_at 非空
     → 继续 2

2. 用户意图判断
   - "改风格" / "调风格" / "风格不对"
     → Branch B：style_spec_negotiation.md Stage 6 局部修改
   - "出 {图种}" / "画 {图种}" / "处理 task_pack"
     → Branch C：出图流程
   - "{图种} 的 {元素} 改 X"（具体反馈）
     → Branch D：找现有 SVG 局部 edit
   - 不明确 或 上游 skill chain 进来未指定
     → 问用户接下来要做什么
```

## Branch C 出图流程

1. 读 `05_output/drawings/semantic/{drawing_type}.json` 检查草图
   - 不存在 → 提示用户去工作台画
   - 存在 → 继续
2. 查 `05_output/drawings/task_packs/` 找最新匹配的 task_pack
   - 没有 → 调用 `_tools/drawing_workbench/task_pack.py` 生成
   - 有 → 用最新的
3. 按 `docs/agent_drawing_protocol.md` 执行：读 task.json → style_spec → context → sketch → base → references → 写 SVG
4. 写到 `05_output/drawings/svg/{drawing_type}.svg`
5. 用户预览 → 反馈循环

## 自动触发入口（被其他 skill chain 进来）

S10 不只走用户显式意图，还接受以下自动 chain：

| 上游 | 触发条件 | 期望 S10 行为 |
|---|---|---|
| S9 入口自检 | `svg/` 空 或 `style_spec.json` 未 approved | 至少完成 functional_zoning + traffic_analysis 再回 S9 |
| S3 完成回执 | S3 末尾"下一步建议" | 用户接受后启动 Branch A 或 C |
| 主路由器状态检查 | 用户问"进度 / 下一步"且 S0-S4 已完成 | 报"可启动 S10" |

## 输出范围（允许写入）

- `projects/{code}/05_output/style/style_spec.json`
- `projects/{code}/05_output/style/style_card.svg`
- `projects/{code}/05_output/style/style_card.png`
- `projects/{code}/05_output/style/vibe_board.md`
- `projects/{code}/05_output/style/vibe_board/var_*.png`
- `projects/{code}/05_output/drawings/svg/*.svg`
- `projects/{code}/05_output/drawings/png/*.png`
- `projects/{code}/05_output/drawings/pdf/*.pdf`
- `projects/{code}/05_output/drawings/task_packs/*`（task_pack 生成产物）

## 禁止

- 不在 style_spec 未 approved 时启动 Branch C（真图生产）
- 不用 imagegen 出真技术图（imagegen 仅 vibe_board Stage 2 用）
- 不替用户决定 drawing_type（画哪种图必须用户明确，或上游 skill 明确传入）
- 不改 `record.md`（drawings 状态由文件存在性自证）
- 不在 `ready_for` / `blocked` 数组里塞 S10（不动 schema）
- 不在 S1 marker 缺失时启动
- 不在用户没明确同意时删本地未跟踪文件

## 路由出口

S10 完成后回到调用方：

- 被 S9 chain 进来 → 回 S9 继续大纲撰写
- 用户直接调进来 → 报告产物路径 + 提示后续动作
- 风格协商完成但用户没继续点图 → 提示去工作台画草图

## 校验

```powershell
python _tools/validate_record.py {code}
```

S10 产物不进 record.md，validator 对 S10 透明。如果 validator 报错，说明误改了其他 skill 的 marker，回滚。
````

---

#### Patch 2：主 `SKILL.md` 改两处

**改动 1**：路由表（约 145 行附近）在 S9 行下加一行：

```markdown
| 出技术图、PPT 用图、确定项目设计风格、画功能分区/交通组织/景观/消防/竖向等 | `S10_technical_drawings` | 至少 S1 完成；项目有底图 | 没 style_spec 走风格协商；已 approved 走 task_pack 出图 |
```

**改动 2**：在"最小续跑机制"段（约 132 行附近）末尾增加：

```markdown
### S10 状态补充扫描

agent 报状态时除 `ready_for` / `blocked` 外，扫文件系统判断 drawing 进度：

- `projects/{code}/05_output/style/style_spec.json` 存在且 `approved_at` 非空 → "风格已锁"
- `projects/{code}/05_output/drawings/svg/` 非空 → 列已出图种
- 任一缺 + ready_for 包含 S9 → 建议先转 S10

drawing 状态**不**进 record.md frontmatter，仅作为 agent 报告的辅助信息。
```

---

#### Patch 3：`skills/S9_report_outline/SKILL.md` 入口自检

在 SKILL.md 文档"必读"段后、"输入"段前插入新段落：

```markdown
## 前置自检（技术图）

进入 S9 写大纲前先扫：

1. `projects/{code}/05_output/style/style_spec.json` 是否存在且 `approved_at` 非空
2. `projects/{code}/05_output/drawings/svg/` 是否至少有 `functional_zoning.svg` 和 `traffic_analysis.svg`

任一缺失：

- 不写 `s9_report_outline` marker
- 在对话窗口报"S9 检测到技术图准备不足，先 chain S10 完成必要图种"
- 路由到 S10，附期望清单："至少需要 functional_zoning + traffic_analysis"
- 等 S10 完成后再回 S9 第二次执行（用户重新喊 S9 或 agent 自动回流均可）

二者齐备 → 正常进入 S9 大纲撰写；大纲里引用已生成的 svg/png 路径。
```

---

#### Patch 4：`skills/S3_area_and_massing/SKILL.md` 完成建议

在 SKILL.md 末尾"校验"段前增加：

```markdown
## 完成后建议

S3 marker 写好且 validator 通过后，agent 在对话窗口附一条建议：

> "S3 已完成。下一步建议：S10（确定项目设计风格 + 出技术图）。
>  理由：S3 已落，可进入图面表达阶段。用户可继续做 S4 问题清单或直接进 S10。"

不强制阻塞，用户决定走向。
```

---

### 验证 / 测试场景

4 个 patch 落盘 + commit 后，codex 在 26-BQ-PARK 上跑这 4 个场景验证触发链路：

**场景 1：S9 自动 chain**
```
用户："出 26-BQ-PARK 汇报"
预期：路由 S9 → S9 自检发现 svg/ 空 → chain 到 S10 → 启动 style 协商 Stage 0
```

**场景 2：直接调用**
```
用户："搞 BQ-PARK 风格"
预期：路由表命中 S10 → style 协商 Stage 0
```

**场景 3：状态检查**
```
用户："BQ-PARK 进度"
预期：agent 报已完成 S0-S4 + "drawings 未出，建议 S10"
```

**场景 4：S3 建议（模拟 S3 刚跑完，可手工触发）**
```
用户跑完 S3 或重新调 S3 → S3 末尾建议出现 "下一步建议：S10"
```

4 个场景全部跑通 = 集成成功。

### 回执要求

完成后 codex 在 review thread 贴：

1. commit hash（一个或几个均可）
2. `python _tools/validate_record.py 26-BQ-PARK` 通过证据
3. 4 个测试场景的实际触发结果（文字描述 agent 怎么响应，不要带屏幕截图）
4. 任何路由表 / SKILL 必读路径冲突或异常

### 不要做的事

- ❌ 不动 `_schema/record.schema.md`
- ❌ 不动 `_inventory/inventory.json`
- ❌ 不动 `_tools/validate_record.py`
- ❌ 不动其他 skill 的 marker 写入逻辑
- ❌ 不在 `ready_for` / `blocked` 数组里加 S10
- ❌ 不实现 S5 / S6 / S7 / S8 / S11 等（仅 S10）
- ❌ 不修改两份协议文档 `docs/style_spec_negotiation.md` / `docs/agent_drawing_protocol.md`
- ❌ 不在 smoke / test 时改 BQ-PARK 的 record.md
- ❌ 不在 commit 前清未跟踪文件

### 完成定义

- 4 个 patch 已 commit
- 4 个测试场景实际触发结果已贴 review thread
- 26-BQ-PARK record.md 未被本波改动
- 用户随时能继续推进（譬如说"启动 BQ-PARK 风格协商"）开始真实跑流程

### 开工

直接做 Wave Skill-Integration。
