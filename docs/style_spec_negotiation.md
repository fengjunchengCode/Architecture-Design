# Style Spec 协商协议

**目的**：为某项目建立或修改 `05_output/style/style_spec.json`（设计 tokens）和 `style_card.svg`（设计资产）。流程"对标 → 变体 → 选定 → 抽参数 → 落 token → 样卡核对"。

**适用对象**：claudecode（规划 + 抽参数 + 审阅）、codex（出图 + 落盘 + 出样卡）、用户（选对标 + 选变体 + 批准）。

**前置**：用户已选项目；工作台 style strip 显示"当前风格：未建立 style_spec"或上次更新时间。

---

## 1. 协议总览

```
Stage 0  用户       选对标（一个 family）
   ↓
Stage 1  Claude     基于对标派生 5 份变体提示词
   ↓
Stage 2  codex      调 imagegen 批量出 5 张 mockup PNG，写 vibe_board.md
   ↓
Stage 3  用户       选定 1 张（或要求重生）
   ↓
Stage 4  Claude     从选定 mockup + 对标原图抽参数，写 style_spec.json 草案
   ↓
Stage 5  codex      落 style_spec.json + 写 SVG 样卡 + 可选 cairosvg 出 PNG
   ↓
Stage 6  用户       看样卡核对真实参数能不能落地
   ├─ OK    →  approved_at 填入，进入 Stage 7（真图生产）
   └─ 不 OK →  回 Stage 4（调参数）或回 Stage 0（换对标）
   ↓
Stage 7  codex      按 agent_drawing_protocol.md 出 A1/A2/...
```

**交付物双轨制**：

- `style_spec.json` —— **design tokens**（机器消费的精确数据）
- `style_card.svg` + `style_card.png` —— **design asset**（人核对用的视觉呈现）

二者必须一致：用户在 Stage 6 看的就是 style_spec.json 翻译出来的样子。

---

## 2. Stage 0 · 选对标

用户在对话窗口或工作台说出对标。可选来源：

| 来源 | 表达 | Claude 后续动作 |
|---|---|---|
| 仓内参考 PDF 同类页 | "按启泰风格" / "按长江风格" | 查 `docs/reference_pdfs/page_index.json` 取页码 |
| 已有项目 | "参考 25-XX 项目" | 读 `projects/25-XX/05_output/style/style_spec.json` |
| 用户上传图 | "按这张图" + 路径 | 视觉打开图片 |
| 默认起步 | "从零开始" | 用默认起步值（见 §10） |

**只能选一个**。多个对标会让派生变体逻辑混乱。如果想揉合多个 family，建议先选主对标，在变体维度上吸收其他对标的某项特征。

---

## 3. Stage 1 · 派生变体提示词（Claude）

输入：对标素材。输出：5 份提示词文本，写入 `vibe_board.md` 准备让 codex 执行。

### 派生原则

- **5 份共享同一个 base**（对标的核心特征：构图、视角、画幅）
- **每份只动 1-2 个维度**，差异小步
- 维度库（每变体动 1-2 个）：
  - palette 温度（暖移 / 冷移）
  - palette 饱和度（提饱 / 降饱）
  - background 明暗（提亮 / 压暗）
  - legend 布局（sidebar / bottom strip / scatter）
  - stroke 粗细（粗化 / 细化）
  - 装饰元素（去除 / 添加纹理）

不要让 5 份变成"5 个完全不同风格"。**变体是兄弟，不是表亲**。

### 提示词模板

每份提示词必须自包含（imagegen 无状态），结构：

```
[场景]：A3 horizontal architectural master plan rendering page.
Top-down aerial view of a small pocket park in Tibet plateau, ~7800㎡ site.
Right side: vertical legend bar.
Left side: master plan with functional zones, flow arrows, entrance markers.
Page is a single sheet from a Chinese architectural design report.

[对标]：{描述对标的核心视觉}.

[变体]：{这一份动了什么维度，怎么动}.

[输出要求]：clean rendering style, no photographic realism, no people, 
no text labels (Chinese characters in legend OK), high resolution, 
A3 landscape composition.
```

### 输出文件

Claude 不写 PNG，只写 `projects/{code}/05_output/style/vibe_board.md`（schema 见 §11）。提示词文本在这份 md 里，codex 读它去调 imagegen。

---

## 4. Stage 2 · 批量出图（codex）

输入：`05_output/style/vibe_board.md`。输出：5 张 PNG + 写回执到 md。

### 执行步骤

1. 读 vibe_board.md，拿到 5 份提示词
2. 检查本机 imagegen MCP 是否可用（`mcp__plugin_imagegen_imagegen__text-to-image` 或 `imagegen:image-generation` skill）
3. 逐份调 imagegen，保存到 `05_output/style/vibe_board/var_{1-5}.png`
4. 调用失败时（quota / 网络 / 模型故障）：写错误到 vibe_board.md 的 `errors` 段，**不要**伪造 PNG
5. commit + 在 review thread 贴：成功几张 / 失败几张 / 路径列表

