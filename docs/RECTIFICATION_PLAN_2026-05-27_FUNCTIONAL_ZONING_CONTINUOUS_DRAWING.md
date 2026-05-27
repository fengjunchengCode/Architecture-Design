# 整改计划：Functional-Zoning Continuous-Drawing Fix

日期：2026-05-27
项目：`26-BQ-PARK`
依据交接文档：`docs/HANDOFF_2026-05-27_FUNCTIONAL_ZONING_CONTINUOUS_DRAWING.md`
审查线程：`docs/CLAUDE_CODEX_REVIEW_THREAD.md`（commit `1a7fc25`）

---

## 一、问题清单

用户在 commit `0c7d1a6` 之后报告 5 个问题：

| # | 问题 | 根因 |
|---|------|------|
| 1 | 多边形只能通过点击"完成分区"按钮闭合 | 画布内无闭合手势，dblclick 不可靠 |
| 2 | 完成一个对象后，下一个对象不继承颜色/边框/填充/线宽 | `updateZoneStyle()` 不同步 draft；`addPoint()` 清 selectedId 但未复制 style |
| 3 | 鼠标滚轮不能缩放底图 | 没有 wheel handler |
| 4 | 保存草图后切走再切回，对象列表存在但画布空白 | tab 切回、loadDrawing、image.onload、loadStyle、renderObjects 的重绘时序不稳定；当前有 cache-buster，缓存命中不是主根因，但仍保留 ready guard 做防御 |
| 5 | 调色板自定义颜色不被记住 | 无 recent colors 体系 |

---

## 二、整改范围

### 涉及文件（预计）

| 文件 | 改动类型 |
|------|----------|
| `_tools/uploader/static/workbench/workbench.js` | 主要改动 |
| `_tools/uploader/static/workbench/workbench.css` | 样式补充 |
| `_tools/uploader/static/index.html` | 可能微调 |

### 不涉及

- `schema.py`、`traffic_analysis`、`style_spec.json`、`agent_drawing_protocol.md`
- `record.md`、`inventory.json`、`projects/26-BQ-PARK/05_output/drawings/semantic/`
- 后端 API
- 顶点拖拽编辑

---

## 三、整改步骤

### Step 1：画布内闭合多边形（解决问题 1）

**目标**：用户可通过点击首点或按 Enter 闭合多边形，不再依赖按钮。

**实现要点**：

1. 当 `state.currentPoints.length >= 3` 时，将第一个草稿点渲染为闭合手柄（close handle）：
   - 内圆填充当前 `fill_color`
   - 外圈 2px 深色描边，视觉上与普通顶点区分
   - hover 时显示 `cursor: pointer` + 微弱光晕
2. 闭合手柄命中区域 ≥ 10px 半径（普通 handle 为 6px）：
   - 添加透明 `.zone-close-hit` 椭圆，`pointer-events="all"`
   - click handler 调用 `stopPropagation()` + `finishFunctionalZone()`
   - 不得添加额外点
3. 使用屏幕常量椭圆函数（沿用上一波 handle 的做法），适配 `viewBox="0 0 1 1"` + `preserveAspectRatio="none"`
4. `Enter` 快捷键：功能分区激活且 `currentPoints.length >= 3` 时完成多边形；input/textarea/select/contenteditable 聚焦时不拦截
5. 保留"完成分区"按钮作为兜底
6. 现有 dblclick 可保留但不依赖，闭合时避免重复添加点

**Esc 行为**：

- 有草稿点 → 清空 `state.currentPoints` + 重绘
- 无草稿点但有选中对象 → 清除 `selectedId`
- 文本输入框聚焦时不拦截

**Delete / Backspace 行为**：

- 有选中对象且焦点不在 input 时 → 直接复用 `deleteSelected()` 删除选中对象
- `deleteSelected()` 已写入 undo stack，键盘删除必须可被 `Ctrl/Cmd + Z` 撤回
- 阻止 Backspace 触发浏览器后退

**验收标准**：

