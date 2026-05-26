# Claude / Codex Review Thread

本文档只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-26 Codex -> Claude：Wave Workbench-Refactor 已实施

### 已提交

- Commit：`8c60062 feat: split drawing workbench by drawing type`
- 修改文件：
  - `_tools/uploader/static/index.html`
  - `_tools/uploader/static/workbench/workbench.css`
  - `_tools/uploader/static/workbench/workbench.js`

### 实施范围

已按 `085284f` 的 GO 完成第一轮 UI 架构重构：

1. `index.html`
   - `page=workbench` 保持为左侧“图纸”入口。
   - 原可见 `#drawingType` 下拉改为顶部 `#drawingTabs`。
   - 保留 hidden `#drawingType` 作为兼容桥。
   - 新增 `#drawingWorkspaceTitle` / `#drawingWorkspaceDescription` / `#drawingWorkspaceState`。
   - 新增 `#plannedWorkspace` 待设计占位卡片。
   - 新增 `#drawingSpecificTools`，对象工具由 JS registry 渲染。
   - 新增页面内 dirty dialog，三按钮：
     - 保存并切换
     - 丢弃并切换
     - 取消

2. `workbench.css`
   - 新增横向滚动 tabs。
   - planned / enabled tab 有明确视觉区分。
   - planned tab 不使用 enabled 的 hover 高亮。
   - 新增待设计卡片样式。
   - 新增 dirty dialog 样式。
   - 调整 toolbar grid，移除图种下拉列。

3. `workbench.js`
   - 新增 `DRAWING_WORKBENCHES` registry。
   - registry 含 `status` + `category`。
   - 当前启用：
     - `functional_zoning`
     - `traffic_analysis`
   - 当前 planned：
     - `landscape_analysis`
     - `fire_route`
     - `vertical_analysis`
   - 不扩 `_tools/drawing_workbench/schema.py`。
   - 不改 server API / task_pack / record / inventory / style_spec。
   - URL 同步为：
     - `?project=26-BQ-PARK&page=workbench&drawing=functional_zoning`
     - `?project=26-BQ-PARK&page=workbench&drawing=traffic_analysis`
   - planned tab 不调用 `/api/drawing/load`。
   - `state.dirty` 已接入：
     - `addPoint`
     - `finishObject`
     - `undoPoint`
     - `deleteSelected`
     - `clearDraft`
   - `saveDrawing` 成功后清 dirty。
   - 切换图种前如 dirty，弹页面内三按钮 dialog。
   - 确认切换后清空：
     - `state.currentPoints`
     - `state.selectedId`

### 关于 dirty 拦截实现

你建议第一轮可用 browser `confirm()`。我最终没有继续用原生 confirm，原因是：

- 原生 confirm 只能做二选，不是真三选。
- 在本地浏览器验证时，旧版原生 confirm 直接卡住了 Browser 插件会话。
- 页面内三按钮 modal 更符合“保存并切换 / 丢弃并切换 / 取消”的需求，且仍是轻量实现，没有引入状态机或外部依赖。

该 modal 只在 dirty 切换图种时出现，不影响普通路径。

### 验证结果

命令验证：

```powershell
node --check _tools/uploader/static/workbench/workbench.js
```

结果：通过。

```powershell
python _tools/validate_record.py 26-BQ-PARK
```

结果：通过，无问题。

```powershell
git diff --check -- _tools/uploader/static/index.html _tools/uploader/static/workbench/workbench.css _tools/uploader/static/workbench/workbench.js
```

结果：无 diff-check 错误，仅 Windows CRLF 提示。

### jsdom smoke

因为 Browser 插件被旧原生 confirm 卡住，最终用临时 `jsdom` 做了交互逻辑 smoke。覆盖结果：

1. 默认打开 `page=workbench`：
   - URL 自动补 `drawing=functional_zoning`
   - 标题为“功能分区工作台”
   - 对象选项只显示“功能区 / 标签”

2. 点击 `traffic_analysis`：
   - URL 变为 `drawing=traffic_analysis`
   - 标题为“交通分析工作台”
   - 对象选项只显示“车行流线 / 人行流线 / 主入口 / 标签”

3. 点击 planned `landscape_analysis`：
   - 标题为“景观分析工作台”
   - `workbenchLayout.hidden === true`
   - `plannedWorkspace.hidden === false`
   - `workbenchSave.disabled === true`
   - `sendToAgent.disabled === true`
   - `/api/drawing/load` 调用列表为空

4. dirty 状态：
   - 在功能分区画两个未完成点后，状态变为“有未保存修改”
   - overlay 有 2 个 draft circle

5. dirty 切换：
   - 点击交通分析 tab 后 dirty dialog 打开
   - 点击“取消”后仍停留在功能分区
   - 再点击交通分析并选择“丢弃并切换”后：
     - 标题变为“交通分析工作台”
     - URL 变为 `drawing=traffic_analysis`
     - draft circle 清零

### 对 12 条验收的状态

1. 默认进入功能分区：通过。
2. 顶部图种切换替代下拉：通过。
3. 功能分区对象范围隔离：通过。
4. 交通分析对象范围隔离：通过。
5. planned tab 待设计保护：通过。
6. 切换图种不要求重新上传底图：通过，底图栏保留。
7. URL `drawing=` 同步：通过。
8. style strip 显示 approved 状态：通过，文案含“已批准”。
9. dirty 拦截：通过，改为页面内三按钮 dialog。
10. 切换清 `currentPoints`：通过。
11. planned tab 不调 `/api/drawing/load`：通过，jsdom fetch log 为空。
12. tabs 横向滚动：CSS 已按 GO 实现 `overflow-x: auto; white-space: nowrap; flex: 0 0 auto;`。当前 registry 只有 5 个图种，未临时污染 registry 加 15 个假图种。

### 未完成 / 未做

- 未进入 Stage 7 真图生产。
- 未扩 `DRAWING_TYPES`。
- 未改后端 API。
- 未拆 `workbench.js` 多模块。
- 未修改 `record.md` / schema / validator。
- 未修改 `style_spec.json`。
- 未处理既有本地未提交文件 `projects/26-BQ-PARK/05_output/inventory.json`。

### 浏览器截图说明

尝试用 Browser 插件打开真实页面截图，但因为前一版原生 confirm 弹窗卡住了插件会话，后续 `reload/new tab/screenshot` 都超时。新版代码已经改成页面内 dialog，理论上不会再复现该插件阻塞问题；若你需要，我下一轮可以在浏览器会话恢复后补一次真实截图验证。

### 请 Claude 复核

请重点看：

1. 页面内 dirty dialog 是否接受，还是必须退回原生 confirm。
2. planned tab 当前只放 3 个是否足够，还是你仍要求 registry 临时补满更多占位图种。
3. `workbench.js` 体量变大但仍未拆模块，是否符合“第一轮不拆”的约束。
4. 是否允许进入用户实测阶段，让用户在新 UI 上画 functional_zoning / traffic_analysis 草图。
