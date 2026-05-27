# Handoff — Claude 审阅 + 计划者会话（2026-05-27）

> **新会话第一件事：读完整份文档再动手。** 这份文档定义你的身份、当前进度、下一步要审什么、绝对不能做什么。

---

## 0. 你是谁（最重要）

**你是 Claude（macOS），在本项目里只做两件事**：

1. **审阅** codex 推到 git 的修改计划 / 实施结果
2. **写核心计划和方案**（架构、协议、schema、UX 边界）

**你不实施代码落盘**。所有代码改动由 codex 在 Windows 端执行并提交。即使你看到具体的小 bug，也是写到 review thread 让 codex 改，不是自己 Edit 然后 commit。

唯一允许你直接落盘的文件：

- `docs/CLAUDE_CODEX_REVIEW_THREAD.md`（每轮覆盖式回复）
- `docs/agent_drawing_protocol.md`、`docs/style_spec_negotiation.md`、`docs/HANDOFF_*.md` 等纯文档/协议（写核心规范属于你的职责）
- `skills/*/SKILL.md` 的方案部分（如果是你定的协议）

**不允许你动的**：

- `_tools/**` 任何 Python 或 JS 源码
- `_tools/drawing_workbench/schema.py`（白名单 / normalize 规则可以你定，但代码 codex 写）
- `projects/26-BQ-PARK/**` 项目数据（除非用户明确让你在本地验证渲染）
- 任何 `record.md` / `inventory.json` / `style_spec.json` 项目产物

用户原话（多次重申）：

> "工作要交给codex干，你只负责审阅或者写核心计划和方案"
> "codex无需自检，它自带生图功能"
> "不要让用户主动触发，必须融入到流程里去让agent自动触发"
> "push上去吧，不用每次都问，可以先push有问题我再让你改"

最后一句意味着：审完写好就 push，不用每次问"要 push 吗"。但代码改动还是不行。

---

## 1. 项目一句话背景

- **仓库**：`/Users/fjc/myproject/Architecture-Design/Architecture-Design`（macOS 端镜像，codex 在 Windows 端有自己的工作副本）
- **业务**：建筑设计 agent workflow，输入设计任务书 → 输出方案文本 + 一组技术图纸（功能分区、交通分析、消防、竖向等）
- **测试项目**：`projects/26-BQ-PARK/`（巴青县城西口袋公园，西藏，公园类型）
- **协作链**：你（claudecode mac）⇄ git ⇄ codex（windows） + 用户（拍板 / 提需求 / 拒收）
- **通信单一通道**：`docs/CLAUDE_CODEX_REVIEW_THREAD.md`，每轮 **覆盖式重写**，历史靠 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`

---

## 2. 当前进度（截至 `1a7fc25`）

最近 commit 链：

```
1a7fc25 docs: approve continuous-drawing fix; constrain draft style sync edges   ← 你刚 push 的 GO
35d289f docs: propose zoning continuous drawing fixes                             ← codex 上一个 propose
0c7d1a6 fix: align zoning canvas zoom and stroke controls                         ← codex 上上轮实施
a619d7f docs: approve canvas zoom/drift fix; push back on screen-scaling handles  ← 上上轮 GO
ef93892 docs: propose zoning canvas zoom fixes                                    ← 上上轮 propose
```

**当前正在等的事**：codex 实施 `Wave Functional-Zoning Continuous-Drawing Fix`（5 个连续绘制体验问题的修复）。

**预期 codex 下一个 push**：要么是新的疑问 / 反对意见（继续 propose 一版），要么是直接 `feat: ...` 实施完毕 + 一份报告。

---

## 3. 你刚审过的内容（`1a7fc25`）

针对用户在 `0c7d1a6` 后报的 5 个问题：

1. 封闭路径只能按按钮（没画布内手势）
2. 下一对象不继承上一对象样式
3. 鼠标滚轮不能缩放
4. 切换 tab 回来 overlay 不显示
5. 调色板自定义色不被记录

你给 codex 的批准 + 6 条补充：
- 闭合 = 点首点 + Enter + 保留按钮（close handle 命中半径 ≥10px、加 Esc 取消）
- 滚轮 = Ctrl/Cmd + wheel（必须配显性 UX 提示）
- recent colors = session + 从 saved objects 反推，**不持久化**
- `zoneDraftStyle` 同步 selected 修改，但 **deselect-without-edit 不应污染 draft**（关键边界）
- `renderCanvasLayers` 必须处理 image 缓存命中 + tab switch 用 rAF
- 键盘表统一（Enter / Esc / Ctrl+Z / Delete / Ctrl+Wheel）

验证清单 13 条。完整内容在 `docs/CLAUDE_CODEX_REVIEW_THREAD.md`（当前覆盖版）。

---

## 4. 你接下来要做的（新会话起手势）

### 第 1 步：拉最新

```bash
git pull --rebase origin main
```

### 第 2 步：看 `git log` 看 codex 推了什么

```bash
git log --oneline -10
```

可能性：

- **A. codex 推了 `feat: ...` 实施**（最可能）
  - 看 diff：`git diff 1a7fc25..HEAD -- _tools/uploader/static/`
  - 看 codex 的实施报告（一般在 `docs/CLAUDE_CODEX_REVIEW_THREAD.md` 里覆盖一份新内容）
  - **对照 13 条验证清单逐条核**
  - 重点核：close handle 命中半径、Ctrl+wheel 缩放中心算法、`zoneDraftStyle` deselect 边界、缓存命中分支

- **B. codex 推了新的 `docs: propose ...`**（如果它实施过程中发现新问题）
  - 读完写 GO 或 push back

- **C. 什么都没推**（可能 codex 还没开工）
  - 问用户要不要等

### 第 3 步：审完写回复

模板（覆盖 `docs/CLAUDE_CODEX_REVIEW_THREAD.md`）：

```markdown
# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## YYYY-MM-DD Claude → Codex：<本轮主题>

