# 项目约定与协作红线（自动注入）

> 本仓库：面向 agent 的建筑设计工作流。核心真相 = `projects/{项目代号}/05_output/record.md`。
> 制图工作台 + PPT 出图是近期主线;背景/结构见 `docs/HANDOFF_2026-06-01_PROJECT_STATE.md`。

## 协作模型

- 出 brief + 最终审 = mac claude;实施 = mac codex(cc-relay-hub 同组 `codex-bot`);必要时一审 = codex。
- **多方向 / 同文件 / 强耦合的修改：单线程顺序做,每条一次提交。** 只有“独立模块、改不同文件、无共享状态”才考虑并行子 agent。

## 实施红线（违反即打回）

1. **门禁驱动行为,不验产物。** 验收必须驱动真实行为 / 逐像素回归,不能只断言“DOM 元素存在”。历史教训：多轮返工都栽在“只验存在性”。
2. **功能分区(FZ)是回归红线。** 任何制图/PPT 重构后,FZ 的创建/收口/选中/弧线/图例行为**逐像素不变**。
3. **不提交运行产物。** `projects/*/05_output/` 下的生成物(drawings 渲染、ppt 导出、inventory 重算)不进 git;`record.md`、用户保存的草图/预设按需保留。
4. **不擅自加重依赖**(如 `python-pptx`)——先在回复里说明、等确认。
5. **不改 `docs/CLAUDE_CODEX_REVIEW_THREAD.md`**(评审线程只 mac claude 写)。
6. 脚本必须从自身位置推导仓库根目录,不假设固定路径。
7. **制图标准动作必须可撤销/重做。** 任意 drawing/workbench/S2 类制图 UI 的移动、旋转、缩放、增删对象、属性编辑、重置等标准交互,必须支持 `Ctrl/Cmd+Z` 撤销与 `Ctrl/Cmd+Y` 或 `Ctrl/Cmd+Shift+Z` 重做；一次用户意图只入栈一次,并用浏览器 smoke 覆盖关键路径。

## 制图标准交互（强制）

- **撤销/重做。** 所有可编辑状态,包括画布对象和 PPT 版式/文本,都必须支持 `Ctrl/Cmd+Z` 撤销与 `Ctrl/Cmd+Y` 或 `Shift+Ctrl/Cmd+Z` 重做；一次用户意图只入栈一次,不得串改其他编辑域。
- **整体移动。** 任何图元,包括闭合图元、开放路径和标注,都必须能整体拖动移动；开放路径必须有足够宽松的线身命中层,手感与闭合图元一致,且不能吞掉顶点、弧线或标注手柄。
- **复制粘贴。** 图纸工作台中的可复制图元必须支持 `Ctrl/Cmd+C/V`,粘贴对象必须生成新 id,并保持几何、样式、标签等用户可见属性。
- 今后任何图纸工作台或可编辑制图功能开发,默认具备以上标准交互且行为一致；缺失任一项视为未完成,必须补浏览器 smoke 或同等级真实交互断言。

## 标准门禁（改完必须全绿）

```bash
python3 -m py_compile _tools/drawing_workbench/*.py _tools/uploader/server.py
node --check _tools/uploader/static/workbench/workbench.js
node --check _tools/uploader/static/app.js
python3 _tools/tests/drawing_workbench_api_smoke.py
python3 _tools/tests/drawing_workbench_browser_smoke.py   # 需起服务 + playwright
```
服务：`python3 _tools/uploader/server.py` → http://127.0.0.1:8765

## 每条任务的节奏

先写会失败的断言 → 跑红 → 改最小实现 → 门禁全绿 → 有视觉则实际截图自检 → 一次提交。
