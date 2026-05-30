# PPT 出图预览功能实施计划

日期：2026-05-30
状态：讨论定稿后开始实施
范围：技术图纸工作台的 PPT 预览、图纸说明、自动排版与后续 PPTX 导出基础设施

## 1. 需求背景

当前制图工作台已经能够完成各类技术图纸的语义绘制、图例生成、配图上传、草图保存、agent task_pack 打包与 PNG/PDF 导出。下一步需要把“保存后的图纸、图例、上传配图、每张图纸的说明文字”自动排版成横版 PPT，并在导出前提供可手动调整的预览界面。

用户确认的硬性规则：

1. PPT 固定为 16:9 横版。
2. 一张图纸对应一页预览和一页最终 PPT。
3. 图纸本体在最终 PPT 中的位置和大小必须全 deck 一致。
4. 自动排版只允许调整图例、图纸说明文本、配图，不能调整图纸本体。
5. 图例、文本、配图必须避开图纸框，不能压在图纸上。
6. deck 模板方向全局统一，可在“图纸左 + 信息右”和“信息左 + 图纸右”之间切换。
7. 用户拖动/缩放图纸框或切换左右版式时，必须弹窗确认，说明该修改会影响所有图纸页。
8. 全局图纸框变化后，所有页图纸框立即同步，所有页信息元素标记为需要重新排版；用户可逐页或全部重新排版。

## 2. 样例版式观察

参考目录：

```text
docs/reference_pdfs/report_examples/
```

已抽查：

- `20260410西藏启泰直销市场建设项目-3.pdf` 第 51-60 页。
- `202600520西藏长江大厦建设项目-4.pdf` 第 41-42 页。

观察结论：

- 两份 PDF 页面尺寸均为 1191 x 669 pt，比例约为 16:9。
- 启泰样例多数技术图纸采用“图纸左 + 信息右”：左侧大图纸约占页面宽度 64%-66%，右侧为说明文字、图例和配图。
- 长江样例采用“信息左 + 图纸右”：左侧为说明和图例，右侧大图纸约占页面宽度 64%-66%。
- 人防等偏技术底图页面仍保持一图一页，只是右侧信息元素更少。

## 3. 架构原则

### 3.1 不改语义草图 schema

现有 `05_output/drawings/semantic/{drawing_type}.json` 只负责“图上画了什么”。PPT 页面排版是另一个层级，不写入 semantic drawing schema，避免污染已经稳定的绘图数据。

### 3.2 新增 deck layout 数据层

新增文件：

```text
projects/{project_code}/05_output/ppt/drawing_deck/layout.json
```

该文件负责：

- deck 全局版式。
- 全局图纸框。
- 每张图纸的说明文字。
- 每张图纸的图例、说明、配图布局。
- 每张图纸当前排版是否基于最新图纸框。
- 是否存在手动调整。

### 3.3 图纸框强一致

`drawing_frame` 是 deck 全局属性，不是单页属性。任何页面中的图纸拖动、缩放或左右模板切换，都修改同一份全局配置。

导出 PPTX 时必须做硬校验：所有 slide 中图纸对象的 `x/y/w/h` 完全一致，否则拒绝导出。

## 4. 数据结构草案

```json
{
  "schema_version": "1.0",
  "project_code": "26-BQ-PARK",
  "slide": {
    "aspect": "16:9",
    "width": 13.333,
    "height": 7.5
  },
  "template_side": "drawing_left",
  "drawing_frame_version": 1,
  "drawing_frame": { "x": 0.02, "y": 0.17, "w": 0.64, "h": 0.72 },
  "slides": {
    "functional_zoning": {
      "title": "功能分区",
      "text": "",
      "layout_generated_from_frame_version": 1,
      "needs_reflow": false,
      "manual_overrides": false,
      "elements": {
        "legend": { "x": 0.70, "y": 0.18, "w": 0.27, "h": 0.32 },
        "text": { "x": 0.70, "y": 0.52, "w": 0.27, "h": 0.18 },
        "supporting_images": []
      }
    }
  }
}
```

