# Style Spec 协商协议

**目的**：为某项目建立或修改 `05_output/style/style_spec.json`（设计 tokens）和 `style_card.svg`（设计资产）。流程"对标 → 变体 → 选定 → 抽参数 → 落 token → 样卡核对"。

**适用对象**：codex（端到端执行）、用户（选对标 + 选变体 + 批准）、claudecode（只在用户喊"复核"时介入审查；不在主流程上）。

**前置**：用户已选项目；工作台 style strip 显示"当前风格：未建立 style_spec"或上次更新时间。

---

## 1. 协议总览

```
Stage 0  codex 主持   询问用户对标（启泰 / 长江 / 已建项目 / 上传图 / 默认起步）
   ↓ 用户答
Stage 1  codex        基于对标派生 5 份变体提示词，写 vibe_board.md
   ↓
Stage 2  codex        调 imagegen 批量出 5 张 mockup PNG，追加 generation log
   ↓
Stage 3  codex 主持   把 5 张图路径告诉用户，等用户挑
   ↓ 用户挑
Stage 4  codex        视觉读 selected var_N + 对标原图，抽参数写 style_spec.json 草案
   ↓
Stage 5  codex        落 style_spec.json（approved_at: null）+ 写 SVG 样卡 + cairosvg 出 PNG
   ↓
Stage 6  codex 主持   告知样卡路径，等用户裁决
   ├─ OK    →  codex 把 approved_at 填入，commit；进入 Stage 7
   └─ 不 OK →  按用户反馈回 Stage 4（调参数）或 Stage 1（重生变体）或 Stage 0（换对标）
   ↓
Stage 7  codex        按 agent_drawing_protocol.md 出 A1/A2/...
```

**Claude 何时介入**：默认不介入。用户可以在任意 Stage 后说"找 Claude 审一下"，Claude 拉最新主线 + 看 codex 的产物，给意见。审查不阻塞流程。

**交付物双轨制**：

- `style_spec.json` —— **design tokens**（机器消费的精确数据）
- `style_card.svg` + `style_card.png` —— **design asset**（人核对用的视觉呈现）

二者必须一致：用户在 Stage 6 看的就是 style_spec.json 翻译出来的样子。

---

## 2. Stage 0 · 选对标（codex 主持）

codex 在对话窗口启动流程时，先报告当前 style_spec 状态，再问对标：

```
codex: 项目 {code} 当前未建立 style_spec。选对标：
  1) 启泰直销市场（P52/P54，冷调低饱和分区 + 暖橙流线）
  2) 长江大厦（P41/P42，同 firm 体系）
  3) 已建项目 style_spec.json（我列一下：...）
  4) 上传图作对标
  5) 从默认起步值开始
```

可选来源 + codex 后续动作：

| 来源 | 用户表达 | codex 后续 |
|---|---|---|
| 仓内参考 PDF 同类页 | "选 1" / "启泰" | 查 `docs/reference_pdfs/page_index.json` 取页码 + 调 `pdf_page_extract.py` 出 PNG |
| 已有项目 | "选 3 / 参考 25-XX" | 读 `projects/25-XX/05_output/style/style_spec.json` |
| 用户上传图 | "选 4" + 路径 | 视觉打开图片 |
| 默认起步 | "选 5 / 从零开始" | 用默认起步值（见 §10） |

**只能选一个**。多个对标会让派生变体逻辑混乱。如果用户想揉合多个 family，让其先选主对标，变体维度上吸收其他对标的某项特征。

**如果 Stage 0 时 pdf_page_extract 失败**（poppler 缺）：codex 把对标原 PDF 路径 + 页码作为 base，跳过实际抽页，直接进 Stage 1 用文字描述代替视觉锚点。

---

## 3. Stage 1 · 派生变体提示词（codex）

输入：Stage 0 锁定的对标素材（视觉可读的 PNG / 文字描述 / 已有 style_spec.json）。输出：5 份提示词文本写入 `vibe_board.md`。

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

codex 写 `projects/{code}/05_output/style/vibe_board.md`（schema 见 §11）。本 Stage **只**写 md，不调 imagegen（Stage 2 才调）。

写完后 codex 可以在对话窗口给用户一个简短预览（5 份变体动的维度列表），不强求用户在出图前确认提示词——直接进 Stage 2。

---

## 4. Stage 2 · 批量出图（codex）

输入：`05_output/style/vibe_board.md`。输出：5 张 PNG + 写回执到 md。

### 执行步骤

