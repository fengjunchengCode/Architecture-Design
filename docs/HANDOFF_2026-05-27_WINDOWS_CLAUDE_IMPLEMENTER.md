# Handoff — Windows claude 实施会话（2026-05-27）

> **第一件事：读完这份 + 计划正文再动手。** 这份给你身份、背景、批准状态、要实施什么、红线、怎么回审。

---

## 0. 你是谁

你是 **Windows claude**，本项目里负责**写开发计划 + 实施代码**。协作链 3 个角色：

| 角色 | 机器 | 职责 |
|---|---|---|
| **用户** | 两端转推 | 提需求 / 拍板，手动在两台机器间转推 commit |
| **Windows claude（你）** | Windows | 写开发计划 + **实施代码** |
| **Windows codex** | Windows | 一审 |
| **mac claude** | mac | 最终审阅 + 写核心架构/协议/schema 规范 |

机器不互通，没有 agent 间直连——**唯一通道是 git 仓库**。一个改动到落地：你写/实施 → Windows codex 一审 → mac claude 最终 gate。本文件 + review thread 由 mac claude 写给你。

## 1. 项目一句话背景

- **业务**：建筑设计 agent workflow，输入设计任务书 → 输出方案文本 + 一组技术图纸（功能分区、交通分析、消防、竖向等）。
- **测试项目**：`projects/26-BQ-PARK/`（巴青县城西口袋公园，西藏，公园类型）。`style_spec.json` 已审批，底图已上传，用户正在画功能分区草图。
- **通信单一通道**：`docs/CLAUDE_CODEX_REVIEW_THREAD.md`，**每轮覆盖式重写**，历史靠 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

## 2. 本轮批准状态（mac claude 已最终 gate）

**主对象**：`docs/INITIAL_PLAN_2026-05-27_FUNCTIONAL_ZONING_PRECISION_LEGEND_CURVES.md`（你们的完整计划，修订版 commit `467759e`）。

**mac claude 结论（见 review thread）**：**批准实施，decision-complete。**

- **Wave A（不改 schema 的 UI 快修）：直接 GO，零阻塞。** 闭合后默认选中、精细命中三态、图例预览分组、协议 §5 图例规则。
- **Wave B（弧线 schema + UI + 协议）：GO**，但实施时**必须折进下面 2 条收紧**。

## 3. 你要实施什么

完全按 `INITIAL_PLAN_...` 正文做，分两波。**Wave A 先做、回推、过审后再做 Wave B。**

### Wave A（先做）
1. `finishFunctionalZone()` 闭合后 `state.selectedId = id`（计划 A1）。
2. `renderFunctionalZoneSvg()` 命中三态（计划 A2）：绘制态禁旧 hit（别误伤草稿 close handle）；空闲态有边框 stroke-only、无边框有填充 `pointer-events="fill"` 面选、全隐形只列表选。`getZoneHitStrokeWidth` 各向异性按短边/折中换算并写注释。
3. 图例预览 `buildFunctionalZoneLegendGroups()` + `renderFunctionalZoneLegendPreview()`，按可见性归一 key 分组（计划 A3）。
4. 改 `docs/agent_drawing_protocol.md` **§5 图例自动生成**，加"功能分区图例按 `style_hints` 合并"。**不碰 §3.5 marker 标准。**

### Wave B（过审后做）
按计划 B1–B6 实施 `geometry.segments`（schema_version 1.1、segments 权威、coords 16 等分重采样、链连续 + 闭合校验、cubic 预留报错、边级 quadratic 编辑、协议 segments 渲染 + 平滑排除）。

## 4. ⚠️ Wave B 的 2 条收紧（mac claude 在最终审加的，务必折进）

**T1 — `schema_version` 影响面（建议）**：现 `schema.py` line 84 严格校验 `!= "1.0" → raise`。计划写"输出统一写 1.1"会让纯折线旧图也被升版。建议改条件写：`out_version = "1.1" if 任一对象带 segments else "1.0"`；normalize 入口同时接受 `{"1.0","1.1"}`。把版本跳动只落在真用弧线的文件上。若坚持"一律 1.1"，请在完成报告写明这是有意为之。

**T2 — 重采样必须开环（必须）**：现有 `coords` 是开环（polygon 自动闭合，最少 3 点）。重采样组装整环时，**最后一段终点 == `coords[0]`，不要写进 coords**，否则产生零长闭合边的重复点，污染点数校验/形心。重采样产出的 `coords` 必须与手绘 `coords` 同为开环——不含等于首点的尾点。

## 5. 红线（绝对不做）

- ❌ Wave A 阶段不碰 `schema.py` / 不引弧线 / 不动 `traffic_analysis`
- ❌ 不新增 `legend_group` schema 字段（本波从 `style_hints` 派生）
- ❌ 不碰 `agent_drawing_protocol.md` **§3.5 SVG 箭头标准**（已锁；只动 §5 + 加 segments 渲染/平滑排除）
- ❌ Wave B 不实现 cubic（validator 遇 cubic 报明确错）；不独立手改 `coords`（从 segments 重采样且开环）
- ❌ 不用 `transform: scale()` 做缩放（继续 `stage.style.width`）；命中带各向异性是已知取舍
- ❌ 不写 `stroke_width_key` 到新保存的 JSON
- ❌ **不 stage** `projects/26-BQ-PARK/05_output/inventory.json` 与 `projects/26-BQ-PARK/05_output/drawings/semantic/`（测试会写它们，保持未提交）
- ❌ 不删用户本地未跟踪文件；不顺手重构相邻代码

## 6. 验证（每波做）

```powershell
node --check _tools\uploader\static\workbench\workbench.js
git diff --check -- _tools\uploader\static\index.html _tools\uploader\static\workbench\workbench.css _tools\uploader\static\workbench\workbench.js docs\agent_drawing_protocol.md
python _tools\validate_record.py 26-BQ-PARK
# Wave B 另加：
python -m py_compile _tools\drawing_workbench\schema.py
```

浏览器冒烟测试按计划「四」逐项跑（Wave A 8 项 / Wave B 6 项）。

## 7. 回审格式（覆盖 `docs/CLAUDE_CODEX_REVIEW_THREAD.md`）

实施完一波后，覆盖式写一段 `Windows claude → mac claude：<Wave X 实施完成>`，必须含：

1. 实施的是 Wave A 还是 Wave B
2. 改动文件列表
3. 各验收项是否通过（命令 + 浏览器冒烟）
4. 是否产生但未提交的项目输出（应为"已产生、未 stage"）
5. **若 Wave B 另报**：coords 重采样规则（含开环处理 T2）、链连续性校验结果、1.0 旧文件兼容结果、T1 版本号策略选了哪种、§平滑排除是否写入协议

然后提交（**只 stage 代码 + 文档，不 stage 运行产物**）并 push，由用户转推给 mac claude 最终核验。

## 8. 起手

```bash
git pull --rebase origin main
git log --oneline -6
# 读：docs/INITIAL_PLAN_2026-05-27_FUNCTIONAL_ZONING_PRECISION_LEGEND_CURVES.md（主）
#     docs/CLAUDE_CODEX_REVIEW_THREAD.md（mac claude 最终批准 + T1/T2）
#     本文件
# 然后开始 Wave A。
```
