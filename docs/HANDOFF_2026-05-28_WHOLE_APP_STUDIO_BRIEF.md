# 全 App「Studio 化」重构 — 方向简报（交 codex 写详细设计）

> **这不是详细计划。** mac claude 只定**重构方向 + 设计语言**；**详细设计/实施计划由 codex 编写**，之后 mac claude 只审阅。Windows claude 实施。
>
> 写给 codex：本文件给你方向和约束，请据此产出**逐页详细设计 + 实施计划 + 每页文本原型**。实施者（Windows claude）**无视觉能力**，你的产出必须是可读文本/可粘贴代码 + id 映射，不能依赖截图。

---

## 1. 背景与目标

工作台已完成 studio v3 全屏重构（`c536a99` 等，已上线、用户认可）。现在把**同一套 studio 范式推广到整个 app 的其余页面**：项目 / S0 建档 / S1 区位 / S2 地形 / 状态。

**目标**：消灭"工作台全屏、其余页面还在 1240px 居中横向 tab"的范式割裂，让整个 app 统一为：**全局左侧活动栏 + 瘦顶栏 + 全屏内容区**。

**当前割裂点**（codex 实施时要解决）：
- `style.css .shell{width:min(1240px,…)}` 仍把非工作台页锁死居中、两侧留白。
- 全局导航现在是 `index.html` 顶部横向 `.stage-nav`（项目/S0/S1/S2/图纸/状态）。
- workbench 用 `body.workbench-mode` 临时全屏并隐藏 `.mast`/`.stage-nav`——这是个**过渡方案**，全 app 统一后应由"全局活动栏"取代，不再需要 per-page 的 mode hack。

## 2. 设计语言（以 studio v3 为唯一规范源，照搬，勿另起炉灶）

**规范源文件**（codex 直接读，逐字沿用，别重新发明配色/字体/组件）：
- `docs/prototypes/workbench_layout_v3.html` —— 视觉基准（可读文本）
- `_tools/uploader/static/workbench/workbench.css` 末尾 `WORKBENCH STUDIO v3` 块 —— 落地的 token 与组件样式

要沿用的设计语言要点：
- **气质**：制图工作室（drafting studio）—— 暖纸底 + 蓝图绿 `--accent3:#1f6f5b`、技术精密、克制密致。
- **字体**：IBM Plex Sans SC + IBM Plex Mono（数字/坐标用 mono）。
- **Chrome 模式**：左侧 64px 图标活动栏（图标 + hover tooltip + 选中左缘高亮条）；瘦顶栏（面包屑 + 标题 + 状态徽章 / 右侧动作按钮）；内容区浮动药丸/工具坞；右侧可折叠手风琴检查器；popover 面板；左下 toast。
- **组件**：`.wb3-btn`(primary/ghost/disabled)、徽章 `.wb3-badge`/`.workspace-state`、分段控件、色板 swatch、`.wb3-sect` 手风琴、`.wb3-pop` 弹窗。
- **令牌**：`--line/--panel/--ink/--muted/--accent/--canvas/--grid` 一套暖色 + 圆角 `~9px` + 既有 shadow。

> 推广到全局时，建议把这些 `--*3` 令牌提升为**全局变量**（放 `style.css :root`），让全 app 共用一套，而不是每页各定义。

## 3. 重构方向（codex 在详细设计里要拍定并展开）

骨架方向（codex 细化为具体 DOM/CSS/迁移步骤）：
- **全局左活动栏**取代横向 `.stage-nav`：承载顶层导航（项目 / S0 / S1 / S2 / 图纸 / 状态）。
- **图纸类型**是工作台的二级导航——codex 决定它如何与全局活动栏共存（两级栏？进入"图纸"后活动栏切上下文？还是工作台内部保留二级栏）。给出推荐 + 理由。
- **全屏内容区**：去掉 `.shell` 1240px 限制（全局），每页内容在全宽区域内自适应（表单页可保留舒适的内容最大宽度，但容器本身全屏）。
- **瘦顶栏全局化**：面包屑（项目名 + 当前阶段）+ 阶段标题 + 状态/动作。
- 退役 `body.workbench-mode` 过渡 hack，统一为全局 studio 外壳。

## 4. 逐页要覆盖（codex 详细设计必须逐页给）

每页都要给：新 DOM 结构（嵌入现有 id）、套用的 studio 组件、与现有 JS 逻辑的对接、id/事件保留清单、文本原型。

- **项目页**：创建/选择项目（列表 + 表单）。
- **S0 建档**：资料投递 / 准入（文件桶 buckets）。
- **S1 区位**：**含高德地图**（`#s1AmapMap` 等），地图容器在全屏布局下的尺寸/初始化时序是重点。
- **S2 地形**：**含高德地图 + DWG/控制点**，同样注意地图 + 表格在全宽下的布局。
- **状态页**：Inventory / Validate，`result-panel`（`#output`/`#resultHint`）归位到状态页内部（工作台已用 CSS 隐藏它，全局统一后应让它只属于状态页）。
- **工作台**：已是 studio v3，作为参考基准，**本轮不回退**；只在"全局活动栏取代 workbench-mode hack"这点上做收口。

## 5. 约束 / 红线（codex 必须在计划里复述并遵守）

- **保留所有现有 id 和事件绑定**（app.js 靠 id 取元素 + `[data-page].stage-tab` 绑导航）；只搬位置/容器 + 调样式。
- **高德地图**：不改地图业务逻辑，只解决容器布局与 resize/初始化时序。
- **增量迁移**：一页一 wave，可独立验证、独立回退；不要一次大爆炸。
- 不动 schema / agent 协议 / 绘图逻辑 / record / validator。
- 不 stage 运行产物；不删用户未跟踪文件。
- 工作台 studio v3 不可回退。

## 6. codex 产出物要求

1. **逐页文本原型**（HTML，放 `docs/prototypes/`），因为实施者无视觉能力。
2. **详细实施计划**（`docs/PLAN_*.md`）：bite-size 任务、每任务给可粘贴代码 + id 映射表 + `node --check`/`validate_record`/浏览器自验 + 提交点。
3. **迁移顺序建议**（哪页先做、依赖关系）。
4. **待决设计问题的明确答案 + 理由**（见 §3 的二级导航等）。

## 7. 流程

codex 按本简报写详细设计/计划并提交 → **mac claude 只审阅**（不制定）→ 通过后 Windows claude 逐 wave 实施。