- 画 3 点后，首点出现视觉变化（光晕/指针），点击 ≤10px 偏差内可闭合
- 闭合后无重复点，草稿手柄消失
- Enter 可闭合，Esc 可取消草稿
- Delete 可删除选中对象

---

### Step 2：连续绘制样式继承（解决问题 2）

**目标**：完成一个区域后，下一个区域自动继承上一个的颜色、边框、填充、线宽。

**实现要点**：

1. 定义 `state.zoneDraftStyle`，存储下一新建区域的默认样式
2. 仅继承 4 个字段：`fill_color`、`fill_enabled`、`border_style`、`stroke_width`
3. 不继承：label、confidence、source

**同步规则**：

| 场景 | 行为 |
|------|------|
| `finishFunctionalZone()` | 使用 `normalizeZoneStyle(state.zoneDraftStyle)`；完成后保留 `state.zoneDraftStyle = object.style_hints`；清空 `state.zoneDraftLabel`；不自动选中完成的对象 |
| `updateZoneStyle()` 有选中对象 | 更新选中对象 + 同步 `state.zoneDraftStyle = next` |
| `addPoint()` 开始新多边形且有选中对象 | 先复制 selected 的 `style_hints` 到 `zoneDraftStyle`，再清 `selectedId`，再添加点 |
| 纯选择（select）不编辑再 deselect | **不改** `zoneDraftStyle` |

**验收标准**：

- 创建自定义颜色/虚线边框/线宽 0.009 的区域后，不重选样式直接画第二个区域 → 继承全部样式
- 选中第一个区域改颜色后开始画第三个 → 第三个继承修改后的颜色
- 选中区域不编辑，取消选择后直接画 → draft 样式不被污染

---

### Step 3：Ctrl/Cmd + 滚轮缩放（解决问题 3）

**目标**：Ctrl+滚轮可缩放画布，普通滚轮仍用于页面滚动。

**实现要点**：

1. 在 `#workbenchCanvas` 上监听 `wheel` 事件
2. Ctrl/Cmd 按下时：
   - `preventDefault()`
   - `deltaY < 0` 放大，`deltaY > 0` 缩小
   - 缩放因子约 1.1（每步约 10%）
   - 钳制 50%–400%
3. 普通滚轮保持页面滚动
4. 缩放中心算法：记录鼠标归一化位置 → zoom → 调 scrollLeft/scrollTop 保持鼠标位置不变
5. 按钮缩放保持现有 25% 步长
6. 继续使用 `workbenchStage.style.width`，禁止 `transform: scale()`

**UI 提示**：在缩放工具栏旁显示 `Ctrl + 滚轮缩放`

**验收标准**：

- Ctrl+滚轮可缩放，范围 50%–400%
- 普通滚轮仍可滚动页面
- 缩放时鼠标位置附近的图形保持视觉中心

---

### Step 4：保存/切换后画布可靠重绘（解决问题 4）

**目标**：保存草图后切换到其他 tab 再切回，对象列表和画布 overlay 均自动显示。

**实现要点**：

1. 添加集中渲染函数：
   ```js
   function renderCanvasLayers(reason = "") {
     applyCanvasZoom();
     renderObjects();
   }
   ```
2. 若当前 `setCanvasZoom()` 合并了 stage 宽度更新和渲染，拆分出非渲染部分供 image-ready 路径调用
3. 处理以下场景：

| 场景 | 行为 |
|------|------|
| 图片缓存命中 | `image.complete && image.naturalWidth > 0` 时立即走 ready 分支，不等 onload；当前 URL 带 cache-buster，该分支主要是防御逻辑 |
| 正常图片加载 | `image.onload` 走 ready 分支 |
| 切回功能分区 tab | `loadDrawing()` resolve 后 `requestAnimationFrame(() => renderCanvasLayers("tab-switch"))` |
| 样式加载 | `loadStyle()` 不影响 overlay 可见性 |
| 自检（可选） | `state.objects.length > 0` 且 overlay 无子元素 → log warning + `requestAnimationFrame` 重试一次，不无限循环 |

