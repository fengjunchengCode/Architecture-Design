# 项目交接摘要 — 2026-06-01

> 用途:供新上下文(新会话)快速了解项目背景、结构、进度与协作约定,以便接手开发/重构其他功能。
> 一句话:这是一个**面向 agent 的建筑设计工作流仓库**;近一周主线是**制图工作台(drawing workbench)+ PPT 出图预览**,已基本成型。

---

## 1. 项目背景

- **性质**:面向 agent 的建筑设计项目工作流仓库。可被 clone 到任意目录,所有脚本必须从自身位置推导仓库根目录(不得假设固定路径)。
- **核心真相文件**:`projects/{项目代号}/05_output/record.md` 是每个项目的唯一核心数据源。脚本只做初始化、盘点、校验、确定性计算;项目理解/字段判断/低置信标记/甲方问题由 agent 按 skill 执行。
- **开发契约**:遵守 `skills/_shared/development_contract.md`——先澄清目标、简洁优先、精准修改、目标驱动验证。
- **视觉**:JPG/PNG 区位图、现场照片优先由有视觉的主模型理解;`_tools/vision_route.py` 是无视觉时的兜底。视觉 provider 配置在根目录 `.env`(从 `.env.example` 复制)。
- **入口文档**:根目录 `README.md`、`AGENTS.md`。

## 2. 仓库结构(关键)

```
README.md / AGENTS.md / SKILL.md   # 入口与总则
_schema/                            # 数据 schema
_tools/                            # 所有脚本
  extract_text.py / inventory.py / vision_route.py / amap_context.py / s1_location_analysis.py ...
  drawing_workbench/               # 制图工作台后端(本周主线)
    registry.py    # 图纸类型 + 对象/工具注册表(单一事实来源)
    schema.py      # 语义草图 schema 校验(对象 type/geometry)
    deck_layout.py # PPT deck 排版数据层(布局/reflow/导出)
    ppt_text_markup.py # PPT 说明轻量标记解析(**小标题**/*强调*)
    style_schema.py / task_pack.py / svg_to_png.py / pdf_page_extract.py
  uploader/
    server.py      # 本地 HTTP 服务 + 所有 /api 路由
    static/
      index.html / app.js          # 主前端(S0-S2 + 工作台壳)
      workbench/workbench.js        # 制图工作台核心(绘制/选中/编辑/图例/PPT预览)
      workbench/workbench_model.js  # 样式/几何模型(normalizeStyleHints 等)
      workbench/ppt_text_markup.js  # PPT 标记前端渲染
  tests/
    drawing_workbench_api_smoke.py      # API 冒烟
    drawing_workbench_browser_smoke.py  # Playwright 浏览器冒烟(主门禁)
docs/                              # 计划 / 交接 / 评审线程(见 §6)
projects/{项目代号}/               # 各项目数据;05_output/ 下是运行产物(不进 git)
skills/                            # agent skills
```

## 3. 制图工作台 + PPT —— 当前能力(已成型)

**11 种图纸类型**(registry):`functional_zoning`(功能分区,认可的基准)、`location_analysis`(选址/区位分析)、`planting_design`、`landscape_analysis`、`traffic_analysis`、`fire_route`、`vertical_analysis`(竖向)、`supporting_facilities`、`sponge_city`、`accessibility_design`、`civil_defense`。兼容旧 ID：`elevation` -> `vertical_analysis`，`accessible_design` -> `accessibility_design`。

**绘制能力**:多边形/线段/圆形/三角形/文字/转弯半径标注/标高点/坡度箭头。统一到功能分区(FZ)的同一套:
- **单一样式模型**(`Model.normalizeStyleHints`,超集,含 functional_zone)、**单一控件渲染器**(`PRIMITIVE_STYLE_SPEC` 驱动)、**单一 SVG 渲染器**(按 geometry.kind 分支)。
- 共享交互:命中层、顶点 handle、弧线编辑(线段中点拖成弧)、选中加深、纵横比补偿(圆正圆/三角等边)、箭头随线宽、PS/PPT 式三角旋转手柄。
- 已删除"对象类型"下拉:工具直出通用几何类型;图例**按样式+标签合并**(不跟死板对象类型)。
- 样式预设:内置批次 + 用户按项目存(`05_output/drawings/presets.json`)。

