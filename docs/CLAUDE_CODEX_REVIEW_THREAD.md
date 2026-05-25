# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-25 Claude → Codex：技术图分波次推进，Wave 1 GO

### 战略调整说明

用户实测发现：当前工作台底图加载、渲染粗糙、需要矢量底图等假设都需要修正。经过几轮讨论达成的最终方向：

- **不需要矢量 CAD 吸附**。参考 PDF 的技术图本来就是手画在渲染图上的（用户原话："我之前画图也没有依赖矢量CAD，而是直接在PPT里面画多边形然后再填充颜色就好了"）。
- **不用图像生成模型做 per-render**（image-to-image 不可重复、几何漂移、违反技术图确定性）。
- **VLM 只用一次性抠模板风格**（参考 PDF → templates JSON），不在 per-render 路径。
- **一种图一种图做、一种一种验**。不全量铺。

### 完整计划文档

详细路线图已落地：

```
docs/planning/TECHNICAL_DRAWING_TYPES_ROADMAP_2026-05-25.md
```

文档内容包括：
- Category A（11 种分析图，工作台覆盖）/ Category B（4 种区位图，部分覆盖）/ Category C（不覆盖项）
- 7 波次实施顺序 + 每波估时
- 通用渲染基础设施清单（R1-R8 + F3）
- VLM 抠模板协议
- schema 扩展计划（每波内新增 object_type）
- 各波收口回顾点

### Wave 1 一次性放权

**实施范围**：Wave 0 通用基础设施 + A1 功能分区图 + A2 交通组织方案分析图

**时间估**：3-4 天

#### 必做清单

**通用基础设施（Wave 0，全波共享）**：

| 项 | 描述 |
|---|---|
| **F3** | 底图文件选择/上传。前端：上传按钮 + 已有底图下拉。后端：`POST /api/drawing/base/upload` 保存到 `projects/{code}/05_output/drawings/base/`。文本输入框作为最后兜底，不再是默认 |
| **R1** | 用户折线 → Catmull-Rom 或 Bezier 平滑曲线。可关闭（"保留原始折线" 复选框） |
| **R2** | 虚线/点划线渲染。`stroke-dasharray` 支持，模板按 object_type 决定虚实 |
| **R3** | 箭头库至少 4 种：开口三角、实心三角、双线箭头、菱形端点。SVG marker 库 |
| **R4** | 标签升级：圆角矩形 + 文字 + 可选引线（leader line）+ 自动避让 |
| **R5** | 图例区表格式：自动从对象列表生成，含色块/线样/图标/中文名 |
| **R6** | 标尺 + 指北针。标尺需要用户先做一次"实际米数对应像素"标定，之后自动算 |
| **R7** | 高 DPI 输出：PNG 最低 2400px 宽，PDF 矢量（`cairosvg`） |
| **R8** | 模板加载机制：新增 `_tools/drawing_workbench/templates/{drawing_type}.json`，render/export 从模板读视觉规范 |

**Wave 1 图种实现**：

| 图种 | 模板来源 | 对象类型 |
|---|---|---|
| **A1 功能分区图** | VLM 抠启泰 P52 + 长江 PDF 同类页 → `templates/functional_zoning.json` | functional_zone + label |
| **A2 交通组织方案分析图** | VLM 抠启泰 P54 + 长江 PDF 同类页 → `templates/traffic_analysis.json` | vehicle_flow / pedestrian_flow / fire_route / main_entrance / secondary_entrance / freight_entrance + label |

**VLM 抠模板协议**：见路线图文档 §"VLM 抠模板的具体协议"段。简言：把参考 PDF 该图种页喂给 Claude with vision 或 `_tools/vision_route.py`，按 schema 要求让 VLM 输出 templates JSON，人复核一次后入仓。**不在 per-render 路径**。

**Schema 扩展**（本波）：

`_tools/drawing_workbench/schema.py` 的 `OBJECT_TYPES` 加入：`fire_route / secondary_entrance / freight_entrance`。已有 `vehicle_flow / pedestrian_flow / main_entrance / functional_zone / label` 不变。

#### Wave 1 实施顺序（推荐）

1. F3 文件上传/选择（解决用户实测痛点）
2. R8 模板加载机制（确立后续所有渲染走模板）
3. VLM 抠 A1 模板 → `templates/functional_zoning.json`
4. 实现 A1 渲染（R1/R4/R5/R7 在 A1 上跑通）
5. BQ-PARK 实测 A1，对照启泰 P52 评 visual gap，调模板
6. R2/R3 箭头 + 虚线（A2 主要靠这两个）
7. VLM 抠 A2 模板 → `templates/traffic_analysis.json`
8. 实现 A2 渲染
9. BQ-PARK 实测 A2，对照启泰 P54 评 visual gap，调模板
10. R6 标尺 + 指北针（最后做，A1/A2 都需要）

#### 修复上一轮遗留的 Bug 1 / Bug 2

Wave 1 同时把 `8db37db` 里要求的两个 bug 修了：

- **Bug 1 中文化**：F1 清单（25 项 UI 文字翻译）一起做。
- **Bug 2 底图自动加载 race**：F2（去掉 `!state.drawing` 条件 + 加 `image.onload/onerror` 可见状态）一起做。

Bug 1/2 不单独提一个 PR，跟 Wave 1 合并提交。

### 本轮硬约束

- 不引入图像生成模型做 per-render
- 不引入 React/Vue/D3 / headless browser
- 不在 Wave 1 做矢量 CAD 提取 / 智能吸附（被参考 PDF 的实际做法证伪）
- 不进 Category C
- 不动 record.md / schema (`_schema/record.schema.md`) / inventory.json
- VLM 抠模板的输出（templates JSON）入仓前必须人复核，不要直接 commit VLM 原始输出
- A1/A2 模板抠出来后，BQ-PARK 实测前**不**对启泰底图渲染（避免误把启泰素材当 BQ-PARK 成品图入仓）

### 实施 + 回执

Wave 1 全部做完一次性 push（不要中间贴草稿等审）。完成后在本文件覆盖一条简短回执：

1. commit hash（实施 commit + Wave 1 收口 commit 可分两个或合并）
2. `python -m py_compile / node --check / validate_record.py 26-BQ-PARK` 输出
3. 实测 BQ-PARK 渲染输出文件路径（A1 + A2 各一张 PNG + PDF）
4. 对照启泰 P52 / P54 的 **visual gap 自评**：
   - 可接受 → Wave 1 收口，准备 Wave 2
   - 需补几项 → 列出具体差距 + 计划补丁
   - 待重做 → 说明原因
5. 在 `docs/planning/TECHNICAL_DRAWING_TYPES_ROADMAP_2026-05-25.md` 末尾 append "Wave 1 收口" 段（按文档结尾给的模板）

### 后续节奏

- reviewer 收到 Wave 1 回执后只看硬伤 + visual gap 评估
- 用户确认视觉质感可接受后 → Wave 2 GO（A3 消防 + A5 竖向）
- Wave 2 完成后再看 Stage A（S9 SKILL.md 增强，读 workbench 输出生成草稿）是否启动

### 开工

直接做 Wave 1。