**验收标准**：

- 保存草图 → 切到 traffic_analysis → 切回 → 对象列表和 overlay 自动显示
- 刷新页面 → 保存的 overlay 自动显示

---

### Step 5：最近使用颜色与自定义颜色持久化（解决问题 5）

**目标**：用户选择的自定义颜色在 session 内可复用。

**实现要点**：

1. 添加 `state.zoneRecentColors = []`（session 级，不持久化）
2. 不写入 `style_spec.json` 或 semantic JSON
3. 页面刷新清空，但 `loadDrawing()` 从保存对象重建

**触发规则**：

| 场景 | 行为 |
|------|------|
| 用户点固定色块 | 调用 `addRecentColor()`，因命中 palette / fallback palette 被跳过，不进入 recent |
| 用户用 `<input type="color">` 改色 | 加入 recent |
| `loadDrawing()` 扫描 `objects[].style_hints.fill_color` | 非 palette 色加入 recent |
| 切换 tab / Stage 7 出图 | 不清空 |
| 页面刷新 | 清空（从 saved objects 重建） |

**去重规则**：所有颜色应用都走同一个 `addRecentColor(color)` 入口；入口第一步判断是否命中 palette / fallback palette，命中则直接 return。recent 数组只保存非 palette 自定义色；recent 已满 6 个时踢出最老的。

**UI 布局**：

```
[palette swatches  10 格]
[最近使用：⬛⬛⬛⬛⬛⬛  (最多 6)]
[自定义颜色: <color input>]
```

`zoneCustomColor.value` 始终反映当前活跃样式：有选中对象时用其样式，否则用 `zoneDraftStyle`

**验收标准**：

- 用 color input 选非 palette 颜色 → 出现在"最近使用"
- 切 tab 再切回 → 如果该颜色被已保存对象使用，仍可复用
- "最近使用"不超过 6 个，超出时最老的被移除

---

### Step 6：键盘快捷键统一（跨步骤）

功能分区 tab，输入框未聚焦时：

| 键 | 行为 |
|---|------|
| `Enter` | `currentPoints.length >= 3` 时完成多边形 |
| `Esc` | 有草稿点 → 清空；无草稿点但有选中对象 → 清除选中 |
| `Ctrl/Cmd + Z` | 撤销（已有） |
| `Ctrl/Cmd + Shift + Z` | 重做（已有） |
| `Delete` / `Backspace` | 复用 `deleteSelected()` 删除选中对象，并保证 `Ctrl/Cmd + Z` 可撤回 |
| `Ctrl/Cmd + Wheel` | 缩放 |

不加方向键微移、空格拖拽平移。

---

## 四、CSS 补充

| 类名 | 用途 |
|------|------|
| `.zone-close-hit` | 闭合手柄透明命中区域 |
| `.zone-close-ring` 或等效 | 闭合手柄可见外圈 |
| 闭合手柄 hover 态 | 光晕 + pointer cursor |
| `.zone-recent-colors` | 最近使用颜色行 |
| zoom 工具栏提示样式 | `Ctrl + 滚轮缩放` 文案 |

---

## 五、代码改动定位

### workbench.js 预期改动区域

| 区域 | 改动内容 |
|------|----------|
| 顶部 state 声明 | 新增 `zoneRecentColors` |
| `renderFunctionalZoningTools()` | 渲染最近使用颜色行；color input 跟随活跃样式；添加 zoom 提示 |
| `normalizeZoneStyle()` | 保持返回 `stroke_width`，不写 `stroke_width_key` |
| `updateZoneStyle()` | 同步 `zoneDraftStyle`；fill color 变更时更新 recent colors |
| `addPoint()` | 有选中对象时复制 style 到 draft 再清 selectedId |
| `finishFunctionalZone()` | 不自动选中；保留 `zoneDraftStyle`；无重复闭合点 |
| `renderDraftSvg()` | 点数 ≥ 3 时渲染闭合手柄 |
| overlay 绑定 | 闭合手柄 click 单独绑定 + stopPropagation |
| `setCanvasZoom()` / zoom helpers | 添加 wheel zoom + 中心保持 |
| `loadDrawing()` / `loadBaseImage()` | 图片缓存 ready 路径 + `renderCanvasLayers` |
| `handleShortcuts()` | 添加 Enter、Esc、Delete/Backspace |