### 不要做的事

- ❌ 不改提示词内容（如果提示词有问题，先在 review thread 提）
- ❌ 不调 imagegen 出超过 5 张
- ❌ 不删之前的 var_*.png（除非重生时才覆盖）

---

## 5. Stage 3 · 选定方向（用户）

用户在工作台 / 文件浏览器 / 终端打开 `vibe_board/*.png` 横向对比，给出一个数字（var_N）。

**允许的反馈**：
- "选 var_3" → Stage 4 启动
- "var_3 但颜色再暖一点" → Stage 4 时 Claude 在 var_3 基础上做微调
- "5 张都不行，再来一批" → 回 Stage 1，Claude 调整维度组合重派
- "换对标" → 回 Stage 0

---

## 6. Stage 4 · 抽参数（Claude）

输入：选定的 var_N.png + 对标原图（同时看）。输出：style_spec.json 草案文本（不落盘）。

### 抽取方法

1. **用视觉打开 var_N.png 和对标原图**
2. 优先以 var_N 为准（用户看到的就是它），对标图作为"补充细节"参考
3. 按 schema 顺序填字段：
   - palette：从 var_N 直接取主色 + 辅色 + accent；从对标补 annotation_colors 细节
   - typography：用对标（imagegen 通常字体不准）
   - strokes：估算粗细，参考 §10 默认
   - arrows：观察 var_N 的箭头样式
   - labels：参考对标
   - legend：以 var_N 的布局为准
   - scale_north：参考对标
4. `based_on` 字段：`["qitai:p52", "qitai:p54", "vibe:var_3"]` 这种格式，全部来源都标
5. `approved_at: null`（强制走 Stage 6）
6. `notes`：一句话说明本次决策要点（"用户挑了 var_3，偏冷调升级、橙色保留启泰"）

### 颜色清洗

imagegen 出的颜色像素级不稳定。抽取规则：

- 找 var_N 里**面积大的主色**，吸出 hex
- 用最近的"整数 hex"代替（如 `#7A9D5F` → `#7A9C5E`）
- 同色系（如多个功能分区绿）保留对比度差，不要全合并成一种绿

### 输出

Claude 在对话窗口贴完整 style_spec.json 候选 + 给 codex 一份 GO 信号（见 §7 的"GO 信号格式"）。

---

## 7. Stage 5 · 落 token + 出样卡（codex）

输入：Claude 给的 GO 信号（含完整 style_spec.json 文本 + 样卡 SVG 规格）。输出：3 个文件。

### 文件清单

| 文件 | 位置 | 内容 |
|---|---|---|
| Design Tokens | `05_output/style/style_spec.json` | 按 GO 信号原文落盘，`approved_at: null` |
| Design Asset (SVG) | `05_output/style/style_card.svg` | 按规格手写，800×600，元素见 §8 |
| Design Asset (PNG) | `05_output/style/style_card.png` | cairosvg 转出来；本机 Cairo 缺则跳过 |

### GO 信号格式（Claude → codex）

```yaml
target_project: 26-BQ-PARK
stage: style_lock
style_spec_json: |
  {  ...完整 JSON...  }
style_card_spec:
  canvas: 800x600
  background: "{style_spec.palette.background}"
  sections:
    - id: title
      content: "26-BQ-PARK 风格样卡 v1"
    - id: palette_swatches
      colors: [primary, secondary, accent, neutral, ...]
    - id: stroke_samples
      lines: [primary, secondary, dashed]
    - id: arrow_samples
      arrows: [vehicle_flow, pedestrian_flow]
    - id: entrance_markers
      types: [main, secondary, freight]
    - id: legend_example
      rows: 6
    - id: scale_bar
    - id: north_compass
```

### 不要做的事

- ❌ 不修改 style_spec.json 字段内容（要改回 Claude 改）
- ❌ 不填 `approved_at`（等用户 Stage 6 OK）
- ❌ 不写"漂亮但不一致"的样卡 —— 样卡所有元素必须**直接取自 style_spec.json 的值**

---

## 8. Stage 5 样卡 SVG 元素规格

样卡 SVG 必须包含以下区域，从 style_spec.json 取值：

| 区域 | 内容 | 取自字段 |
|---|---|---|
| 顶部标题 | "{code} 风格样卡 v1" | typography.title_* |
| 色块网格 | palette 所有色 + annotation_colors，每块 80×40，标 hex + 用途 | palette |
| 字号样本 | 标题 / 副标题 / 正文 / 标签四档示例文字 | typography |
| 线样 | 主线 / 辅线 / 虚线 / 点划线四条样本，标毫米数 | strokes |
| 箭头 | per_object_type 里每种箭头一个示例 | arrows |
| 出入口 | 主 / 次 / 货 三种 marker | palette.annotation_colors |
| 标签样例 | 一个完整 label 样例（含底盒 / 引线 / 文字） | labels |
| 图例条目 | 6 行 sidebar 示例 | legend |
| 标尺 | 5 段刻度，标 100m | scale_north |
| 指北针 | compass / arrow / text，取实际配置 | scale_north |

