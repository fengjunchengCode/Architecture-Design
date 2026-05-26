# Style Spec 协商协议

**目的**：当用户要为某项目建立或修改 `05_output/style/style_spec.json` 时，agent（Claude）按本文档的对话 SOP 引导，确保对话产出能机械映射成 style_spec 字段。

**适用 agent**：claudecode / 任意带视觉的 Claude 会话。不是脚本协议，是对话剧本。

**前置条件**：用户在工作台已经选了项目；工作台顶部 style strip 显示"当前风格：未建立 style_spec"或上次更新时间。

---

## 1. 协商触发场景

| 场景 | 用户表达 | 走法 |
|---|---|---|
| 全新项目首次出图 | "26-BQ-PARK 还没有风格，先谈一下" | 走全流程 §3-§7 |
| 想沿用其他项目 | "参考 25-XX 项目的风格" | §2(b) → 跳到 §6 |
| 想基于参考 PDF | "我要启泰那种深绿+橙的风格" | §2(c) → §3-§7 |
| 改某一项 | "把主色再深一点" | 跳到 §5 直接局部改 |

---

## 2. Step 1 — 摸清起点

agent 第一句问，给四个选项：

```
本次报告想用什么风格？四个选项：
  (a) 沿用本项目已有的 style_spec
  (b) 复用其他项目的 style_spec（我可以列已有的）
  (c) 参考某份 PDF / 图片（你上传或指路径）
  (d) 从默认值起步，逐项谈
```

按选项加载素材：

- **(a)** 读 `projects/{code}/05_output/style/style_spec.json`，直接进入"过一遍当前值确认改/不改"
- **(b)** `ls projects/*/05_output/style/style_spec.json`，列出来让用户挑；挑完读那份作为起始
- **(c)** 用户给路径或上传 → 用视觉打开 → 抽出 palette/strokes/arrows 候选值
- **(d)** 从下面"默认起步值"起跑

### 默认起步值

```yaml
palette:
  primary: "#2E7D5C"        # 深绿
  accent: "#F97316"         # 橙
  neutral: "#1F2937"        # 深灰
  background: "#FFFDF8"     # 暖白
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

## 3. Step 2 — 走 7 个字段组

按顺序逐组确认：palette → typography → strokes → arrows → labels → legend → scale_north。

每组问一句、给候选、等回。**不要一次性把 7 组都摊开问，那是 form 填表，不是对话**。

### 问法模板

```
palette：
  我看 {参考来源} 是 {primary} + {accent}，本次沿用还是换？

typography：
  字体我建议中文用思源黑体回退到苹方，标题 16pt、正文 9pt、标签 9pt，要调吗？

strokes：
  主线 0.7mm、辅线 0.4mm、虚线节拍 4-2（毫米）。{参考来源} 主线偏粗约 1.0mm，
  本次跟参考还是按默认？

arrows：
  车行 / 人行流线默认开口三角（启泰风）。如果你想要实心箭头（长江风）告诉我。

labels：
  标签底色圆角矩形 + 透明度 0.88。要不要带引线（leader line）？

legend：
  图例表格式、放右下、单列。要不要改成散落式（直接贴在对象旁）或横排多列？

scale_north：
  标尺放左下、指北针放右上，标尺用色块刻度。要换 ratio 格式吗？