1. 读 vibe_board.md，拿到 5 份提示词
2. 逐份调 imagegen 出图（codex 自带生图能力，直接调用即可）
3. 保存到 `05_output/style/vibe_board/var_{1-5}.png`
4. 调用失败时（quota / 网络 / 模型故障）：写错误到 vibe_board.md 的 `errors` 段，**不要**伪造 PNG，**不要**重试超过 2 次同一份提示词
5. 全部完成后追加 `## Generation log` 段到 vibe_board.md（结构见 §11）
6. commit 5 张 PNG + 更新后的 vibe_board.md
7. 在对话窗口告诉用户：5 张 mockup 路径 + 哪几张成功，进 Stage 3

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

## 6. Stage 4 · 抽参数（codex）

输入：选定的 var_N.png + 对标原图（同时视觉打开）。输出：style_spec.json 草案文本（先在内存里、不落盘，Stage 5 才落盘）。

### 抽取方法

1. **用视觉同时打开 var_N.png 和对标原图**
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

### 衔接

codex 自己抽完直接进 Stage 5 落盘 + 出样卡，不需要外部 review。如果用户在 Stage 3 给了"颜色再暖一档"这种微调要求，codex 在抽取时就吸收进去。

---

## 7. Stage 5 · 落 token + 出样卡（codex）

输入：Stage 4 抽出的 style_spec.json 草案。输出：3 个文件。

### 文件清单

| 文件 | 位置 | 内容 |
|---|---|---|
| Design Tokens | `05_output/style/style_spec.json` | 按草案落盘，`approved_at: null`，`updated_at: now()` |
| Design Asset (SVG) | `05_output/style/style_card.svg` | 按 §8 规格手写，800×600 |
| Design Asset (PNG) | `05_output/style/style_card.png` | cairosvg 转出来；本机 Cairo 缺则跳过并写明 |

### 自检前 commit

样卡 SVG 的每一处颜色 / 线宽 / 字号必须**直接引用 style_spec.json 的字段值**。codex 写完 SVG 后再扫一遍：

- 色卡区每块的 fill 是否在 palette 里能找到？
- 线样区每条线的 stroke-width 是否换算自 strokes.*_width_mm？
- 箭头形状是否对应 arrows.default_style / per_object_type？
- 图例区布局是否匹配 legend.layout？

任何一条对不上 → 改 SVG，不改 spec（spec 是 ground truth）。

### 不要做的事

- ❌ 不在样卡里加 spec 没写的视觉元素
- ❌ 不填 `approved_at`（等用户 Stage 6 OK）
- ❌ 不调 imagegen 出样卡（样卡是确定性 SVG，imagegen 只在 Stage 2 用）

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

**调一两项**：用户说"主色再深一点 / 箭头改小一点"。codex 在原 spec 基础上局部改字段 → 重写 style_spec.json + 重出样卡。**不**回头重出 mockup。每次改动 `updated_at` 同步、`approved_at` 清回 null。

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

1. 用户在 Stage 0 选"参考 25-XX 项目"
2. codex 读 source 项目 style_spec.json
3. **不**跳到 Stage 5。仍要走 Stage 1-3：把 source spec 作为 var_1（用 imagegen 出图也行，但可以让 var_1 直接复用 source 的样卡截图），再派生 4 个变体让用户对比
4. 用户选 → 后续相同

继承不等于复用。每个项目都要走一遍批准，避免风格漂移失控。

---

## 13. 边界 / 不做的事

- ❌ 不在工作台 UI 做 GUI 风格编辑器（调色板 / 滑块全部不要）
- ❌ 不调 imagegen 出真实技术图（imagegen 只用于 Stage 2 的 vibe board）
- ❌ 不把 Stage 2 / Stage 5 失败的产物入仓
- ❌ 不在 style_spec.json 里写绝对像素（mm/pt 单位描述，渲染时换算）
- ❌ 不在没批准（`approved_at: null`）时启动 Stage 7 真图生产
- ❌ 不在 style_spec.json 里塞 drawing_type 特定字段（per-drawing 偏好放在 task_pack 的 user_notes）
- ❌ 不在用户没明确同意的情况下删本地未跟踪文件（之前 codex 在 smoke 收尾时清过用户的 IMG_*.jpg，下次保留）

---

## 14. 关联文档

- `docs/agent_drawing_protocol.md` —— Stage 7 真图生产时怎么用 style_spec
- `docs/planning/TECHNICAL_DRAWING_TYPES_ROADMAP_2026-05-25.md` —— 图种全集
- `_tools/drawing_workbench/style_schema.py` —— validate_style_spec 字段约束
- `docs/reference_pdfs/page_index.json` —— 参考 PDF 页码索引（Stage 0 用）
