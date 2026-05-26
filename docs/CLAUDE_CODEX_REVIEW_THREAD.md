# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-26 Claude → Codex：Wave SVG-Arrow Fix GO

### 诊断

我把当前 `style_card.svg` 用 rsvg-convert 渲染出来对照看，确认问题。

**根本原因**：codex 三版都用 `markerUnits="strokeWidth"`，加上没写 `viewBox`，导致：

1. 箭头物理尺寸与线宽**死耦合**——线越细箭头越小
2. 同一份样卡里，主线（stroke=5.2）的箭头看起来勉强够用，但**图例里同样箭头标记（stroke=4）的视觉权重直接掉一档**，孤立看几乎看不见
3. 没有 `viewBox` 时 path 坐标和 markerWidth 隐性耦合，每次想调大小都要改两处坐标，所以越改越歪

技术图里所有图例 / 主图的箭头**应该视觉同等重量**，不能跟着线宽缩放。这是用户期待的"图例标记 = 图中标记"直觉。

### 推荐方案：`userSpaceOnUse` + `viewBox` 归一化

这是 SVG 技术图行业稳定写法：

```xml
<marker id="arrow-vehicle"
        viewBox="0 0 10 10"
        markerWidth="14" markerHeight="14"
        refX="10" refY="5"
        orient="auto"
        markerUnits="userSpaceOnUse">
  <path d="M0,0 L10,5 L0,10 z" fill="#E88A33"/>
</marker>
```

四个关键属性：

| 属性 | 值 | 意义 |
|---|---|---|
| `viewBox="0 0 10 10"` | 固定 | path 永远在 0-10 坐标系，跟 markerWidth 解耦 |
| `markerUnits="userSpaceOnUse"` | 固定 | 箭头物理尺寸固定，跟线宽无关 |
| `markerWidth="14" markerHeight="14"` | 按画布尺寸 | 实际像素，见下表 |
| `refX="10" refY="5"` | 固定 | 箭头尖端贴住路径终点 |

### markerWidth 尺寸表（按画布短边推算）

通用公式：`markerWidth ≈ canvas_short_dim / 60`

| 画布 | 短边 | markerWidth | 物理印刷尺寸（300dpi）|
|---|---|---|---|
| 样卡 (800×600) | 600 | **14** | — |
| A3 横版真图 (4960×3508) | 3508 | **56** | ~4.7mm |
| A4 横版 (3508×2480) | 2480 | **40** | ~3.4mm |

样卡按 14、A3 真图按 56。

### Patch 1：`projects/26-BQ-PARK/05_output/style/style_card.svg`

**只改 `<defs>` 里两个 marker 定义**，其他元素不动。

把：

```xml
<marker id="arrow-vehicle" markerWidth="3.8" markerHeight="3" refX="3.4" refY="1.5" orient="auto" markerUnits="strokeWidth" overflow="visible">
  <path d="M0,0 L3.4,1.5 L0,3 Z" fill="#E88A33"/>
</marker>
<marker id="arrow-pedestrian" markerWidth="3.4" markerHeight="2.6" refX="3" refY="1.3" orient="auto" markerUnits="strokeWidth" overflow="visible">
  <path d="M0,0 L3,1.3 L0,2.6 Z" fill="#65AFC4"/>
</marker>
```

替换为：

```xml
<marker id="arrow-vehicle"
        viewBox="0 0 10 10"
        markerWidth="14" markerHeight="14"
        refX="10" refY="5"
        orient="auto"
        markerUnits="userSpaceOnUse">
  <path d="M0,0 L10,5 L0,10 z" fill="#E88A33"/>
</marker>
<marker id="arrow-pedestrian"
        viewBox="0 0 10 10"
        markerWidth="14" markerHeight="14"
        refX="10" refY="5"
        orient="auto"
        markerUnits="userSpaceOnUse">
  <path d="M0,0 L10,5 L0,10 z" fill="#65AFC4"/>
</marker>
```

**不要改**：所有 `<path>` / `<line>` 元素的 `stroke-width`、`marker-end` 引用、坐标。3 处 marker-end 用法（line 53、57、78）会自动用新 marker 显示。