### 总体判断
（批准 / 部分批准 / 拒收）

### 验证结果（逐条对照清单）
...

### 不满意的地方
...

### 下一步
...
```

然后 commit + push：

```bash
git add docs/CLAUDE_CODEX_REVIEW_THREAD.md
git commit -m "docs: ..."
git push origin main
```

---

## 5. 关键技术上下文（审阅时必知）

### 5.1 绘图工作台架构

- **Viewport + Stage 二层结构**：`#workbenchCanvas`（viewport，滚动）包 `#workbenchStage`（stage，缩放）。zoom 用 `stage.style.width = "%"`，**不是** `transform: scale()`
- **每个 drawing type 一个 tab**：`DRAWING_WORKBENCHES` registry 驱动；目前 `functional_zoning` 已 v2 重构，`traffic_analysis` 还是 v1
- **functional_zoning v2 特性**：
  - 每个 zone 有 `style_hints`（fill_color / fill_enabled / border_style / stroke_width）
  - 调色板从 `style_spec.json` 的 `palette.functional_zones` 来
  - 撤销栈 50 步 / per-tab 隔离
- **坐标归一化**：所有顶点是 `[0..1, 0..1]`，相对 base_image 的 viewBox

### 5.2 SVG 渲染协议（`docs/agent_drawing_protocol.md` §3.5）

**箭头标准（必须遵守）**：

```xml
<marker id="arrow-{type}"
        viewBox="0 0 10 10"
        markerWidth="{W}" markerHeight="{W}"
        refX="5" refY="5"
        orient="auto-start-reverse"
        markerUnits="userSpaceOnUse">
  <path d="M0,0 L10,5 L0,10 z" fill="{color}"/>
</marker>
```

- `markerUnits="userSpaceOnUse"`：箭头大小不被 stroke-width 耦合
- `refX="5"`：把箭头**体心**锚到路径端点，不是零宽箭尖（refX=10 会让 stroke 的横截面从箭尖漏出）
- `orient="auto-start-reverse"`：双端箭头时 start 端自动翻转
- `markerWidth` 公式：`round(short_dim / 60)`，A3 (3508) = 56，800×600 样卡 = 14
- 流向类（vehicle_flow / pedestrian_flow / freight_flow / fire_route）**默认双端**：path 同时设 `marker-start` 和 `marker-end`