坐标均为 slide 归一化坐标，范围 0-1。前端预览与后端 PPTX 导出必须使用同一份坐标，避免 HTML 预览和最终 PPT 不一致。

## 5. 默认模板

### 5.1 图纸左 + 信息右

适合启泰样例多数页面。

```json
{
  "template_side": "drawing_left",
  "drawing_frame": { "x": 0.02, "y": 0.17, "w": 0.64, "h": 0.72 },
  "info_area": { "x": 0.70, "y": 0.17, "w": 0.27, "h": 0.72 }
}
```

### 5.2 信息左 + 图纸右

适合长江样例。

```json
{
  "template_side": "drawing_right",
  "drawing_frame": { "x": 0.34, "y": 0.10, "w": 0.64, "h": 0.84 },
  "info_area": { "x": 0.04, "y": 0.18, "w": 0.25, "h": 0.72 }
}
```

### 5.3 图纸实际比例处理

不同图纸本体可能是长方形或正方形。为保证 PPT 中图纸对象位置大小一致，导出时应先生成统一比例的 `drawing_plate`：

- `drawing_plate` 尺寸比例等于全局 `drawing_frame`。
- 真实图纸在 plate 内按 `contain` 方式居中显示。
- plate 允许留白，但不拉伸真实图纸。
- PPTX 中插入的是 plate，因此每页图纸图片对象的 `x/y/w/h` 完全一致。

第一阶段预览可直接用现有 PNG/SVG/底图模拟 plate；PPTX 导出阶段再落机械生成。

## 6. 用户交互

### 6.1 图纸说明

每张图纸工作台增加“PPT 图纸说明”文本框。

- 保存到 deck layout 当前 slide 的 `text`。
- 不进入 semantic drawing schema。
- 切换图纸时读取对应文本。
- 保存草图不必自动保存说明；说明有自己的保存动作，避免混淆。

### 6.2 PPT 预览

在工作台中增加“PPT 预览”模式：

- 左侧仍用现有图纸类型 tabs 切换页面。
- 中央显示 16:9 slide 预览。
- 图纸框、图例、说明文本、配图均按 layout 坐标渲染。
- 图纸框使用全局 `drawing_frame`。
- 当前页若 `needs_reflow=true`，预览显示“需重新排版”提示。

### 6.3 修改全局图纸框

触发条件：

- 用户拖动图纸框。
- 用户缩放图纸框。
- 用户切换 `drawing_left` / `drawing_right`。

必须弹窗：

```text
图纸位置和大小会应用到全部图纸页，并可能影响现有图例、文本、配图排版。
是否继续？
```

确认后：

1. 更新全局 `drawing_frame` 或 `template_side`。
2. `drawing_frame_version += 1`。
3. 所有 slides 标记 `needs_reflow=true`。
4. 图纸框立即在所有预览页同步。
5. 用户可选择“重新排版本页”或“全部重新排版”。

### 6.4 重新排版

重新排版只允许改变：

- `elements.legend`
- `elements.text`
- `elements.supporting_images`

禁止改变：

- `drawing_frame`
- `template_side`

如果当前页存在 `manual_overrides=true`，重新排版前提示：

```text
重新排版会覆盖本页手动调整。是否继续？
```

### 6.5 手动调整

第一阶段先实现基础预览和全局图纸框同步；后续增加图例、文本、配图拖动/缩放。

手动调整规则：

- 图例、文本、配图：只影响当前 slide。
- 图纸框：影响全部 slide，必须确认。
- 手动调整后当前 slide `manual_overrides=true`。

## 7. 自动排版规则

第一阶段使用确定性规则，不直接接 AI：

