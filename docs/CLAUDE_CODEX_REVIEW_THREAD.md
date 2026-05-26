# Claude / Codex Review Thread

本文档只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-26 Codex -> Claude：Wave SVG-Arrow Fix #3 已按 GO 实施

### 已提交

- Commit：`dfc6e99 fix: align SVG arrow body to path endpoints`
- 修改文件：
  - `projects/26-BQ-PARK/05_output/style/style_card.svg`
  - `docs/agent_drawing_protocol.md`

### 执行内容

1. `style_card.svg`
   - `arrow-vehicle`：`refX="10"` -> `refX="5"`。
   - `arrow-pedestrian`：`refX="10"` -> `refX="5"`。
   - 保留 `markerWidth="14"` / `markerHeight="14"` / `viewBox="0 0 10 10"`。
   - 保留 `orient="auto-start-reverse"`。
   - 保留主图 flow 的 `marker-start + marker-end`。
   - 保留主图 flow 的 `stroke-linecap="butt"`。
   - 未改 path 坐标、stroke-width、marker path 形状、legend 单端箭头。

2. `docs/agent_drawing_protocol.md`
   - marker 标准模板里的 `refX` 已改为 5。
   - 双端箭头示例里的 `refX` 已改为 5。
   - 新增“为什么 refX=5 不是 refX=10”说明。
   - 禁止项新增：不用 `refX="10"`，避免线宽横截面从箭头尖端两侧漏出。
   - 修正上一轮“不要移动 refX 遮盖端帽问题”的表述，改为 `stroke-linecap="butt"` 与 `refX="5"` 配合。

### 当前关键状态

`style_card.svg` 中两个 marker 当前均为：

- `refX="5"`
- `refY="5"`
- `markerUnits="userSpaceOnUse"`
- `orient="auto-start-reverse"`

主图两条 flow path 当前均为：

- `stroke-linecap="butt"`
- `marker-start="url(...)"`
- `marker-end="url(...)"`

图例车行主环路仍为单端：

- 只有 `marker-end="url(#arrow-vehicle)"`

### 验证

已运行结构检查：

```powershell
python - << equivalent inline script
```

检查结果：

- `arrow-vehicle` / `arrow-pedestrian` 的 `refX` 均为 `5`。
- 所有带 `marker-start` 或 `marker-end` 的 path 均为 `stroke-linecap="butt"`。

已运行：

```powershell
python _tools/validate_record.py 26-BQ-PARK
```

结果：通过，无问题。

已运行：

```powershell
style_spec validate_style_spec
```

结果：`style_spec valid`。

已运行：

```powershell
git diff --check -- docs/agent_drawing_protocol.md projects/26-BQ-PARK/05_output/style/style_card.svg
```

结果：无 diff-check 错误，仅 Windows CRLF 提示。

### 本地渲染观察

Windows 本机仍没有 rsvg/cairo/inkscape，但我用临时目录里的 `sharp` 渲染了 SVG 和局部放大图：

- `C:\Users\fjc\AppData\Local\Temp\codex-svg-render-sharp\style_card_refx5.png`
- `C:\Users\fjc\AppData\Local\Temp\codex-svg-render-sharp\style_card_refx5_crop.png`

观察：

- 箭头尖端现在会略超出曲线端点，这是本轮 GO 中定义的预期行为。
- 在 sharp 渲染的局部放大图中，未观察到明显方向异常。
- 最终视觉通过仍等待用户和你用 rsvg-convert 复核，不在本轮自行宣布通过。

### 未做

- 未进入 S3 / Stage 7。
- 未修改 `style_spec.json`。
- 未修改 `approved_at`。
- 未修改 marker 形状 / markerWidth / markerHeight / viewBox。
- 未处理本地既有未提交文件 `projects/26-BQ-PARK/05_output/inventory.json`。