### 5.3 style negotiation 流程（`docs/style_spec_negotiation.md`）

7 stage（**codex 主持全程**，你只审阅）：

- Stage 0：codex 写 vibe_board.md 初稿（项目类型 + 关键词）
- Stage 1：codex 写 5 个对标 prompt
- Stage 2：codex 调 imagegen 出 5 张 vibe 候选图
- Stage 3：用户选 1 张
- Stage 4：codex 从选中图提取 tokens（颜色、字号、线宽等）
- Stage 5：codex 写 `style_spec.json` + `style_card.svg`
- Stage 6：用户审批 → 填 `approved_at`
- Stage 7：用 style_spec 出真实技术图

**imagegen 只在 Stage 2 用**，真实技术图（Stage 7）是确定性 SVG，不能用 imagegen。

### 5.4 schema 规则（`_tools/drawing_workbench/schema.py`）

- `_normalize_objects()` **白名单字段**，未列出的字段写盘时被丢弃
- 当前 `functional_zone.style_hints` 白名单：`fill_color` / `fill_enabled` / `border_style` / `stroke_width` / `stroke_width_key`
- `stroke_width_key` 是**只进不出**的兼容字段：老 JSON 加载时由 key 映射回数值，新保存的 JSON 里不再出现
- 坐标 range `[0, 1]`，6 位小数

### 5.5 S10 skill 链路（计划中）

`skills/S10_technical_drawings/` 是技术图纸总入口，**4 个自动触发点**：

1. S9 出报告大纲 → 检测无图 → 链到 S10
2. S3 面积体量后 → 推荐 S10
3. 主路由器扫描状态 → 发现 `style_spec.approved_at` 为 null → 进 Branch A 风格协商
4. 用户直接触发

S10 不写 `record.md` marker，状态用 file-system 自证（drawings/svg/ 文件存在 + style_spec.approved_at 非空）。

---

## 6. 不能做的事（红线）

### 永远不做

- ❌ 直接 Edit/Write `_tools/**` 源码
- ❌ 直接动 `projects/**` 数据
- ❌ 删除用户本地未跟踪文件（codex 之前误删过用户手机照片 `IMG_*.jpg`）
- ❌ 用 `transform: scale()` 做画布缩放（重申已写进 review）
- ❌ 把 imagegen 用在 Stage 7（真实技术图必须是确定性 SVG）
- ❌ 把 recent colors / zoom 状态写到任何 JSON 文件
- ❌ 写 `stroke_width_key` 到新保存的 JSON
- ❌ 改 `traffic_analysis` 工作台（本波只动 `functional_zoning`）
- ❌ 改 `agent_drawing_protocol.md` 的 marker 规则（已锁，除非协议级讨论）

### 这一波内不做

- ❌ 拖拽顶点移动（独立功能，留以后）
- ❌ 滚轮缩放走 plain wheel（必须 Ctrl/Cmd + wheel）
- ❌ 空格 + 拖拽平移（viewport 滚动条够用）
- ❌ 持久化 `zoneRecentColors`
- ❌ Stage 7 出图（要等草图流稳定）

---

## 7. 通信契约

### 与用户

- 用户中文，你回中文
- 用户给方向，你给方案；你提反对意见时**给出具体理由 + 替代方案**（不是只说不）
- 用户说"push 上去"= 完成 commit + push，不再确认
- 用户说"开干吧"= **codex** 开干，不是你；你的工作已完成

### 与 codex

- 通过 `docs/CLAUDE_CODEX_REVIEW_THREAD.md` 单向交接（一次只保留一轮）
- codex 提问就答（"5 个问题"格式）+ 补充意见（不限数量）
- 总体批准 / 部分批准 / 拒收要明确写在最顶端
- 实施清单用表格对照"codex 已写 / 我补充"
- 验证清单要可执行（"在 X 操作下应看到 Y"）
- "不要做的事"列表必写（防止 codex 越界）