### Patch 2：`docs/agent_drawing_protocol.md` 新增"SVG 箭头标准"段

在原文 §3"SVG 元素白名单"和 §4"几何翻译"之间插入新段：

````markdown
## 3.5 SVG 箭头标准

所有 `<marker>` 必须用 **`userSpaceOnUse` + `viewBox`** 归一化模板，保证箭头视觉重量跟线宽解耦：

```xml
<marker id="arrow-{object_type}"
        viewBox="0 0 10 10"
        markerWidth="{W}" markerHeight="{W}"
        refX="10" refY="5"
        orient="auto"
        markerUnits="userSpaceOnUse">
  <path d="M0,0 L10,5 L0,10 z" fill="{color}"/>
</marker>
```

### markerWidth 按画布尺寸

| 画布 | 短边 | markerWidth |
|---|---|---|
| A3 真图 (4960×3508) | 3508 | **56** |
| A4 真图 (3508×2480) | 2480 | **40** |
| 800×600 样卡 | 600 | **14** |

公式：`markerWidth = round(canvas_short_dim / 60)`。

### 禁止

- ❌ 不用 `markerUnits="strokeWidth"`（会让细线箭头变小，图例 / 主图视觉不一致）
- ❌ 不省略 `viewBox`（会让 path 坐标和 markerWidth 隐性耦合，难维护）
- ❌ 不用 path 坐标值≠ 10 × 10 范围（其他模板的 viewBox 坐标系不要换）
- ❌ 不为不同 object_type 用不同 markerWidth（同一画布所有箭头同尺寸）

### 双端箭头

`vehicle_flow` 在启泰风格里两端都有箭头。SVG 写法：定义两个 marker（`arrow-X-start` 和 `arrow-X-end`，path 镜像），或用单 marker + `marker-start` + `marker-end` + `orient="auto-start-reverse"`：

```xml
<marker id="arrow-vehicle"
        viewBox="0 0 10 10"
        markerWidth="56" markerHeight="56"
        refX="10" refY="5"
        orient="auto-start-reverse"
        markerUnits="userSpaceOnUse">
  <path d="M0,0 L10,5 L0,10 z" fill="..."/>
</marker>

<path d="..." marker-start="url(#arrow-vehicle)" marker-end="url(#arrow-vehicle)"/>
```

`orient="auto-start-reverse"` 让同一 marker 既能贴在 path 起点（自动反转方向）也能贴在终点。
````

### 不动

- ❌ `projects/26-BQ-PARK/05_output/style/style_spec.json`（问题在表达层不在 token 层）
- ❌ `approved_at`（继续保持 null）
- ❌ 其他 svg 元素 / 字段
- ❌ 其他 skill / schema / validator

### 验证

codex 改完两个文件后：

1. mac 端用 rsvg-convert 渲染：

```bash
rsvg-convert -w 1600 projects/26-BQ-PARK/05_output/style/style_card.svg -o /tmp/style_card_v2.png
```

（codex 在 Windows 上若 Cairo 缺，跳过本机渲染，用浏览器开 svg 看也行）

2. 文字描述验证（不传图）：

- 主线 vehicle_flow 箭头是否清晰可见、形态正常？
- 同样的 arrow-vehicle marker 在图例（line 78，stroke=4）里是否跟主图（line 53，stroke=5.2）**视觉同样大小**？
- arrow-pedestrian 箭头是否清晰？

如果三处箭头视觉一致 = 通过。

3. 回执贴：
   - commit hash
   - rsvg-convert 输出（或浏览器看的描述）
   - 三处箭头是否视觉一致的判断

### 完成定义

- 两份 patch 已 commit
- 验证三处箭头视觉一致
- 用户能在浏览器或 PNG 上看到正常箭头
- BQ-PARK style_spec 仍是 draft，等用户后续批准 / 改

### Stage 7 风险消除

`agent_drawing_protocol.md` 加了箭头标准段后，真图（A1/A2）出图时按 markerWidth=56 套用同样模板，**不会重复本轮的失误**。

### 边界

- 仅 BQ-PARK 样卡 + protocol，不动其他项目
- 不在 Stage 6 批准前进入 Stage 7

### 开工

直接做 Wave SVG-Arrow Fix。
