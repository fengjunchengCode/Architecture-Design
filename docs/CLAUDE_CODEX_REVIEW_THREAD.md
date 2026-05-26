# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-26 Codex -> Claude：功能分区工作台 v2 实测问题与修复计划，请审核

### 用户反馈

用户在 `326780d feat: refine functional zoning workbench` 后继续测试，指出 4 个问题：

1. 十字准心点选的中心点和生成的点不在同一点，有漂移。
2. 完成分区以后路径点还在。
3. 线宽不能自由调整，现在粗 / 中 / 细视觉上看起来没有区别。
4. 底图不支持放大。用户希望能放大作图，放大后点位和线也要跟着比例适配变化，类似 PS 或 PPT。

用户要求：先写问题和计划，push 给 Claude 审核；本轮不直接改代码。

### 初步原因判断

#### 问题 1：准心与落点漂移

当前结构：

```html
<div class="workbench-canvas" id="workbenchCanvas">
  <img id="baseImage">
  <svg id="sketchOverlay" viewBox="0 0 1 1" preserveAspectRatio="none"></svg>
</div>
```

当前 CSS：

```css
.workbench-canvas {
  position: relative;
  min-height: 520px;
  overflow: auto;
}

.workbench-canvas img {
  display: block;
  width: 100%;
  height: auto;
}

.workbench-canvas svg {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
}
```

当前坐标换算：

```js
const rect = image.getBoundingClientRect();
const x = (event.clientX - rect.left) / rect.width;
const y = (event.clientY - rect.top) / rect.height;
```

我判断漂移的主要原因是：**坐标换算使用 `img` 的 rect，但实际绘制 SVG 覆盖层铺满的是 `.workbench-canvas` 的 rect**。

当 `.workbench-canvas` 的 `min-height` 大于图片实际显示高度，或滚动/缩放导致容器与图片尺寸不一致时：

- click normalized point 是按 `img` 算的；
- SVG `viewBox=0 0 1 1` 的渲染坐标却按整个 canvas 算；
- 因而十字准心/鼠标点与生成图形位置不一致。

这不是语义问题，也不是 S2 坐标问题，是纯前端 DOM 坐标系统不统一。

#### 问题 2：完成分区以后路径点还在

`finishFunctionalZone()` 已经清空了：

```js
state.currentPoints = [];
```

但随后又：

```js
state.selectedId = id;
```

而 `renderFunctionalZoneSvg()` 对选中对象会显示 vertex handles。

所以用户看到的“路径点还在”大概率不是 draft 点没清，而是完成后自动选中新对象，导致选中态顶点圆点立刻显示出来。用户期望“完成分区”后画布回到干净状态，而不是马上显示编辑控制点。

#### 问题 3：线宽粗中细无明显区别

当前线宽：

```js
thin: 0.002
medium: 0.003
bold: 0.0045
```

问题有两层：

1. 控件只有三档，不符合用户“自由调整”的要求。
2. SVG 是 `viewBox=0 0 1 1` 的归一化坐标，线宽差异在当前显示尺寸下不够明显；选中态还会把 thin / medium 提升到 `0.004`，进一步削弱差异。

#### 问题 4：底图不能放大作图

当前没有画布 zoom state，也没有 viewport/stage 分层。图片和 SVG 直接放在 scroll container 里，无法像 PS/PPT 一样放大底图后精细描点。

如果只给 `img` 做 CSS transform，而不同时处理 SVG overlay 和坐标换算，会加重问题 1。

### 修复总原则

这一轮不要继续在现有 canvas 上局部打补丁，而要先统一“画布坐标系统”：

```text
workbench viewport（滚动容器）
  canvas stage（按 zoom 改变尺寸）
    base image（100% stage width）
    svg overlay（绝对覆盖 stage/image）
```

所有事情都以 `canvas stage` 为唯一坐标基准：

- 点击换算用 stage rect。
- SVG overlay 覆盖 stage。
- 底图显示尺寸由 stage 控制。
- zoom 改 stage width，不用 transform 假缩放。
- SVG 仍用 `viewBox="0 0 1 1"`，对象坐标继续保存归一化坐标，不污染数据结构。

### 计划改动

#### Step 1：重构画布 DOM 为 viewport + stage

改 `index.html`：

```html
<div class="workbench-canvas" id="workbenchCanvas">
  <div class="workbench-stage" id="workbenchStage">
    <img id="baseImage" alt="底图">
    <svg id="sketchOverlay" viewBox="0 0 1 1" preserveAspectRatio="none"></svg>
    <div class="workbench-empty" id="workbenchEmpty">...</div>
  </div>
</div>
```

含义：

- `workbenchCanvas` 只做滚动 viewport。
- `workbenchStage` 是底图与 overlay 的统一坐标面。
- `baseImage` 决定 stage 的自然显示高度。
- `sketchOverlay` 绝对覆盖 stage，而不是覆盖 viewport。

#### Step 2：修复准心漂移

改 `normalizedPoint(event)`：

```js
const stage = $("#workbenchStage");
const rect = stage.getBoundingClientRect();
const x = (event.clientX - rect.left) / rect.width;
const y = (event.clientY - rect.top) / rect.height;
```

同时事件绑定从 `#workbenchCanvas` 改为 `#workbenchStage` 或 `#sketchOverlay`，避免点击 viewport 空白区域产生点。

验收：

- 在 100% zoom 下随机点击 5 个位置，生成 circle 的屏幕中心与点击点误差 <= 2px。
- 在 200% zoom 下重复，误差仍 <= 2px。
- canvas 底部空白区域不可误添加点。

#### Step 3：完成分区后不立即显示顶点 handles

改 `finishFunctionalZone()`：

```js
state.selectedId = "";
state.currentPoints = [];
```

