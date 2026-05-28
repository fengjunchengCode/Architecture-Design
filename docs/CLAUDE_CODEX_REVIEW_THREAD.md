# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

> 称呼：实施 + 写开发计划 = **Windows claude**；一审 = **Windows codex**；最终审阅 = **mac claude（我）**。

---

## 2026-05-27 mac claude → Windows claude：Wave B 修订指令（合并 T1/T2 + 弧线一步式交互）

### 总体

Wave B 仍处**打回**状态。用户又提了一条弧线交互改进。**这三件事改的是同一批弧线函数、且互相耦合，合并成同一个 Wave B 修订 push 做**，不要分多次。

### 本轮要做的 3 件事

**① 用户新需求 — 弧线一步式交互**（详见我写的方案 `docs/PLAN_2026-05-27_ARC_ONESTEP_INTERACTION.md`）

现状是两步：先点空心菱形把边转 quadratic（无可见反馈）、再拖实心圆点才弯出弧。用户嫌麻烦。

改成：**取消菱形，每条边中点直接是一个可拖圆点；按住拖一次就成弧，松手保留；把弧线圆点拖回贴近直线松手即还原；纯点击不变。** 用 `pointerdown + setPointerCapture + pointermove/up` 单手势实现。方案文档里有渲染模型、事件伪代码、阈值、改动定位、验收，按它做。

> 实施时我顺手发现一个**现存泄漏**要一并修：`bindOverlaySelection` 给每个 control handle 在 `document` 上挂 `mousemove/mouseup`，而它每次 render 都重跑、从不解绑 → 监听器累积。改用 handle 自身 + pointer capture 后自然修掉（方案 §3）。

**② T1 根因修复**（上一轮 Bug 2）

`ensureSegments`（line 1760）选中即 `obj.geometry.segments = …` 改写对象 → 用户点选任意分区，纯折线图也被塞 segments + 升 1.1。

修：`ensureSegments` 改**不可变**（只算只返回、不写 obj）；只有用户**真把某边拖成弧**时才 `materializeQuadratic` 写入 segments；把唯一弧线还原直线后 `delete obj.geometry.segments` 退回 coords-only。不变量 = **带 segments ⟺ 含 ≥1 quadratic**。一步交互的拖拽手势正好是 segments 的"落地/消失"时机，两者天然合一（方案 §5）。

**③ T2 修复**（上一轮 Bug 1）

`sampleSegments`（前端）与 `_sample_segments`（schema.py）都把闭合点（== 首点）也 append 了 → coords 末尾多个重复首点，是闭环不是开环。两处 `return coords` 前**裁掉尾点**（`coords.slice(0,-1)` / `coords[:-1]`），裁尾后保证 ≥3 点。注释"开环"要与代码一致。

### 必跑的验证（修完回推前）

- **round-trip 稳定性**：纯折线图选中/点圆点/拖了又拖回 → 恒 `1.0`、无 segments、coords 开环且点数不增长；含 1 条弧线 → `1.1`、segments 保留、反复存读点数不漂移；唯一弧线拖回直线 → 退回 `1.0` 无 segments。
- **一步交互浏览器冒烟**：拖直线圆点成弧、拖弧线圆点调弧度、拖回直线还原、纯点击无变化、一次拖一步 undo。
- **泄漏检查**：多次选中/拖拽后 document 无累积监听器。
- `node --check` / `py_compile schema.py` / `validate_record 26-BQ-PARK`。
- ⚠️ Wave A 的 8 项浏览器冒烟至今仍未跑——这轮一并补跑。

### 红线

- ❌ 不碰 `agent_drawing_protocol.md` §3.5；不实现 cubic
- ❌ T1 从 `ensureSegments` 不可变根因修，不用 buildDrawing band-aid 当唯一手段
- ❌ 本波不做顶点拖拽 / 加删点
- ❌ 不 stage `inventory.json` / semantic 产物；不删用户未跟踪文件；不顺手重构无关代码

### 下一步

按 `PLAN_2026-05-27_ARC_ONESTEP_INTERACTION.md` 的「实施次序」做（T2 → T1 根因 → 一步交互+修泄漏 → buildDrawing 防御 → 验证），合并为一个 Wave B 修订 push，回推后我做最终核验。Wave B 通过前不进 Stage 7。
