# 设计方案：弧线一步式交互（拖拽边中点圆点直接成弧）

作者：mac claude（核心交互规范）
日期：2026-05-27
对象：`_tools/uploader/static/workbench/workbench.js` + `workbench.css` 功能分区弧线编辑
状态：交给 Windows claude 实施；**并入 Wave B 修订一起做**（与 T1/T2 修复耦合，见末节"实施次序"）

---

## 1. 背景与目标

### 现状（两步交互，麻烦）

选中 polygon 后，每条直线边中点显示**空心菱形** `zone-edge-handle`：

1. **点击**菱形 → `convertSegmentToQuadratic`：边变 quadratic，`control` 初始化到边中点（此时弧线仍是直的，看不出变化）。
2. 出现**实心圆** `zone-control-handle`。
3. **拖动**圆点 → `dragControlHandle`：才真正弯出弧度。
4. 双击圆点 → `convertSegmentToLine` 恢复直线。

→ 要"先点菱形、再拖圆点"两次独立手势，且第 1 步点完没有可见反馈，体验割裂。

### 目标（一步交互）

**取消菱形，把每条边的中点直接做成可拖动的圆点；按住拖一次就成弧。**

- 直线边中点显示一个圆点；**按住并拖动**它 → 该边在同一手势里直接弯成 quadratic 弧线，松手保留。
- 弧线边的圆点 = 它的控制点；继续拖可调弧度。
- 把弧线圆点**拖回贴近原直线**再松手 → 自动恢复直线（无需双击）。
- **纯点击不拖**（按下即松、没有位移）→ 不发生任何转换（保持直线）。

---

## 2. 渲染模型（替换 `renderSegmentHandles`）

每条 segment 只渲染**一个圆点** `zone-arc-handle`（删除菱形 `zone-edge-handle`）：

| segment 状态 | 圆点锚点 | 视觉 | 附加 |
|---|---|---|---|
| `line` | 弦中点 `(from+to)/2` | **空心**（白底 + 描边），提示"此边是直线、可拖出弧" | 无 |
| `quadratic` | 控制点 `seg.control` | **实心**（填 `darkenHex(fill_color)`），提示"此边已是弧" | from→control→to 虚线辅助线（沿用 `renderControlGuide`） |

要点：

- 圆点必须**屏幕恒定**。因 `viewBox="0 0 1 1"` + `preserveAspectRatio="none"`，用 `<ellipse rx=k/stageWidth ry=k/stageHeight>`（沿用 `renderEdgeHandle` 里 `5/stageWidth`、`5/stageHeight` 的写法），不要用 `<circle r>`（现 `renderControlHandle` 用 `circle r` 在 y 方向不恒定，一并修正）。
- 每个圆点带 `data-object-id` + `data-segment-index`。
- 顶点 handle（`renderHandleSvg` 那批白点）保持不变，仍只表示顶点、不可拖（本波不做顶点拖拽）。

---

## 3. 事件模型（重写 `bindOverlaySelection` 里 handle 部分，用 pointer capture）

**用单一指针拖拽手势，替换"菱形 click + 圆点 mousedown/document-mousemove/mouseup + dblclick"。**

> ⚠️ 同时修一个现存泄漏：当前代码给每个 control handle 在 `document` 上挂 `mousemove`/`mouseup`，而 `bindOverlaySelection` 每次 render 都重跑、从不解绑 → document 监听器逐次累积。改用 **handle 自身 + `setPointerCapture`** 后，监听器随每次 render 被替换的元素一起回收，无泄漏。

对每个 `.zone-arc-handle` 绑定（监听器挂在 handle 元素上，不挂 document）：

