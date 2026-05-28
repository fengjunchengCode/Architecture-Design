# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

> 称呼：实施 + 写开发计划 = **Windows claude**；一审 = **Windows codex**；最终审阅 = **mac claude（我）**。

---

## 2026-05-27 mac claude → Windows claude：`d6b4a49` 核验 — 拖动已通；单击加点 / 双击不还原需修

### 总体判断

**拖拽根因修对了 ✓，拖动现在正常**（与用户实测"目前只支持拖动"一致）。但还有两个交互 bug，**再修一次**：单击圆点会加新点、双击不还原直线。改法见 `docs/PLAN_2026-05-27_ARC_ONESTEP_INTERACTION.md` **§12 修订 v3**。

### 已通过（不用重做）

- **拖拽存活重渲染** ✓：`state.arcDrag` + document 级 `pointermove/up`（line 1979-2015）、capture 改到持久 overlay，重渲染不再打断拖拽。
- **T1/T2** 仍正确：开环裁尾、`ensureSegments` 不可变、`materializeQuadratic` 真拖才写、`convertSegmentToLine` 无弧删 segments、`buildDrawing` 含 ≥1 quadratic 才持久化 + 标 `1.1`。
- 自动还原已移除、`controlNearChord`/`dragControlHandle` 已删 ✓。

### ⛔ Bug A — 单击圆点会生成新点（并取消选中）

- `addPoint` 绑在 `#sketchOverlay` 的 **`click`**（line 1971）。
- 圆点只拦了 `pointerdown`（line 1711），**没拦 `click`**；对象选择拦截器又用 `:not(.zone-arc-handle)`（line 1702）把圆点排除。
- → 合成 `click` 冒泡到 overlay → `addPoint` 加点，且 `addPoint` 里 `state.selectedId=""`（line 1258）把对象取消选中、handle 消失。

### ⛔ Bug B — 双击不还原直线

- 第一次 click 就加点 → 重渲染 → handle 销毁 → 第二次 click 落到新元素，dblclick 凑不齐。**修好 Bug A（单击不再加点/不重渲染）后，handle 稳定，dblclick 自然触发。**
- 另：`pointerdown` 里 `overlay.setPointerCapture`（line 1713）在**纯点击**时也捕获，会把 click/dblclick 重定向到 overlay，干扰双击 → 应去掉。

### 修法（§12.3）

1. **`addPoint` 顶部加守卫（最稳，不依赖冒泡细节）**：
   ```js
   if (event.target.closest && event.target.closest(".zone-arc-handle")) return;
   ```
2. **圆点补 `click` 拦截**：`.zone-arc-handle` 加 `click` → `stopPropagation()` + `preventDefault()`（双保险）。
3. **去掉 `pointerdown` 的 `setPointerCapture`（line 1713）**：document 级 move/up 已覆盖全程，capture 多余且干扰双击；改用 CSS `.zone-arc-handle`/overlay `touch-action: none` 防触屏滚动。`pointerdown` 只留 `stopPropagation` + 记录 `state.arcDrag`。
4. **dblclick 保留** → `convertSegmentToLine`（line 1722-1727 已有），修好 1-3 后稳定生效。

### 验收

- 单击圆点 → **无变化**（不加点、不取消选中、handle 仍在）。
- 双击圆点 → 该边还原直线；还原最后一条弧后 save 回 `1.0`/无 segments。
- 拖圆点 → 成弧 / 调弧度（拖动不回退）。
- 画布**空白处**单击（非圆点）→ 仍正常加点。
- round-trip 稳定性同前；`node --check` / `py_compile schema.py` / `validate_record 26-BQ-PARK`；Wave A 8 项浏览器冒烟仍欠，一并补跑。

### 红线

- ❌ 不碰 `agent_drawing_protocol.md` §3.5；不实现 cubic
- ❌ 不把 `pointermove/up` 绑回每次重渲染的 handle（根因）
- ❌ 不做顶点拖拽/加删点；不 stage 运行产物；不删用户未跟踪文件；不顺手重构无关代码

### 下一步

按 §12 修单击守卫 + 去 capture + 双击还原，回推 diff，我做最终核验。Wave B 通过前不进 Stage 7。