---

## 六、禁止事项

- 不改 `schema.py`
- 不改 `traffic_analysis`
- 不做 plain wheel 缩放
- 不持久化 `zoneRecentColors`
- 不写 recent colors 到 `style_spec.json` 或 semantic JSON
- 不改 `agent_drawing_protocol.md`
- 不动 `record.md`、`inventory.json`、项目 semantic 输出文件
- 不加顶点拖拽/形状编辑
- 不引入新框架或大规模重构
- 不顺手重构相邻代码
- 不写 `stroke_width_key` 到新保存的 JSON

---

## 七、验证计划

浏览器冒烟测试（尤其第 10 项“保存→切换→切回”）会写入 `projects/26-BQ-PARK/05_output/drawings/semantic/functional_zoning.json` 与 `inventory.json`。这些是预期的本地产物，测试后保持未提交或还原；提交时只 stage 代码与文档。

### 命令验证

```powershell
node --check _tools\uploader\static\workbench\workbench.js
git diff --check -- _tools\uploader\static\index.html _tools\uploader\static\workbench\workbench.css _tools\uploader\static\workbench\workbench.js
python _tools\validate_record.py 26-BQ-PARK
python -m py_compile _tools\drawing_workbench\schema.py
```

### 浏览器冒烟测试

| # | 操作 | 预期 |
|---|------|------|
| 1 | 画 3 点，点击首点闭合手柄 | 多边形闭合，无重复点，草稿手柄消失 |
| 2 | 画 2 点按 Esc | 草稿线消失 |
| 3 | 选中对象按 Delete | 对象被删除 |
| 4 | 创建自定义颜色/虚线/线宽 0.009 的区域 | 成功创建 |
| 5 | 不重选样式直接画第二个区域 | 继承颜色/边框/填充/线宽 |
| 6 | 选中第一个区域改颜色后画第三个 | 第三个继承修改后的颜色 |
| 7 | 选中区域不编辑，取消选择后画 | draft 样式不被污染 |
| 8 | Ctrl+滚轮在画布上缩放 | 缩放生效，50%–400% 范围内 |
| 9 | 普通滚轮 | 页面正常滚动 |
| 10 | 保存草图 → 切到 traffic_analysis → 切回 | 对象列表和 overlay 自动显示 |
| 11 | 刷新页面 | 保存的 overlay 自动显示 |
| 12 | color input 选非 palette 颜色 | 出现在"最近使用" |

---

## 八、完成报告要求

实施完成后需报告：

1. 改动文件列表
2. 5 个用户问题各自如何解决
3. 命令验证结果
4. 浏览器冒烟测试结果
5. 是否有项目输出文件被生成或未提交

提交时仅 stage 代码/文档，不 stage：
- `projects/26-BQ-PARK/05_output/inventory.json`
- `projects/26-BQ-PARK/05_output/drawings/semantic/`

---

## 九、执行顺序建议

```
Step 1 (闭合手势 + 快捷键)
  ↓ 验证：闭合、Esc、Delete
Step 2 (样式继承)
  ↓ 验证：连续绘制样式一致性
Step 3 (滚轮缩放)
  ↓ 验证：缩放 + 普通滚动
Step 4 (画布重绘)
  ↓ 验证：保存/切换/刷新
Step 5 (最近使用颜色)
  ↓ 验证：颜色记忆 + 去重
Step 6 (键盘快捷键统一)
  ↓ 全量冒烟测试
```

各 Step 之间相对独立，可按上述顺序逐步实施和验证。
