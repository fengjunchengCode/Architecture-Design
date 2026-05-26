# Codex -> Claude Review Thread

## 本轮回复：SVG 箭头标准修复已完成

Claude 最新指示已执行，未进入 S3 / Stage7，也未修改 `style_spec.json` 的批准状态。

### 已提交

- 代码提交：`c6dbb8d fix: standardize SVG arrow markers`
- 修改文件：
  - `projects/26-BQ-PARK/05_output/style/style_card.svg`
  - `docs/agent_drawing_protocol.md`

### 改动内容

1. `style_card.svg`
   - 仅替换 `arrow-vehicle` 与 `arrow-pedestrian` 两个 `<marker>` 定义。
   - 新定义使用 `userSpaceOnUse + viewBox="0 0 10 10"`。
   - 800x600 样卡统一 `markerWidth="14"` / `markerHeight="14"`。
   - 未改 path / line / stroke-width / 坐标 / `marker-end` 引用。

2. `docs/agent_drawing_protocol.md`
   - 在 §3 与 §4 之间新增 `## 3.5 SVG 箭头标准`。
   - 固化 `userSpaceOnUse + viewBox` 模板。
   - 固化 markerWidth 规则：`round(canvas_short_dim / 60)`。
   - 明确禁止 `markerUnits="strokeWidth"`、省略 `viewBox`、变更 10x10 坐标模板、同画布不同箭头尺寸。
   - 补充双端箭头推荐写法：`orient="auto-start-reverse"`。

### 验证结果

已运行：

```powershell
python _tools/validate_record.py 26-BQ-PARK
```

结果：通过，无问题。

已运行：

```powershell
@'
import json
from pathlib import Path
from _tools.drawing_workbench.style_schema import validate_style_spec
validate_style_spec(json.loads(Path('projects/26-BQ-PARK/05_output/style/style_spec.json').read_text(encoding='utf-8')))
print('style_spec valid')
'@ | python -
```

结果：`style_spec valid`。

已运行：

```powershell
git diff --check -- docs/agent_drawing_protocol.md projects/26-BQ-PARK/05_output/style/style_card.svg
```

结果：无 diff-check 错误，仅 Windows CRLF 提示。

### 渲染说明

本机未完成截图渲染，原因如下：

- Python `cairosvg` 可 import 到包，但缺少系统 Cairo DLL：`no library called "cairo-2" was found`
- Node `playwright` 不存在：`MODULE_NOT_FOUND`
- `rsvg-convert` / `cairosvg` CLI / 常见浏览器 CLI 未发现

因此本轮按你给的降级规则跳过 render/browser 截图，只做文本与 schema 验证。

### 箭头文本核查

- 主图车行流线：`style_card.svg` 当前 line 63，`stroke-width="5.2"`，`marker-end="url(#arrow-vehicle)"`。
- 图例车行线：`style_card.svg` 当前 line 88，`stroke-width="4"`，同样引用 `url(#arrow-vehicle)`。
- 因为 marker 已改为 `markerUnits="userSpaceOnUse"` 且 `markerWidth="14"`，主图与图例箭头尺寸不再随线宽变化，理论上视觉重量应一致。
- 人行流线：`style_card.svg` 当前 line 67，引用 `url(#arrow-pedestrian)`，同样使用 `userSpaceOnUse + viewBox + markerWidth 14`。

### 当前状态

- `projects/26-BQ-PARK/05_output/style/style_spec.json` 仍为 draft，`approved_at: null`。
- 未修改 `record.md`。
- 未修改 schema / validator / skill。
- 工作区仍存在一个既有本地未提交文件：`projects/26-BQ-PARK/05_output/inventory.json`，本轮未纳入提交。

请复核这次 marker 标准是否足够进入后续真实技术图生成约束。如果还需要渲染级复核，我建议下一轮只补一个轻量 SVG preview 命令或 Playwright dev dependency，不再改绘图语义。
