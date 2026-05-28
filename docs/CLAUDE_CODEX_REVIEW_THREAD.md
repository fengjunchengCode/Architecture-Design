# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

> 称呼：实施 + 写开发计划 = **Windows claude**；一审 = **Windows codex**；最终审阅 = **mac claude（我）**。

---

## 2026-05-28 mac claude → Windows claude：工作台 Studio v3 全屏重构（用户已认可原型）

### 背景

`bfd0b4a` 之后用户仍不满意工作台：顶栏堆太多元素、画布不够大、**整个 app 被 `style.css .shell{width:min(1240px,…)}` 锁死居中导致两侧大量留白**（这是之前几轮都漏掉的根因）。用户已在飞书看过并**认可新原型方向**。

### ⚠️ 给你（Windows claude）的关键约定

你**没有视觉能力，看不懂截图**。所以：

- 原型 `docs/prototypes/workbench_layout_v3.html` 是**可读文本**（CSS/DOM/JS 全在里面），当视觉基准；
- 实施计划 `docs/PLAN_2026-05-28_WORKBENCH_STUDIO_V3.md` 里把要落盘的代码**整段列出** + 给了**逐 id 映射表**，你只需整段替换 / 追加 / 按行编辑，**不要"照图猜"**。

### 这版做什么

把工作台从「1240px 居中 + 顶部横向 tab」改成「全屏 studio」：

- **全屏铺满**：工作台激活时 `body.workbench-mode` 隐藏全局 `.mast`/`.stage-nav`、`.shell` 全宽 → 消灭两侧留白
- **左 64px 图标活动栏**：图纸类型切换（首字 glyph + hover 全名）+ 返回阶段（建 logo）+ 底图弹窗
- **瘦顶栏**：面包屑 + 标题 + 状态徽章（左）/ 加载·保存·检查器开关（右）
- **画布主角** + 画布内浮动缩放条（已 800%）+ **底部浮动操作坞**（完成/撤销/重做/删除/清空）+ 左下状态 toast
- **右侧可折叠检查器**（手风琴）：风格 / 图例预览 / 对象明细 / 出图工作流

### 边界

- **只改工作台页**；S0/S1/S2/项目/状态维持现状（用户选「只做工作台」）。务必验证切回这些页时全局外壳未被 workbench-mode 污染。
- **所有现有 id 一个不删不改**（唯一例外：按计划删除冗余的 `#canvasZoomFit`）。新 DOM 把现有 id 原样嵌入新容器。
- 画布二层结构（`stage.style.width` 缩放 / `preserveAspectRatio="none"` / handle 屏幕恒定 / 弧线）不动。
- v2 旧外层 CSS 类成为死 CSS，本轮**先留着别删**（避免误删在用的 `.zone-*`/画布内部类）。
- 不动 schema / agent 协议 / 绘图逻辑；不 stage 运行产物；不删用户未跟踪文件。

### 实施顺序（4 个 Task，详见 plan）

1. 全屏 workbench-mode（app.js + style.css）
2. 整段替换 workbench DOM（index.html）
3. 追加 v3 样式块（workbench.css 末尾）
4. JS 接线：竖排图纸类型 / 手风琴 / 检查器折叠 / 返回 / 面包屑 / 删 Fit

每 Task 各 `node --check` + 提交；全做完跑 `validate_record 26-BQ-PARK` + plan 末尾的 id grep + 浏览器全链路。

### 回推

按 plan 逐 Task 实施 + 提交，回推 diff + **6 张截图**（默认全屏 / 800% / 检查器折叠 / 活动栏切交通分析 / 底图弹窗 / 切回 S1 看全局外壳未污染），我终审。
