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