布局：上左到下右 z 字流，色块网格占最大区。

---

## 9. Stage 6 · 核对+批准（用户）

用户在浏览器打开 `style_card.svg`（或看 PNG）。

**OK 路径**：用户说"过 / OK / 拍板" → codex 把 `style_spec.json` 的 `approved_at` 填上 now()，`updated_at` 同步更新。

**调一两项**：用户说"主色再深一点 / 箭头改小一点"。Claude 在原 spec 基础上局部改字段 → 给 codex 新 GO 信号 → codex 重写 spec + 重出样卡。**不**回头重出 mockup。

**整体不行**：用户说"风格不对，再选" → 回 Stage 3 重新挑 var_N；或回 Stage 0 换对标。

**调整时**：codex 每次更新 spec 必须把 `approved_at` 清回 null，强制重批。

---

## 10. 默认起步值

用户选"从零开始"时用这个；变体派生时也作为字段填补默认：

```yaml
palette:
  primary: "#2E7D5C"
  accent: "#F97316"
  neutral: "#1F2937"
  background: "#FFFDF8"
typography:
  title_font: "Source Han Sans CN, PingFang SC, sans-serif"
  body_font: "Source Han Sans CN, PingFang SC, sans-serif"
  title_size_pt: 16
  body_size_pt: 9
  label_size_pt: 9
strokes:
  primary_width_mm: 0.7
  secondary_width_mm: 0.4
  dashed_pattern: "4 2"
arrows:
  default_style: "open_triangle"
  default_size_mm: 5
labels:
  shape: "rounded_rect"
  corner_radius_mm: 1.5
  padding_x_mm: 2
  padding_y_mm: 1
  background_alpha: 0.88
legend:
  layout: "table"
  position: "bottom_right"
  columns: 1
scale_north:
  scale_style: "bar"
  scale_position: "bottom_left"
  north_style: "compass"
  north_position: "top_right"
```

---

## 11. vibe_board.md schema

Claude 在 Stage 1 写、codex 在 Stage 2 追加回执：

```markdown
# Vibe Board · {project_code}

## Benchmark

- source: qitai
- ref_pages: [52, 54]
- ref_pdf: docs/reference_pdfs/report_examples/20260410西藏启泰直销市场建设项目-3.pdf
- locked_at: 2026-05-26T...

## Base prompt template

[场景]: ...
[对标]: ...
[输出要求]: ...

## Variations

### var_1

- axis_varied: ["palette_temperature: +warm"]
- prompt: |
  [完整提示词文本，包含 base + 变体 + 输出要求]
- status: pending | generated | failed
- file: var_1.png
- error: null

### var_2

(同上)

### var_3
### var_4
### var_5

## Generation log（codex 写）

- attempted_at: 2026-05-26T...
- imagegen_tool: mcp__plugin_imagegen_imagegen__text-to-image
- model: gpt-image-1（或实际用的）
- success: [1, 2, 3, 5]
- failed: [4]
- errors:
  - var_4: "rate limit / model error / ..."

## Selection（用户 + Claude 写）

- picked: var_3
- picked_at: 2026-05-26T...
- adjustments_requested: "颜色再暖一档"  # 可选
```

---

## 12. 跨项目风格继承

新项目想沿用旧项目的 style_spec：

1. 用户说"参考 25-XX 项目"
2. Claude 读 source 项目 style_spec.json
3. **不**跳到 Stage 5。仍要走 Stage 1-3：把 source spec 作为 var_1，再派生 4 个变体让用户对比
4. 用户选 → 后续相同

继承不等于复用。每个项目都要走一遍批准，避免风格漂移失控。

---

## 13. 边界 / 不做的事

- ❌ 不在工作台 UI 做 GUI 风格编辑器（调色板 / 滑块全部不要）
- ❌ 不调 imagegen 出真实技术图（imagegen 只用于 Stage 2 的 vibe board）
- ❌ 不让 codex 自行决定 style_spec 字段值（必须 Claude 给）
- ❌ 不把 Stage 2 / Stage 5 失败的产物入仓
- ❌ 不在 style_spec.json 里写绝对像素（mm/pt 单位描述，渲染时换算）
- ❌ 不在没批准（`approved_at: null`）时启动 Stage 7 真图生产
- ❌ 不在 style_spec.json 里塞 drawing_type 特定字段（per-drawing 偏好放在 task_pack 的 user_notes）

---

## 14. 关联文档

- `docs/agent_drawing_protocol.md` —— Stage 7 真图生产时怎么用 style_spec
- `docs/planning/TECHNICAL_DRAWING_TYPES_ROADMAP_2026-05-25.md` —— 图种全集
- `_tools/drawing_workbench/style_schema.py` —— validate_style_spec 字段约束
- `docs/reference_pdfs/page_index.json` —— 参考 PDF 页码索引（Stage 0 用）
