# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-25 Claude → Codex：Workbench 两个 Bug 必修（中文化 + 自动加载底图）

### 用户实测反馈

工作台全英文 + 底图加载不出来。**两个都是真 bug**，不是用户操作问题。

### Bug 1 — UI 全英文，违反仓库中文规范

诊断：
- `_tools/uploader/static/workbench/workbench.js` 中文字符数 = 0
- `_tools/uploader/static/workbench/workbench.css` 中文字符数 = 0
- `index.html` 的 workbench section（line 283-360）heading/description/按钮/下拉/placeholder 全部英文

跟现有 uploader 其它页面（S0/S1/S2/Status）的中文规范不一致。`skills/_shared/output_style.md` 默认中文输出，UI 字符串也应当中文。

#### F1 必修清单

`_tools/uploader/static/index.html` workbench section（line 283-360）：

| 英文 | 中文 |
|---|---|
| "Drawing Workbench" (eyebrow) | "图纸工作台" |
| "Semantic drawing workbench" (h2) | "语义图纸工作台" |
| "Draw functional zoning, traffic flows..." | "在底图上手绘功能分区、交通流线、出入口和标签。工作台保存语义 JSON，并渲染 HTML/PNG 供汇报图使用。" |
| "Load drawing" 按钮 | "加载图纸" |
| "Drawing type" label | "图纸类型" |
| "Functional zoning" option | "功能分区" |
| "Traffic analysis" option | "交通组织" |
| "Base image path" | "底图路径" |
| "Save JSON" 按钮 | "保存 JSON" |
| "Render PNG" 按钮 | "渲染 PNG" |
| "Object type" | "对象类型" |
| "Functional zone" option | "功能区" |
| "Vehicle flow" option | "车行流线" |
| "Pedestrian flow" option | "人行流线" |
| "Main entrance" option | "主入口" |
| "Label" option | "标签" |
| "Geometry" | "几何类型" |
| "Polygon" / "Arrow" / "Polyline" / "Point" | "多边形" / "箭头" / "折线" / "点" |
| "Label" (input label) | "标签文本" |
| "Main entrance / leisure zone" (placeholder) | "如：主入口 / 休闲活动区" |
| "Source" | "来源" |
| "User sketch" / "Vision inferred" / "CAD extracted" | "用户手绘" / "视觉识别" / "CAD 提取" |
| "Finish object" / "Undo point" / "Delete selected" / "Clear draft" | "完成对象" / "撤销最后一点" / "删除选中" / "清空草图" |
| "Waiting for project and base image." | "等待项目和底图加载。" |
| "Select a project, then load the base drawing." | "请先选择项目，再加载底图。" |

`_tools/uploader/static/workbench/workbench.js`：

- `objectName()` 全部中文（line 67-73）
- `geometryName()` 全部中文（line 75-77）
- `setStatus()` 所有提示文字中文：
  - "Open or create a project before loading the workbench." → "请先打开或创建项目，再加载工作台。"
  - "Loaded saved semantic drawing." → "已加载已保存的语义图纸。"
  - "Loaded an empty semantic drawing." → "已初始化空白语义图纸。"
  - "Base image not found. Put it under ..." → "未找到底图。请把底图放到 05_output/drawings/base/master_plan.jpg。"
  - "Saved {path}." → "已保存：{path}"
  - "Rendered {path}." → "已渲染：{path}"
  - "Need at least N point(s) for {kind}." → "{kind} 至少需要 N 个点。"
  - "Added {label}." → "已添加：{label}"
  - "Deleted selected object." → "已删除选中对象。"
  - "Cleared current semantic sketch." → "已清空当前草图。"
  - "Open or create a project before saving." → "请先打开或创建项目，再保存。"
  - "Open or create a project before rendering." → "请先打开或创建项目，再渲染。"
- `renderObjectList()` 空状态 (line 310): "No semantic objects yet." → "还没有语义对象。"
- 默认 label fallback (line 221) 用中文 objectName

`_tools/uploader/static/index.html` line 39 tab 名：

```html
<span>图纸工作台</span>   <!-- 替换 "Workbench" 或类似 -->
```

（具体 tab DOM 结构以 codex 当前实现为准，对齐到 S0/S1/S2 tab 的中文 label 风格）

### Bug 2 — 底图加载逻辑有 race condition

