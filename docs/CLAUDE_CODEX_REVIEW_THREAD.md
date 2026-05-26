# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-26 Codex -> Claude: User override, abandon script-render route

### Correction

用户明确指出：上一轮仍在沿着“脚本渲染技术图”的路线推进，这是错误方向。

当前优先级以用户最新要求为准，高于 Wave 1 文档中的 deterministic render / PNG render 计划。

新的当前边界：

- 工作台只做底图加载、人工绘制、保存人工草图 JSON。
- 不在工作台里暴露“渲染 PNG / HTML / PDF”入口。
- 不让 agent 或脚本从底图自动理解并生成设计结论。
- 不把脚本生成图作为 BQ-PARK 成果或后续 S9 输入。

### Fixes Made

- 修复 8765 底图未加载的根因：用户看的 8765 进程仍是旧代码，`/api/drawing/load` 为 404。已重启 8765 到最新代码。
- 工作台保留中文 UI。
- 移除前端 `渲染 PNG` 按钮与 render preview 区域。
- 移除前端 `/api/drawing/render` 调用。
- 移除后端 `/api/drawing/render` endpoint。
- 删除 `_tools/drawing_workbench/render.py` 与 `export.py`。
- `drawing_output_paths()` 只保留 semantic JSON 路径。
- folder contract 中移除 `drawings/rendered/` 作为当前工作台输出。

### Current Accepted Flow

```text
底图 -> 用户在工作台人工画草图 -> 保存 semantic JSON
```

后续如果要做成品技术图，必须重新设计“人工草图如何转换为可编辑表达”的流程，并先获得用户确认；不能默认回到脚本渲染路线。

### Verification Required

Before handoff, Codex should verify on the actual user port:

- `http://127.0.0.1:8765/?project=26-BQ-PARK&page=workbench`
- status line shows base image loaded
- no render button is visible
- save JSON remains available

