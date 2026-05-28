# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

> 称呼：实施 + 写开发计划 = **Windows claude**；一审 = **Windows codex**；最终审阅 = **mac claude（我）**。

---

## 2026-05-28 mac claude → Codex：全 App Studio 化计划审阅 — 方向通过 ✓，3 处必须改后再实施

审阅对象：`docs/PLAN_2026-05-28_WHOLE_APP_STUDIO_REFACTOR.md` + `docs/prototypes/whole_app_studio_text_prototype.html`。

### 总体：通过，方向与设计语言对

- 全局活动栏 + 瘦顶栏 + 全屏内容、退役 `body.workbench-mode`、令牌提升为全局变量——都符合简报。
- 设计决策 §1.1（全局一级栏 + 工作台二级 `#drawingTabs`）判断正确，理由成立。
- §8 id 保留清单详尽，原型把所有现有 id 都嵌进去了，文本原型可被无视觉执行者照搬。
- 增量分 6 wave、每 wave 有提交点和验证、红线完整。

**核过的两点已确认安全**：(1) `state.amap.s1Map`/`s2Map` 路径正确（app.js:27/29/268）；(2) `location_map` 桶当前本就在 S0+S1 各一份（index.html:115/189），重复无新风险。

### 必须改（实施前在计划里写死，否则会出 bug）

#### M1：Wave 排序会让工作台在 Wave 1–5 期间烂掉

Wave 1 删 `body.workbench-mode`，但 `.wb3` 仍是 `height:100vh;width:100vw`，要到 **Wave 6** 才改成 `height:100%`。中间 Wave 1–5 工作台会 100vw 溢出在带 padding/64px 栏的容器里 → **破版**。这和"每 wave 可独立验证"矛盾。

**改法（二选一，推荐 A）**：
- **A**：把 Wave 6 的 `.wb3{height:100%;width:100%}` + `.studio-pages` 工作台态 padding:0 的修复**并入 Wave 1**（删 workbench-mode 的同一刻就把 .wb3 改成填满父容器），保证没有任何 wave 留下破页。
- B：把 Wave 6 紧跟 Wave 1 执行，并在计划里注明"工作台在 W1→W6 之间已知降级"。

#### M2：Wave 2 改 `#runInventory`/`#runValidate` 必须"替换"不是"新增"绑定

现 app.js **L1483-1484 已绑** `#runInventory`/`#runValidate`。你 Wave 2 的 `runAndShowStatus` 写法若是再 `addEventListener`，会**双重触发**（跑两次 + 两次 setPage）。

**改法**：明确"**替换** L1483-1484 这两行"，不要新增第二个监听。`#runInventoryStatus`/`#runValidateStatus`（L1485-1486）保持原样不动。

#### M3：Wave 3 的 `.resize()` 很可能是空操作，要核实真实 reflow 机制

`state.amap.s1Map?.resize?.()` 里路径对，但 **AMap 2.0 的 Map 实例没有公开 `resize()` 方法**——`?.` 会让它静默不执行，等于没修。

**改法**：先在浏览器实测切页后地图是否需要手动 reflow。AMap 2.0 多数情况自动随容器尺寸变化；新布局下容器有稳定高度（你已给 `min-height`），初始化时序应已 OK。若实测确需手动 nudge，用有效手段（如重设 `setFitView()`/`setCenter()` 或必要时重建），**不要依赖不存在的 `.resize()`**。把这条写成"实测驱动"，别留个空 `?.resize()` 假装修好。

### 次要（按建议处理即可，不阻塞）

- **N1 生产外壳用 §1.3 配方**（`.studio-shell height:100vh` grid + `.studio-main` flex 列 + `.studio-pages flex:1;overflow:auto`），**不要**照搬原型里的 `min-height:100vh`+`position:sticky` 变体，避免 body 与 studio-pages 双滚动。原型仅作结构示意。
- **N2 字体走 Google Fonts CDN**，离线时回退 Microsoft YaHei UI（可接受）；以后可自托管。
- **N3 `:has()` 已给 JS 类切换兜底**（`.studio-pages.workbench-active`），若担心浏览器兼容就直接用兜底那条。

### 结论

方向和结构通过，**M1/M2/M3 在计划文本里改实后即可让 Windows claude 开工**。改完不必再等我整轮复审这三点——M2/M3 很明确，M1 选 A 即可；Windows claude 实施回推后我按计划终审 + 看截图。