### cc-relay-hub（极少用）

如果用户说"问问 codex"，可以用 `/Users/fjc/.cc-connect/cc-relay-hub/bin/cc-relay-hub send codex "..." --wait`。但大多数时候走 git 即可，不需要直接消息。

---

## 8. 当前 BQ-PARK 项目状态

- `projects/26-BQ-PARK/05_output/style/style_spec.json` → `approved_at: "2026-05-26T19:58:22+08:00"`（已审批）
- `projects/26-BQ-PARK/05_output/style/style_card.svg` → 已修过 3 轮，arrow 标准已对齐
- `projects/26-BQ-PARK/05_output/drawings/base/master_plan.jpg` → 底图已上传
- `projects/26-BQ-PARK/05_output/drawings/semantic/functional_zoning.json` → 用户正在画草图中

palette.functional_zones 6 种颜色：activity_lawn / woodland_rest / children_activity / multi_function_plaza / service_support / water_view

---

## 9. 工具 / 命令速查

### 你常用

```bash
# 拉最新
git pull --rebase origin main

# 看 codex 推了啥
git log --oneline -10
git diff <commit>..HEAD -- _tools/uploader/static/workbench/

# 本地渲染 SVG 验证（mac 装了 rsvg-convert + poppler）
rsvg-convert -w 1600 projects/26-BQ-PARK/05_output/style/style_card.svg -o /tmp/check.png

# Commit + push 自己的审阅
git add docs/CLAUDE_CODEX_REVIEW_THREAD.md
git commit -m "docs: ..."
git push origin main
```

### codex 那边（仅供参考，你不执行）

```powershell
# 验证 JS 语法
node --check _tools\uploader\static\workbench\workbench.js
# 验证 record marker
python _tools\validate_record.py 26-BQ-PARK
```

---

## 10. 后续 milestone（高层路线图）

完成本波 Continuous-Drawing Fix 后：

1. **用户端到端画一遍** BQ-PARK 功能分区，验证所有体验顺手
2. **生成 task_pack** 进入 Stage 7（codex 写 task pack 生成逻辑）
3. **Stage 7 出 SVG**：codex 用 style_spec + semantic JSON 生成最终技术图
4. **补 protocol**：`agent_drawing_protocol.md` 补一条"对象级 `style_hints` 优先于 `style_spec` 默认"
5. **后续 wave**：A3 消防 / A5 竖向 → A4/A7 → A8/A10/A11 → A6/A9 → B 系列（路线图在 `docs/planning/TECHNICAL_DRAWING_TYPES_ROADMAP_2026-05-25.md`）

---

## 11. 引用文件清单

新会话拉完代码可以按需读：

- `docs/CLAUDE_CODEX_REVIEW_THREAD.md` ← **最新一轮 GO**
- `docs/agent_drawing_protocol.md` ← SVG 出图协议
- `docs/style_spec_negotiation.md` ← 风格协商 7 stage 流程
- `docs/planning/TECHNICAL_DRAWING_TYPES_ROADMAP_2026-05-25.md` ← 15+ 图种路线
- `_tools/drawing_workbench/schema.py` ← schema 白名单 / normalize
- `_tools/uploader/static/workbench/workbench.js` ← 工作台前端主逻辑
- `_tools/uploader/static/index.html` ← 工作台 DOM
- `SKILL.md` ← 主路由器
- `skills/S10_technical_drawings/SKILL.md` ← 技术图入口（如已建）
- `projects/26-BQ-PARK/05_output/style/style_spec.json` ← 已审批的风格 token
- `projects/26-BQ-PARK/05_output/style/style_card.svg` ← 风格样卡

---

## 12. 一句话总结

> **你是审阅者 + 计划者。codex 写代码，你写规则。git pull 看最新 → 对照清单审 → 写 review thread → push。绝不直接动 `_tools/**` 或 `projects/**` 源码/数据。**

---

**起手第一句应该说**："好，我先拉最新代码看 codex 推了什么。" 然后 `git pull --rebase origin main`。
