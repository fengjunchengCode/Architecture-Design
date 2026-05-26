# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-26 Codex → Claude：S10 style_card arrow marker issue needs review

### Current State

用户已启动 `26-BQ-PARK` S10 风格协商，并选择 `var_4`。

本轮测试产物均已提交并推送：

- `a548152 feat: generate BQ-PARK style vibe board`
  - `projects/26-BQ-PARK/05_output/style/vibe_board.md`
  - `projects/26-BQ-PARK/05_output/style/vibe_board/var_1.png`
  - `projects/26-BQ-PARK/05_output/style/vibe_board/var_2.png`
  - `projects/26-BQ-PARK/05_output/style/vibe_board/var_3.png`
  - `projects/26-BQ-PARK/05_output/style/vibe_board/var_4.png`
  - `projects/26-BQ-PARK/05_output/style/vibe_board/var_5.png`
- `6df3b9a feat: draft BQ-PARK style spec`
  - `projects/26-BQ-PARK/05_output/style/style_spec.json`
  - `projects/26-BQ-PARK/05_output/style/style_card.svg`
- `3a4dac7 fix: normalize BQ-PARK style card arrows`
- `902753d fix: anchor style card arrowheads`

`style_spec.json` 仍是草案状态：

- `approved_at: null`
- 未进入真图生产
- 用户尚未批准样卡

### Problem

用户连续指出 `style_card.svg` 的箭头样式不对：

1. 初版：`markerUnits="strokeWidth"` + 较大 marker，导致“线样与箭头 / 车行主环路”的箭头畸形过大。
2. 第二版：改为 `markerUnits="userSpaceOnUse"` 后，箭头变小，且视觉上没有贴在线条端点，像随意摆放。
3. 第三版：改回小比例 `strokeWidth` marker，用户仍认为没有改对。

用户担心这个问题会在后续交通流线、消防流线等技术图中反复出现，因此要求交给 Claude 分析。

当前问题不只是 BQ-PARK 样卡局部瑕疵，而是 `agent_drawing_protocol.md` / `style_card.svg` 里缺少稳定 SVG arrow marker 标准。若不明确，Stage 7 真图生产时很可能重复出错。

### Current Files To Review

- `projects/26-BQ-PARK/05_output/style/style_card.svg`
- `projects/26-BQ-PARK/05_output/style/style_spec.json`
- `docs/agent_drawing_protocol.md`
- `docs/style_spec_negotiation.md`

当前 `style_card.svg` 相关片段：

```xml
<marker id="arrow-vehicle" markerWidth="3.8" markerHeight="3"
        refX="3.4" refY="1.5" orient="auto"
        markerUnits="strokeWidth" overflow="visible">
  <path d="M0,0 L3.4,1.5 L0,3 Z" fill="#E88A33"/>
</marker>

<path d="M64 356 C120 340, 178 372, 234 352"
      fill="none" stroke="#E88A33" stroke-width="5.2"
      stroke-linecap="round" marker-end="url(#arrow-vehicle)"/>
```

### What I Need From Claude

请先做 review / 方案判断，不要直接进入大规模重构：

1. 判断 SVG 箭头应采用哪一种稳定方案：
   - `markerUnits="strokeWidth"`，但统一 marker viewport/ref/path 比例；
   - `markerUnits="userSpaceOnUse"`，但按线宽手工设置 marker 尺寸并处理 refX；
   - 放弃 `<marker>`，改为 agent 手绘 arrowhead polygon，按路径末端切线计算；
   - 其他更适合后续技术图的方案。
2. 给出一个最小可落地修法：
   - 是否只修 `style_card.svg`？
   - 是否同时要补 `docs/agent_drawing_protocol.md` 的箭头规范，避免 Stage 7 复发？
   - 是否需要补一个小型 SVG arrow test asset，专门验证不同线宽/曲线/直线端点？
3. 明确 BQ-PARK 当前 `style_spec.json` 是否需要改：
   - 我倾向不改 token，因为问题是 SVG marker 表达，不是风格 token。
4. 如果建议 codex 实施，请给出具体 patch 边界和验证方式。

### Constraints

- 不改 `record.md`
- 不 approve `style_spec.json`
- 不进入 Stage 7 真图生产
- 不改 schema / validator
- 不清理用户未提交文件

### Local Note

本地仍有历史遗留未提交改动：

- `projects/26-BQ-PARK/05_output/inventory.json`

该文件与本轮样卡问题无关，未提交。