```
pointerdown(e):
  e.stopPropagation(); e.preventDefault();
  handle.setPointerCapture(e.pointerId);
  pushUndoSnapshot();                 // 整个手势只快照一次
  drag = { objectId, segIndex, moved: false };

pointermove(e):                        // 因 pointer capture，move 路由到本 handle
  if (!drag) return;
  const p = clampUnit(normalizedPoint(e));   // 见 §4，拖到画布外也钳到 [0,1]
  if (!p) return;
  if (!drag.moved && 位移 < START_THRESHOLD) return;   // 见 §4 阈值
  drag.moved = true;
  // 直线边：第一次真正移动时落地转换（T1-safe，见 §5）
  if (该 segment.kind === "line") materializeQuadratic(objectId, segIndex, p);
  else setControl(objectId, segIndex, p);    // 已是 quadratic，直接更新 control
  renderCanvasLayers("arc-drag");

pointerup / pointercancel(e):
  handle.releasePointerCapture(e.pointerId);
  if (drag && 该 segment.kind === "quadratic" && controlNearChord(seg) ) {
     convertSegmentToLine(objectId, segIndex);   // 贴回直线 → 还原；若无弧线剩余则删 segments（§5）
  }
  drag = null;
  markDirty();
```

- 双击恢复直线（`dblclick → convertSegmentToLine`）可**保留为冗余便捷项**，非必需（拖回直线已能还原）。
- 顶点/对象选择的既有绑定（`[data-object-id]:not(.zone-arc-handle)` → `selectObject`、`data-close-zone` → finish）保持。

---

## 4. 阈值与几何

- `START_THRESHOLD`（直线边开始转弧的最小位移）：约 `3px`，按 stage 短边换算成归一单位（`3 / shortSide`）。避免纯点击或微抖动误转弧。
- `controlNearChord(seg)`（松手时判定"是否退回直线"）：控制点到弦 `from–to` 的**垂直距离** < `CHORD_EPS`（约 `4px / shortSide` 归一）。注意距离要在**屏幕像素**意义上判，因 viewBox 各向异性——简单做法：把 from/control/to 用 stage rect 投影回像素再算垂距。
- `clampUnit(p)`：把越界坐标钳到 `[0,1]`，让拖到画布边缘时弧线仍跟随（现 `normalizedPoint` 越界返回 null 会让拖拽"卡住"，体验差）。

---

## 5. 与 T1 不变量的整合（关键，必须一起做）

沿用 Wave B 修订要求的不变量：**polygon 持久化携带 `segments` ⟺ 含至少一条 quadratic（真弧）**。一步交互正好自然落地：

- **`ensureSegments(obj)` 改为不可变**：只为渲染计算并返回全 line 的临时 segments，**不写回 `obj.geometry.segments`**（去掉现 line 1760 的赋值）。渲染 handle 用它即可。
- **`materializeQuadratic(objectId, segIndex, p)`（拖动直线边首次移动时调用）**：这是"真正发生弧"的时刻——
  - 若 `obj.geometry.segments` 不存在 → 用 `ensureSegments` 的全 line 数组**实例化写入** `obj.geometry.segments`（此刻起对象正式带 segments）。
  - 把第 `segIndex` 段 `kind` 设为 `quadratic`，`control = p`。
- **`convertSegmentToLine` 扩展**：把该段还原 `line`、`delete seg.control`；之后若 `obj.geometry.segments` 中**已无任何 quadratic** → `delete obj.geometry.segments`（回到 coords-only）。
- **`buildDrawing`**：持久化 segments 的条件加防御——`segments` 存在**且含 ≥1 个 quadratic**才写；`schema_version` 随之 `1.1`，否则 `1.0`。

效果：选中、拖了又拖回、纯点击都**不会**让纯折线图凭空带上 segments / 升 1.1；只有真留下弧线才 1.1。这同时根治了上一轮 Bug 2（T1 被 `ensureSegments` 选中即写废掉）。

---

## 6. 同批必须一起修的 T1 / T2（来自 Wave B 打回，勿遗漏）

- **T2（开环）**：`sampleSegments`（前端）与 `_sample_segments`（schema.py）必须**丢掉等于首点的尾点**（`coords.slice(0,-1)` / `coords[:-1]`），裁尾后仍保证 ≥3 点。
- **T1（根因）**：即上一节 `ensureSegments` 不可变 + 仅真弧持久化。**不要**用 buildDrawing 粗暴判断绕过根因。

---

## 7. 改动定位

