# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-26 Claude → Codex：Wave SVG-Arrow Fix #2 GO（双端箭头）

### 诊断

我用 rsvg-convert 渲染了 `c6dbb8d` 后的样卡。**marker 尺寸和视觉一致性已经修好**（用户反馈和我的复核都确认），但留了一个语义问题：

**流线只有右端有箭头，左端是裸断**。

参考 qitai P54 实物：流线（vehicle_flow / pedestrian_flow）两端都有箭头，表示双向流动。这是这类技术图的标准画法。当前样卡 `marker-end="url(#arrow-vehicle)"` 只是单端，违反 qitai 风格语义。

**根因**：我上一份 GO（`5a04ef6`）写得太窄，明确说"不要改 path / line / marker-end 引用"，导致 codex 没机会补 marker-start。这次明确放开。

### Patch 1：`projects/26-BQ-PARK/05_output/style/style_card.svg`

#### 改动 A：两个 marker 的 orient

把 `arrow-vehicle` 和 `arrow-pedestrian` 的 `orient="auto"` 都改成 `orient="auto-start-reverse"`。这样同一个 marker 既能贴在 path 起点（自动反转方向）又能贴在 path 终点。

#### 改动 B：line 63 主图 vehicle_flow 加 marker-start

把：
```xml
<path d="M64 356 C120 340, 178 372, 234 352" fill="none" stroke="#E88A33" stroke-width="5.2" stroke-linecap="round" marker-end="url(#arrow-vehicle)"/>
```
改成：
```xml
<path d="M64 356 C120 340, 178 372, 234 352" fill="none" stroke="#E88A33" stroke-width="5.2" stroke-linecap="round" marker-start="url(#arrow-vehicle)" marker-end="url(#arrow-vehicle)"/>
```

#### 改动 C：line 67 主图 pedestrian_flow 加 marker-start

把：
```xml
<path d="M64 416 C124 404, 172 432, 232 414" fill="none" stroke="#65AFC4" stroke-width="4.0" stroke-linecap="round" marker-end="url(#arrow-pedestrian)"/>
```
改成：
```xml
<path d="M64 416 C124 404, 172 432, 232 414" fill="none" stroke="#65AFC4" stroke-width="4.0" stroke-linecap="round" marker-start="url(#arrow-pedestrian)" marker-end="url(#arrow-pedestrian)"/>
```

#### 不动

- **legend 单端保留**（line 88 周边的图例条目）：图例只是表达"这是个流线 / 这种线型"，单端是合理的、清晰的，不要画双端
- line 65 的 dashed secondary 线：原本就没箭头，继续没箭头
- 其他所有元素

### Patch 2：`docs/agent_drawing_protocol.md` §3.5"双端箭头"段升级

把现有"双端箭头"小节从"可选写法"升级为"flow 类对象的默认要求"。把整段替换为：

````markdown
### 双端箭头（flow 类默认要求）

技术图里所有 **flow 类对象**默认双端箭头，单端是例外：

| 对象类型 | 默认双端 | 例外 |
|---|---|---|
| `vehicle_flow` | ✅ | 单向出入口短段可单端 |
| `pedestrian_flow` | ✅ | 同上 |
| `freight_flow` | ✅ | 同上 |
| `underground_flow` | ❌（默认单端，指向地库入口） | — |
| `fire_route` | ✅ | — |

**图例条目里允许单端**：图例只表达"这是一种流线"，不需要展示双向语义。

实现方式：所有 flow 类 marker 用 `orient="auto-start-reverse"`，path 同时挂 `marker-start` 和 `marker-end`：

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

`orient="auto-start-reverse"` 让同一 marker 既能贴在 path 起点（自动反转方向）也能贴在终点，不需要定义 `arrow-start` 和 `arrow-end` 两份。

### Stage 7 出真图时

agent 翻译 sketch.json 到 SVG 时，凡 object_type ∈ {vehicle_flow, pedestrian_flow, freight_flow, fire_route} 的 path，自动套用上面的 marker-start + marker-end 双端模式。不需要用户在草图里特意标"两端有箭头"。
````

### 不动

- ❌ `projects/26-BQ-PARK/05_output/style/style_spec.json`
- ❌ `approved_at`（继续保持 null）
- ❌ legend 区域的单端箭头
- ❌ 任何其他文件

### 验证

完成后 codex：

1. 提交 commit
2. mac 端我会 rsvg-convert 渲染复核
3. 视觉判断：主图两条流线（橙、青）是否**两端都有箭头**？图例的车行主环路线是否**仍是单端**？
4. 三处箭头视觉重量是否一致（沿用上一波的 marker 尺寸标准）？

回执贴：
- commit hash
- 文字描述（不传图）：路径 line 63 / 67 / 88 当前的 marker-start / marker-end 状态
- 是否注意到任何 marker-start 让箭头位置漂移的副作用

### 完成定义

- 两处 path 加 marker-start，markers orient 改 auto-start-reverse
- protocol §3.5 双端箭头段升级到默认要求
- 三处验证视觉自检 OK

### 开工

直接做 Wave SVG-Arrow Fix #2。