后端验证：
- `/api/drawing/load?project=26-BQ-PARK&drawing_type=functional_zoning` 返回 `base_image_exists=true, base_image_url=/api/project-file?...`
- `/api/project-file?project=26-BQ-PARK&path=05_output/drawings/base/master_plan.jpg` 返回 HTTP 200 + 4.5MB JPEG

**后端没问题**。前端 `loadDrawing()` 触发时机有问题。

当前触发条件：
1. 点击 "Load drawing" 按钮
2. 改变 drawingType 下拉
3. `uploader:state` 事件 + `state.page==="workbench"` + `state.project` + `!state.drawing`

#### F2 必修：保证进 workbench tab 一定自动加载底图

**workbench.js 改动**：

```js
// 移除 listener 中的 `!state.drawing` 条件
window.addEventListener("uploader:state", (event) => {
  const newProject = (event.detail && event.detail.project) || "";
  const newPage = event.detail && event.detail.page;
  // 项目变了或者刚切到 workbench 页 → 都重新加载
  const shouldReload =
    newPage === "workbench" && newProject && (newProject !== state.project || !state.drawing);
  state.project = newProject;
  if (shouldReload) {
    loadDrawing().catch((err) => setStatus(err.message, false));
  }
});
```

理由：原来 `!state.drawing` 阻止重复加载，但也阻止了"用户切换项目/重新进 tab"时的重新加载。改成"项目变了或还没加载过"就触发。

**额外修补**：bind() 末尾的 fallback 检查（line 357-364），同样把 `!state.drawing` 移除：

```js
state.project = projectCode();
if (
  state.project &&
  window.architectureUploader &&
  window.architectureUploader.getPage &&
  window.architectureUploader.getPage() === "workbench"
) {
  loadDrawing().catch((err) => setStatus(err.message, false));
}
```

（这一段实际就是 `!state.drawing` 已经天然成立，但去掉条件让逻辑更直白）

**可观测性补丁**：在 `loadBaseImage()` 里加 console.log + setStatus 的可见追踪：

```js
function loadBaseImage(url, exists) {
  const image = $("#baseImage");
  const empty = $("#workbenchEmpty");
  console.log("[workbench] loadBaseImage", { url, exists });
  if (!exists || !url) {
    image.removeAttribute("src");
    state.loadedBaseUrl = "";
    empty.hidden = false;
    empty.textContent = "未找到底图。请把底图放到 05_output/drawings/base/master_plan.jpg。";
    setStatus("底图不存在，请先把 master_plan.jpg 放到 05_output/drawings/base/。", false);
    return;
  }
  state.loadedBaseUrl = `${url}&_=${Date.now()}`;
  image.onload = () => {
    setStatus(`底图已加载 ${image.naturalWidth}×${image.naturalHeight}。`);
    console.log("[workbench] base image loaded", image.naturalWidth, image.naturalHeight);
  };
  image.onerror = () => {
    setStatus(`底图加载失败：${state.loadedBaseUrl}`, false);
    console.error("[workbench] base image error", state.loadedBaseUrl);
  };
  image.src = state.loadedBaseUrl;
  empty.hidden = true;
}
```

`onload`/`onerror` 让用户在状态行直接看到加载成败，不用打开 devtools。

### 本轮硬约束（仍不能破）

- 不动 P0+ 安全阀代码
- 不改 schema
- 不改 record.md
- 不动 `_tools/drawing_workbench/` 后端 Python（后端没问题）
- 不改任何 API endpoint 形态
- 不重新设计 UI 布局，只本地化字符串 + 修触发逻辑

### 实施 + 回执

1. 执行 F1 + F2 两组改动
2. 跑：
   ```powershell
   python -m py_compile _tools/uploader/server.py
   node --check _tools/uploader/static/app.js
   node --check _tools/uploader/static/workbench/workbench.js
   python _tools/validate_record.py 26-BQ-PARK
   ```
3. 实测：
   - 浏览器打开 `?project=26-BQ-PARK&page=workbench` → 底图应当自动加载 + 状态行显示 "底图已加载 3393×1964"
   - 从 S2 tab 切换到工作台 → 同样底图自动加载
   - 所有 UI 文字中文
4. commit + push
5. 本文件覆盖一条简短回执：commit hash、`node --check` 输出、浏览器手测两种入口（直接 URL / 切换 tab）的状态行截图描述

### Bug 修完后立即做的事

不要回审，直接进 **Stage A 重排版**（S9 SKILL.md 增强 + 读 workbench 输出 + 生成草稿）。`0037f40` GO 仍然有效。
