# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-26 Codex -> Claude：Wave Canvas-Zoom-Fix 已实施，请复核

### 提交范围

已按 `a619d7f` 审核意见实施画布漂移、完成后点残留、自由线宽和缩放修复。

修改文件：

- `_tools/uploader/static/index.html`
- `_tools/uploader/static/workbench/workbench.css`
- `_tools/uploader/static/workbench/workbench.js`
- `_tools/drawing_workbench/schema.py`

未修改：

- `traffic_analysis`
- `style_spec.json`
- `style_schema.py`
- `task_pack.py`
- agent 协议
- `record.md`
- `inventory.json`
- `_schema/record.schema.md`

未提交本地项目产物：

- `projects/26-BQ-PARK/05_output/inventory.json`
- `projects/26-BQ-PARK/05_output/drawings/semantic/`

### 实施内容

#### 1. viewport + stage

画布 DOM 已从“容器即坐标面”改成：

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

- `workbenchCanvas` 是滚动 viewport。
- `workbenchStage` 是底图和 SVG overlay 的统一坐标面。
- `sketchOverlay` 只覆盖 stage，不再覆盖整个 viewport。
- 底图加载成功后 stage 加 `has-image`，去掉空态 min-height；无底图时保留空 stage。

#### 2. 漂移修复

`normalizedPoint()` 改为使用 `#workbenchStage.getBoundingClientRect()`。

点击事件从 `#workbenchCanvas` 改绑到 `#sketchOverlay`：

- 避免点击 viewport 空白区误加点。
- 点击坐标、SVG viewBox、底图显示尺寸使用同一 stage 基准。

#### 3. 完成分区后不自动选中

`finishFunctionalZone()` 现在：

- push object
- 清空 `currentPoints`
- `selectedId = ""`

完成后不会立刻显示 vertex handles。用户点击图中 polygon 或列表项后才进入选中态。

#### 4. stroke_width 数值字段

`schema.py` 新增 `stroke_width` 数值字段：

- 范围：`0.001 <= stroke_width <= 0.012`
- 默认：`0.003`
- 老文件只有 `stroke_width_key` 时会映射：
  - `thin -> 0.002`
  - `medium -> 0.003`
  - `bold -> 0.0045`

弃用路径已按 Claude 要求实现：

- 读入老 `stroke_width_key`
- normalize 输出只写 `stroke_width`
- 新保存文件不会写出 `stroke_width_key`

#### 5. 线宽 slider

功能分区面板中线宽三档按钮已替换为 range slider：

```html
min="0.001"
max="0.012"
step="0.0005"
```

旁边显示当前数值，例如 `0.0120`。

拖动 slider 会即时更新画布 stroke width。

#### 6. zoom toolbar

画布顶部新增缩放工具条：

```text
画布缩放  [−] [100%] [+] [适合宽度]
```

行为：

- zoom 范围：50% 到 400%
- 步长：25%
- `+` / `−` 改 `workbenchStage.style.width`
- `100%` 和 `适合宽度` 都回到 100%
- 切换图纸时重置 100%
- 不保存 zoom 到项目文件
- 不使用 `transform: scale()`

#### 7. handles 屏幕恒定

已按 Claude 反对意见修正。

注意到一个额外细节：因为 SVG 是 `viewBox="0 0 1 1"` + `preserveAspectRatio="none"`，如果继续用 `<circle>`，屏幕上会被底图宽高比压成椭圆。因此我改成了 `<ellipse>`：

- `rx = HANDLE_BASE_R_PX / stageWidth`
- `ry = HANDLE_BASE_R_PX / stageHeight`

这样 handles 在屏幕上保持真正的 12×12px 圆点：

- 100% zoom：12×12px
- 200% zoom：12×12px

绘制内容本身仍随 stage zoom 放大。

### 验证结果

命令验证：

```powershell
node --check _tools\uploader\static\workbench\workbench.js
python -m py_compile _tools\drawing_workbench\schema.py
git diff --check -- _tools\drawing_workbench\schema.py _tools\uploader\static\index.html _tools\uploader\static\workbench\workbench.css _tools\uploader\static\workbench\workbench.js
python _tools\validate_record.py 26-BQ-PARK
```

结果：

- JS 语法通过
- Python 编译通过
- diff check 通过（仅 Git CRLF warning）
- `validate_record.py 26-BQ-PARK` 通过

Schema smoke：

```python
旧 key 输入: {'stroke_width_key': 'bold'}
normalize 输出: {'fill_color': '#DCE8C8', 'fill_enabled': True, 'border_style': 'solid', 'stroke_width': 0.0045}

数值输入: {'stroke_width': 0.011, 'fill_enabled': False, 'border_style': 'dashed', 'fill_color': '#abcdef'}
normalize 输出: {'fill_color': '#ABCDEF', 'fill_enabled': False, 'border_style': 'dashed', 'stroke_width': 0.011}
```

Browser smoke：

1. 打开 `http://127.0.0.1:8765/?project=26-BQ-PARK&page=workbench&drawing=functional_zoning`。
2. 初始 stage 与 overlay 尺寸一致：`544×314.875`。
3. 100% zoom 下点击 3 个点：
   - 点 1 误差：`dx=0.5px, dy=0.36px`
   - 点 2 误差：`dx=0.5px, dy=0.36px`
   - 点 3 误差：`dx=0.5px, dy=0.36px`
4. 完成分区后：
   - `objects=1`
   - `hitZones=1`
   - `ellipses=0`
   - `selectedRows=0`
   - `text labels=0`
5. 点击 polygon 选中后：
   - 100% handles：`12×12px`
   - 200% handles：`12×12px`
   - 200% stage：`1088×629.77`
6. 200% zoom 下画点，handles 仍为 `12×12px`，点位落在预期屏幕坐标。
7. 线宽 slider 设为 `0.012`：
   - UI value：`0.012`
   - UI label：`0.0120`
   - polygon `stroke-width="0.012"`

本轮浏览器验证没有点击“保存草图”，避免写入测试草图污染项目文件。`stroke_width_key` 不写出的行为已由 `schema.py` smoke 和前端 `normalizeZoneStyle()` 输出验证。

### 请 Claude 复核

重点请看：

1. handles 从 `<circle>` 改 `<ellipse>` 是否接受。原因是 `preserveAspectRatio="none"` 下 circle 会被压扁，ellipse 才能保证屏幕圆点。
2. `适合宽度` 当前等同于回到 100%。因为 stage 默认就是适合 viewport 宽度；若未来有“原图像素 100%”概念，可再拆分。
3. slider `input` 事件会记录 undo 快照，50 步上限会保护内存。若你认为拖动中不应每一步入栈，可以下一轮改成 `input` 只预览、`change` 才入栈。

如果复核通过，建议让用户继续实画一张 BQ-PARK 功能分区草图并保存，重点感受准心、缩放、线宽和完成后的画面清爽度。
