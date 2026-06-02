# 修复计划 — S1 草稿报错 / PPT 文本撤销 / 开放路径移动（2026-06-02）

> mac claude 分析定位,codex 实施,mac claude 终审。红线见 `.trellis/spec/guides/project-conventions.md`。
> 范围:`_tools/uploader/server.py`、`_tools/s1_location_analysis.py`、`_tools/uploader/static/app.js`、`_tools/uploader/static/workbench/workbench.js`、`_tools/tests/*`、`.trellis/spec/guides/project-conventions.md`。不动功能分区(FZ)既有行为。

## 问题与根因(均已读代码确诊)

| # | 现象 | 根因(file:line) |
|---|---|---|
| F1 | S1 点"生成区位分析草稿"报"生成失败" | `s1_location_analysis.py:47-52` 强制前置 `05_output/amap/s1_map_context.json`(且状态正常),否则抛 `FileNotFoundError("...请先生成 S1 高德上下文")`/`ValueError`。`server.py:2349-2357` 把子进程异常吞成 `ok=false`;前端 `app.js:2710` 只显示笼统 `data.error || "生成失败"`。 |
| F2 | PPT 预览改图纸说明不能 Ctrl+Z | 撤销栈(`workbench.js` `pushUndoSnapshot`/`undoStacks`/`undoHistory`)只作用于 `state.objects`;PPT 文本走 `contenteditable`(`workbench.js:1230`)→ `saveDeckLayout` 改 `deckLayout.slide.text`,**未接入撤销**;重渲染还清掉原生撤销。 |
| F3 | 消防流线/转弯半径的线不能移动 | 移动绑在 `.geometry-hit[data-object-id]` pointerdown(`workbench.js:4070`);闭合图元靠**内部填充**(`pointer-events="fill"`)可抓而能移。开放路径(线段/转弯半径,kind=path/closed=false)是**细描边**,选中后被顶点+弧线中点手柄(转弯半径还有 labelbox 手柄 `workbench.js:3476`)覆盖,pointerdown 总落在手柄上(拖顶点/拉弧),抓不到线身 → 无法整体移动。**非实现不一致,是"细线无填充可抓"的交互缺陷。** |

## 修复方案

### F1 — S1 草稿报错:暴露真因 + 顺序门控
1. **暴露真实错误**:`handle_s1_auto_draft` 把三个失败点(快照生成 / 子进程 `s1_location_analysis.py` / `sync_location_analysis_drawing`)的具体错误原样回前端;前端 `summarizeAutoDraftV2`/状态条显示**具体中文原因**,不再只显示"生成失败"。
2. **前置处理**:若 `s1_map_context.json` 不存在/状态异常,要么(优先)在草稿流程里**自动先生成高德上下文**再继续;要么在按钮上**明确门控**并提示"请先生成 S1 高德上下文"。二选一,以"用户一键可用"为准。
3. **验收**:
   - [ ] 未生成高德上下文时点草稿:UI 显示明确"请先生成 S1 高德上下文"(或自动补跑后成功),**不出现笼统'生成失败'**。
   - [ ] 正常路径:草稿成功生成 `location_analysis_draft.json` + `satellite_2km.png` 并同步底图。
   - [ ] api smoke 覆盖:缺上下文→返回明确 error 文案;有上下文→ok=true。

### F2 — PPT 文本编辑接入撤销
1. PPT 预览里对图纸说明(`deckLayout.slide.text`)及版式元素的编辑,**纳入撤销/重做**:扩展撤销快照覆盖 `deckLayout`(或为 PPT 编辑单开 undo/redo 栈),Ctrl/Cmd+Z 撤销、Shift+Ctrl/Cmd+Z 重做。
2. 避免 `contenteditable` 重渲染打断:编辑提交时记快照;撤销后正确回填文本并重渲染预览。
3. **验收**:
   - [ ] PPT 预览改说明文本→Ctrl+Z 回到上一版文本;再重做可恢复。
   - [ ] 撤销不串改画布对象(两套 undo 互不污染)。
   - [ ] browser smoke 驱动:编辑文本→Ctrl+Z→断言文本回退。

### F3 — 开放路径整体移动(统一交互)
1. 给开放路径(线段/转弯半径/坡度箭头等)**一致的整体移动**:抓"线身"(非手柄处)即移动整体。实现可选:① 提高描边命中层 `pointer-events="stroke"` 的命中容差并让"移动"优先于落空;② 或加一个**专用移动手柄**(如线段中部偏移处)统一所有图元;③ 或选中态按住空格/修饰键拖动整体。**目标:闭合与开放图元移动手感一致。**
2. 不破坏现有顶点拖动 / 弧线中点拖动 / labelbox 拖动。
3. **验收**:
   - [ ] 选中一条消防流线后可整体拖动移动;转弯半径(线+标注框)可整体移动。
   - [ ] 顶点/弧线/labelbox 手柄仍各自可用,不被移动吞掉。
   - [ ] 闭合图元(多边形/圆)移动行为不变。
   - [ ] browser smoke 驱动:选中线段→拖线身→断言 geometry 整体平移(坐标位移一致)。

### F4 — 把"制图标准交互"写进项目规约
在 `.trellis/spec/guides/project-conventions.md` 新增一节「制图标准交互(强制)」:
- **撤销/重做**:所有可编辑状态(画布对象 + PPT 版式/文本)都必须支持 Ctrl/Cmd+Z / Shift+Ctrl/Cmd+Z。
- **整体移动**:任何图元(闭合/开放/标注)都必须能整体拖动移动,手感一致。
- **复制粘贴**:Ctrl/Cmd+C/V。
- 今后任何图纸工作台/编辑功能开发,默认具备且一致;缺失视为未完成。

## 门禁(每条改完必须全绿)
```
python3 -m py_compile _tools/uploader/server.py _tools/s1_location_analysis.py _tools/drawing_workbench/*.py
node --check _tools/uploader/static/app.js _tools/uploader/static/workbench/workbench.js
python3 _tools/tests/drawing_workbench_api_smoke.py
python3 _tools/tests/drawing_workbench_browser_smoke.py
```
服务:`python3 _tools/uploader/server.py` → http://127.0.0.1:8765。

## 范围红线
- 不改功能分区(FZ)既有行为;现有 workbench/FZ smoke 必须继续全绿(回归即打回,禁止改测试蒙混)。
- 不提交 `projects/*/05_output/` 运行产物;不擅自加依赖(确需先说明)。
- 单线程顺序 F1→F2→F3→F4,每条一次小提交,信息清晰。有视觉自检(实际跑服务点一遍)。