1. 根据 `template_side` 计算信息区。
2. 说明文本较长时优先占信息区上部。
3. 图例放在说明文本下方或信息区顶部，视是否有说明文本决定。
4. 配图按 1/2/3/4 张在信息区剩余空间内网格排布。
5. 所有信息元素必须避开 `drawing_frame`。
6. 信息区不足时降低配图高度或标记 `layout_warnings`，不覆盖图纸。

后续接 AI 时，AI 只能输出信息元素布局，后端必须校验：

- 坐标在 0-1。
- 不与 `drawing_frame` 相交。
- 最小宽高满足可读性。
- 不修改全局图纸框。

## 8. 实施步骤

### F1 文档与数据模型

- 新增本文档。
- 新增 `_tools/drawing_workbench/deck_layout.py`。
- 实现 layout 默认值、normalize、load/save、reflow。
- 新增 API：
  - `GET /api/drawing/deck-layout?project=...`
  - `POST /api/drawing/deck-layout/save`
  - `POST /api/drawing/deck-layout/reflow`

验收：

- 新项目无 layout 时返回默认 layout。
- 保存说明文本后写入 `05_output/ppt/drawing_deck/layout.json`。
- 切换模板或图纸框后 `drawing_frame_version` 增加，所有 slide 标记 `needs_reflow=true`。

### F2 工作台说明文本

- 在右侧检查器增加“PPT 图纸说明”区域。
- 展示当前图纸的说明文本。
- 保存到 deck layout 当前 slide。
- 切换图纸后加载对应文本。

验收：

- 每张图纸文本互不覆盖。
- 保存、刷新、重新加载项目后文本仍在。

### F3 PPT 预览基础模式

- 工作台增加“制图 / PPT 预览”切换。
- PPT 预览显示 16:9 slide。
- 使用全局 `drawing_frame` 渲染图纸区域。
- 使用当前 slide 的 `legend/text/supporting_images` 布局渲染信息元素。

验收：

- 10 张图纸都有预览。
- 所有预览中的图纸框位置和大小一致。
- 图例、文本、配图不压住图纸框。

### F4 全局图纸框与模板切换

- 支持切换 `图纸左` / `图纸右`。
- 支持基础图纸框数值调整。
- 修改前弹窗确认。
- 修改后所有页同步并标记需重新排版。

验收：

- 任一页修改图纸框后，切到其他页图纸框一致。
- 重新排版按钮可清除当前页或全部页 `needs_reflow`。

### F5 手动调整与导出

后续阶段：

- 图例、文本、配图拖动/缩放。
- 生成 `drawing_plate`。
- PPTX 导出。
- PPTX XML 校验所有 slide 图纸对象 `x/y/w/h` 一致。

## 9. 测试门禁

基础门禁：

```powershell
python -m py_compile _tools\drawing_workbench\deck_layout.py _tools\uploader\server.py
node --check _tools\uploader\static\workbench\workbench.js
python _tools\tests\drawing_workbench_api_smoke.py
python _tools\tests\drawing_workbench_browser_smoke.py
```

新增 API smoke 断言：

- deck layout 默认加载。
- 保存 slide text。
- 模板切换标记所有 slide 需要重新排版。
- reflow 当前页后当前页 `needs_reflow=false`。

新增浏览器 smoke 断言：

- PPT 说明文本保存并重载。
- PPT 预览存在 16:9 slide。
- 切换图纸时图纸框坐标一致。
- 模板切换弹窗存在。
- reflow 后当前页不再提示需要重新排版。

## 10. 开发红线

- 不改 `docs/CLAUDE_CODEX_REVIEW_THREAD.md`。
- 不把 PPT layout 字段塞进 semantic drawing schema。
- 不提交 `projects/26-BQ-PARK/05_output/` 下已有运行输出脏文件，除非用户明确要求保存项目输出示例。
- 不破坏现有制图工作台：绘制、选中、弧线、预设、图例、配图、task_pack、PNG/PDF 导出必须继续通过现有 smoke。