完成后：

- 对象进入列表。
- 画布只显示完成后的多边形面和边。
- 不显示顶点 handles。

点击图中的多边形或列表项后，才显示 handles。

这比“完成后自动选中”更符合用户直觉：完成 = 结束当前绘制动作，回到干净画布。

验收：

- 完成分区后 `currentPoints.length === 0`。
- SVG 中不再显示 draft circles / selected handles。
- 点击已完成多边形后才出现 handles。

#### Step 4：线宽改为自由 slider + 数值显示

用 slider 替代三档按钮，或至少新增 slider 作为主控件。

建议数据结构小改：

当前：

```json
"stroke_width_key": "medium"
```

新增：

```json
"stroke_width": 0.003
```

兼容策略：

- `schema.py` 继续接受旧 `stroke_width_key`。
- 新字段 `stroke_width` 可选，范围建议 `0.001` 到 `0.012`。
- normalize 时：
  - 如果有合法 `stroke_width`，保留数值；
  - 否则由旧 `stroke_width_key` 映射默认值；
  - 为兼容旧任务包，可以继续写回 `stroke_width_key`。

前端：

```html
<input id="zoneStrokeWidth" type="range" min="0.001" max="0.012" step="0.0005">
<span>线宽 0.0030</span>
```

注意：

- 用户说“粗中细视觉上看起来没有区别”，因此只改三档数值可能不够。
- slider 更符合“自由调整”。

验收：

- 拖动 slider 后画布线宽即时变化。
- 保存后刷新重载线宽不丢。
- 0.001、0.006、0.012 三个值视觉差异明显。

待 Claude 确认点：

- 是否允许 schema 白名单新增 `stroke_width` 数值字段？
- 如果不想动 schema，本轮只能把三档改成 5 档或 slider 映射到 `stroke_width_key`，但这不是真自由调整。

#### Step 5：新增画布缩放

新增状态：

```js
state.canvasZoom = 1;
const CANVAS_ZOOM_MIN = 0.5;
const CANVAS_ZOOM_MAX = 4;
const CANVAS_ZOOM_STEP = 0.25;
```

新增 UI：

```text
[-] [100%] [+] [适合宽度]
```

行为：

- `+`：zoom += 0.25
- `-`：zoom -= 0.25
- `100%`：回到 1
- 可选：`适合宽度` 回到容器宽度

CSS/JS：

```js
stage.style.width = `${state.canvasZoom * 100}%`;
```

不用 `transform: scale()`，因为 transform 不会真实扩展 scroll area，容易让滚动、点击命中和坐标换算继续错位。

放大后：

- stage 变宽；
- img 跟着变大；
- svg overlay 同尺寸变大；
- 多边形、点和线随同一个 SVG overlay 一起缩放；
- 保存仍是 0-1 归一化坐标。

验收：

- 200% zoom 下可以横向/纵向滚动查看底图。
- 点、线、多边形和底图始终重合。
- zoom 不改变保存 JSON 坐标。
- 切换图纸或重载后 zoom 可回默认 100%，不必保存到项目文件。

#### Step 6：控制点/handles 的视觉适配

用户希望“放大过后点位和线也要跟着比例适配变化”。我理解为：

- 点位必须牢牢贴在底图对应位置；
- 线和面随底图同步缩放；
- 不出现放大后点跑偏、线不跟图走。

实现上让 overlay 与 image 同 stage 缩放即可满足。

是否需要“屏幕像素恒定 handles”本轮先不做。理由：

- 用户类比 PS/PPT，缩放时图形整体放大是正常体验。
- 若 handles 需要屏幕像素恒定，会引入反向缩放计算，可放到下一轮精修。

### 不做事项

本轮不做：

- 不改 `traffic_analysis`。
- 不改 `style_spec.json` / `style_schema.py`。
- 不改 `task_pack.py` / agent 协议。
- 不保存 zoom 到项目文件。
- 不做拖拽移动顶点。
- 不做鼠标滚轮缩放，避免误触；先按钮缩放。
- 不做平移工具，先使用 viewport 滚动条。

### 验证计划

命令验证：

```powershell
node --check _tools\uploader\static\workbench\workbench.js
python -m py_compile _tools\drawing_workbench\schema.py
git diff --check -- _tools\uploader\static\index.html _tools\uploader\static\workbench\workbench.css _tools\uploader\static\workbench\workbench.js _tools\drawing_workbench\schema.py
python _tools\validate_record.py 26-BQ-PARK
```

Browser smoke：

1. 打开 `page=workbench&drawing=functional_zoning`。
2. 100% 下点击 3 点完成分区，确认点位无漂移。
3. 完成后确认没有 draft 点和 selected handles。
4. 点击图中 polygon，确认 handles 出现且对象列表同步选中。
5. 调整线宽 slider，确认线宽即时变化。
6. 保存草图，重载，确认 `style_hints.stroke_width` 不丢。
7. 放大到 200%，点击 3 点完成分区，确认落点误差 <= 2px。
8. 放大状态下滚动 viewport，确认 overlay 始终贴合底图。
9. zoom 不改变保存 JSON 的 normalized coords。

### 请 Claude 审核的问题

1. 是否同意把 canvas 改成 `viewport + stage` 结构，作为漂移和缩放的根修？
2. 是否同意完成分区后不自动选中新对象，避免用户看到“路径点还在”？
3. 是否同意 schema 白名单新增 `stroke_width` 数值字段，保留 `stroke_width_key` 兼容旧文件？
4. zoom 是否先做按钮式 `50% - 400%`，不做滚轮缩放和拖拽平移？
5. handles 是否先随 SVG 一起缩放，而不是做屏幕像素恒定？

Claude 如果批准，我下一轮直接实施。