```

### 用户常见说法 → 字段映射

| 用户说 | 映射 |
|---|---|
| "深绿+橙" | `palette.primary = "#2E7D5C"`，`palette.accent = "#F97316"` |
| "颜色再深一点" | `palette.primary` 整体亮度 -10% |
| "字大一点" | `typography.*_size_pt += 1` 或 +2 |
| "线粗一点" | `strokes.primary_width_mm += 0.2` |
| "改实心箭头" | `arrows.default_style = "filled_triangle"` |
| "图例放右下" | `legend.position = "bottom_right"` |
| "不要指北针" | `scale_north.north_style = "none"` |
| "跟启泰一样" | 读启泰 P52/P54，反向抽 palette/strokes/arrows，全套覆写 |

---

## 4. Step 3 — 试出图确认（关键步骤）

7 组字段都谈完后，**不要直接落 style_spec.json**。先做试出图：

### 试出图选项

**A. 风格样卡（轻量）**：agent 生成一张 800×600 SVG，包含：
- 主色 + 辅色 + accent 三个色块
- 主线 / 辅线 / 虚线 三条线样
- 默认箭头一支
- 标签样例一个
- 图例条目两条
- 标尺 + 指北针

**B. 真实图试跑（重）**：agent 直接用当前 style_spec 跑一张已存在的草图（比如 BQ-PARK 的 A1 功能分区）。

**默认走 A**。除非用户说"直接出真实图"才走 B。

### 试出图后的对话

```
agent: 试出图在 {path}，你看一眼，要调哪里？
user: 主色还是不够深 / 箭头太大 / 图例字号太小 / ...
agent: 改 {field} 为 {new_value}，重新出图。{再贴新路径}
user: OK
```

### 注意

- 试出图 SVG 写到 `projects/{code}/05_output/style/preview/style_card_{timestamp}.svg`
- 同时把 PNG 也导一份（cairosvg），方便用户在终端 / 编辑器看
- 试出图迭代过程中**不**频繁覆盖 style_spec.json；只在用户最终拍板时写

---

## 5. Step 4 — 局部修改（绕过全流程）

用户已有 style_spec 且只想动一两项时，**不要把整个流程跑一遍**。

```
user: 把箭头改成实心
agent: 
  - 读当前 style_spec
  - 改 arrows.default_style = "filled_triangle"
  - 出一张新样卡
  - 用户确认 → 写 style_spec.json
```

判断标准：用户只提到 1-2 个字段 → 局部改；提到 3+ 个或"整个风格" → 全流程。

---

## 6. Step 5 — 保存 + 标注 approved_at

用户拍板后，agent 写 style_spec.json：

```json
{
  "schema_version": "1.0",
  "palette": {...},
  "typography": {...},
  ...
  "based_on": ["qitai:p52", "qitai:p54"],
  "approved_at": "2026-05-26T15:30:00+08:00",
  "updated_at": "2026-05-26T15:30:00+08:00",
  "notes": "用户偏好启泰主色，调亮一档"
}
```

字段说明：

- `based_on`：参考来源数组，格式 `{source}:{ref}`（如 `qitai:p52`、`project:25-XX`、`upload:inspiration1.jpg`）
- `approved_at`：用户最后一次"OK"的时刻
- `updated_at`：本次写入时刻（每次 save 都更新）
- `notes`：一句话说明本次决策要点，方便下次复用

agent 调 `POST /api/style/save`，让 server 跑 `validate_style_spec` 把关。

---

## 7. Step 6 — 风格继承（跨项目）

新项目想沿用旧项目时：

```
agent:
  1. 读 source 项目的 style_spec.json
  2. 全字段复制
  3. 仅改 based_on = [..., "project:{source_code}"]
  4. approved_at = null（强制用户重新过一遍才算批准）
  5. 跑一张样卡让用户看
  6. 用户拍 OK → approved_at 填上
```

继承不是"copy-and-forget"，永远要让用户走一次确认。

---

## 8. 边界 / 不做的事

- ❌ 不在 style_spec 里写绝对像素值（如"字号 36px"）—— 全用 pt/mm，渲染时换算
- ❌ 不让用户在工作台 UI 里调色（没有 GUI 调色板，本协议是对话产出唯一来源）
- ❌ 不假装能从 PDF 抽出精确色值 —— 视觉给的是"接近"，要用户确认
- ❌ 不在 style_spec 里塞 drawing_type 特定的字段（如 `functional_zoning.zone_a_color`）—— 风格是跨图种的，per-drawing 配色在 task_pack 的 user_notes 或 sketch 的 label 里说

---

## 9. 关联文档

- `docs/agent_drawing_protocol.md` —— agent 拿 style_spec 出图时怎么用
- `_tools/drawing_workbench/style_schema.py` —— validate_style_spec 校验逻辑