| 文件 | 函数 | 改动 |
|---|---|---|
| `workbench.js` | `renderSegmentHandles` | 每段渲染单一 `zone-arc-handle` 圆点（line 空心@中点 / quad 实心@control + guide）；删菱形 |
| | `renderEdgeHandle` | 删除（并入统一圆点） |
| | `renderControlHandle` | 改成统一圆点渲染，用 `<ellipse rx/ry>` 屏幕恒定 |
| | `bindOverlaySelection` | 重写 handle 事件：`pointerdown`+`setPointerCapture`+`pointermove`/`pointerup` 单手势；**移除 document 级监听（修泄漏）**；保留对象/close 绑定 |
| | `ensureSegments` | 改不可变（只算只返回，不写 obj）—— T1 根因 |
| | 新增 `materializeQuadratic` | 拖动直线边首次移动时实例化 segments + 该段转 quadratic |
| | `convertSegmentToLine` | 还原直线后若无 quadratic 剩余则删 `obj.geometry.segments` |
| | `dragControlHandle` | 保留（设 control），加 `clampUnit` |
| | 新增 `controlNearChord` / `clampUnit` | 阈值与几何（§4） |
| | `buildDrawing` | 持久化 segments 防御：含 ≥1 quadratic 才写 + 版本 |
| | `sampleSegments` | T2 裁尾 |
| `schema.py` | `_sample_segments` | T2 裁尾 |
| `workbench.css` | handle 样式 | 圆点 grab/grabbing 光标、空心/实心两态；删菱形样式 |

**不需要**改 `agent_drawing_protocol.md`（渲染协议 segments→path 不变）。

---

## 8. 验收

交互：

- 选中 polygon → 每条边显示圆点（直线边空心、弧线边实心）。
- 在直线边圆点上**按住拖出** → 同一手势直接成弧，松手保留；其间 from→control→to 虚线辅助线出现。
- 拖弧线边圆点 → 实时调弧度。
- 把弧线圆点**拖回贴近原直线**松手 → 自动恢复直线。
- 纯点击圆点（不拖）→ 无变化。
- 一次拖拽 = 一步 undo（pointerdown 时快照一次）；undo/redo 覆盖成弧 / 调弧 / 还原。

T1/T2 + round-trip 稳定性：

- 纯折线图：选中、点击圆点、拖了又拖回 → save 始终 `1.0`、无 `segments`、coords 开环且点数不增长。
- 含 1 条弧线：save→load→save → `1.1`、`segments` 保留、coords 开环（N-1 直线顶点 + 16×弧段，首尾不重复）、反复存读点数不漂移。
- 把唯一弧线拖回直线后保存 → 退回 `1.0`、无 `segments`。

工程：

- 反复选中/拖拽多次后，`document` 上**无累积监听器**（泄漏已修）。
- 触屏/笔（pointer events）下拖拽同样可用（附带收益）。
- `node --check workbench.js`、`python -m py_compile schema.py`、`validate_record 26-BQ-PARK` 通过。

---

## 9. 红线

- ❌ 不碰 `agent_drawing_protocol.md` §3.5 marker 标准
- ❌ 不实现 cubic
- ❌ T1 从 `ensureSegments` 不可变根因修，不用 buildDrawing band-aid 当唯一手段
- ❌ 本波不做顶点拖拽移动 / 加点删点（独立功能，留后）
- ❌ 不 stage `inventory.json` / `projects/26-BQ-PARK/05_output/drawings/semantic/`；不删用户未跟踪文件
- ❌ 不顺手重构相邻无关代码

---

## 10. 实施次序

Wave B 当前处于打回状态（T1/T2 未落地）。**把本方案与 T1/T2 修复合并为同一个 Wave B 修订 push**，因为它们改的是同一批弧线函数、且一步交互与 T1 不变量耦合。建议顺序：

1. T2 裁尾（前后端 sampleSegments）。
2. `ensureSegments` 改不可变 + `materializeQuadratic` + `convertSegmentToLine` 删空 segments（T1 根因）。
3. 渲染统一圆点 + pointer capture 单手势（本方案主体，顺带修 document 泄漏）。
4. `buildDrawing` 防御 + 版本。
5. round-trip 稳定性检查 + 浏览器冒烟（§8）。

完成后回推 diff，由 mac claude 最终核验。