**PPT 出图预览**(`deck_layout.py` + workbench.js 预览模式):
- 16:9 deck,一图一页,全局图纸框强一致;图纸左/右版式切换(改框/换版弹窗确认 + 全页标记重排)。
- 信息列**说明在上、图例在下**,随文字长度/图例数/配图数**自适应**;`reflow` 守护手动调整。
- **页标题**是固定页眉、全 deck 字体/颜色统一(`layout.title_style`);**小标题/加粗**用单一**全局品牌色**(`layout.typography_accent`,默认 `#D9882B`)——不按图纸逐图变色(依据样例 PDF)。
- 预览即编辑工作台:框位置/大小、文字字号/颜色可手调;**自动排版按钮**(reflow,带覆盖确认)。
- **PPT 轻量标记**(`ppt_text_markup`):`**小标题：**`→加粗/品牌色,`*强调*`→加粗品牌色,正文深灰;预览内编辑 + Ctrl/Cmd+B,富文本 PPTX 导出。规则见 `docs/PPT_DRAWING_TEXT_MARKUP.md`。
- **选址分析(location_analysis)**:S1 页输入/拾取 GCJ-02 中心点 → 高德上下文 + 1km/2km 天地图卫星快照 + 草稿,同步成 `location_analysis` 底图,进工作台补绘道路/水体/文字。

## 4. 如何运行 / 测试

```bash
python3 _tools/uploader/server.py            # 启动本地服务 → http://127.0.0.1:8765
```
- 制图工作台:`http://127.0.0.1:8765/?project=26-BQ-PARK&page=workbench&drawing=functional_zoning`(进去可切"PPT预览")
- 选址分析:`?project=<代号>&page=s1` 生成 → `?page=workbench&drawing=location_analysis`
- 门禁:
```bash
python3 -m py_compile _tools/drawing_workbench/*.py _tools/uploader/server.py
node --check _tools/uploader/static/workbench/workbench.js
python3 _tools/tests/drawing_workbench_api_smoke.py
python3 _tools/tests/drawing_workbench_browser_smoke.py   # 需服务 + playwright
```

## 5. 当前 git 状态

- 分支:`codex/location-analysis-next`(= `origin/...`),HEAD `8301c93 feat: improve workbench ppt text editing`(集齐选址分析 + PPT 预览 + PPT 标记)。
- `main` 在 `8e4dcac`(选址分析合并)。新功能开发建议**从 main 切干净的新分支**。
- **未提交的运行产物(正常,勿提交)**:`projects/26-BQ-PARK/05_output/inventory.json`(M)、`05_output/drawings/semantic/`、`05_output/ppt/`。建议有空把 `05_output` 运行产物加进 `.gitignore`。

## 6. 计划 / 评审文档索引(docs/)

- `CLAUDE_CODEX_REVIEW_THREAD.md` — 评审线程(只 mac claude 写,实施方勿动)。
- 制图统一与修复:`PLAN_2026-05-29_UNIFY_DRAWING_PRIMITIVES_TO_FZ.md`、`..._DRAWING_PRIMITIVE_FIXES.md`、`..._DRAWING_FIXES_ROUND6.md`、`..._ROUND7.md`。
- PPT:`PLAN_2026-05-30_PPT_OUTPUT_PREVIEW.md`(含 phase-2 第 11 节、预览修正第 12 节)、`PPT_DRAWING_TEXT_MARKUP.md`。
- 工作台布局/studio:`PLAN_2026-05-28_WORKBENCH_*`、`..._WHOLE_APP_STUDIO_*`。
- 历史交接:`HANDOFF_2026-05-2x_*`。

## 7. 协作模型与红线(重要)

- **角色**:实施 + 写详细计划 = Windows/mac codex;一审 = Windows codex;**最终审 = mac claude(我)**。当前主要用 **mac codex(cc-relay-hub 同组 `codex-bot`)** 实施,mac claude 出 brief + 终审。
- **多方向修改不并行**:同文件/强耦合任务**单线程顺序**做,每条一次提交;独立模块才考虑并行子 agent。
- **门禁驱动行为,不验产物**:对实施方,验收要驱动真实行为/逐像素回归,不能只断言"DOM 元素存在"(历史教训:多轮都栽在"只验存在")。
- **功能分区(FZ)是回归红线**:任何重构后 FZ 行为逐像素不变。
- **不提交 `05_output` 运行产物;不擅自加重依赖(如 python-pptx 先说明)**;实施方不改 `CLAUDE_CODEX_REVIEW_THREAD.md`。

## 8. 给新上下文的下一步

用户准备**重构另一个功能**(待定)。建议新会话:① 先读本文件 + `README.md`/`AGENTS.md` + 相关 PLAN;② 从 `main` 切干净分支;③ 明确目标后由 mac claude 出 brief、mac codex(`codex-bot`)实施、mac claude 终审,沿用 §7 红线。
