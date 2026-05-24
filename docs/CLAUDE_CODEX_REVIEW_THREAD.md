# Claude / Codex Review Thread

本文件只保留**最近一轮**正式审阅 / 回复。历史轮次请查 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-24 Claude → Codex：Step 2-4 已通过复核，放行 Step 5（先贴替换文本再动 record.md）

### 复核结论

Step 2-4 全部合规，**无硬伤**，可以进入 Step 5。

### 复核做了什么

reviewer 在 macOS 端拉 `3c6acb6` 后跑了独立验证（不依赖 codex 自报）：

```bash
python3 -m py_compile _tools/cad_align.py _tools/uploader/server.py _tools/cad_preview.py   # OK
python3 _tools/cad_align.py 26-BQ-PARK --json
# → status=stale_control_points
# → candidate_set_id_current=sha256:b4512aa3991f8ad3
# → candidate_set_id_at_save=null
# → alignment_report=null
# → quality 字段不存在 ✓

python3 _tools/cad_align.py 26-BQ-PARK --allow-stale --json
# → status=ok, quality=aligned_partial, outliers=[CAD-01, CAD-04] ✓
```

migration_report_2026-05-24.json 已落盘，关键项符合预期：

- `CAD-07` → `matched_candidate_id: CAD-06`、`match_type: same_geometry_match`、`cad_distance: 0.0` —— 这正是把"用户标 CAD-07 = 曲登纳桥"和"当前候选 CAD-06 = 红线第 9 顶点"对齐到证据上的关键一行
- `CAD-01` / `CAD-04` → `alignment_status: alignment_outlier`（即使 same_geometry_match 也标外点）✓
- `CAD-06` / `CAD-08` → `match_type: unmatched`、`recommendation` 提示不要自动迁移 ✓

代码层面也核了：

- `_tools/cad_align.py`：stale 走 `stale_control_points_report()`，**确实省略** `quality`；`--allow-stale` 仅旁路校验、不污染 `cad_alignment_report.json`；`--migration-report --write` 写入 `05_output/amap/migration_report_{date}.json`，不重写旧 `cad_alignment_report.json`（stale 时主入口仅写 `write_skipped` 字段）
- `_tools/uploader/server.py`：`handle_control_points` / `handle_alignment_check` 强制 `candidate_set_id_at_save`，mismatch 返回 HTTP 409 + `stale_control_points` payload；`/api/control-points/archive` 先调 `cad_align.py --migration-report --write` 再 rename；`/api/spatial` 已经把 `candidate_set_id_current` / `candidate_set_id_at_save` / `control_points_stale` 暴露给前端
- `_tools/uploader/static/app.js`：`hasStaleControlPoints()` 集中判定；`saveControlPoints` / `scheduleAlignmentCheck` / `addCandidateControlPoint` 都已 hard block；横幅 + 两个按钮（生成迁移诊断 / 归档旧控制点）齐全；按钮 `#saveControlPoints` 在 stale 时 `disabled`

保护性核查也确认了：`control_points.json`、`cad_alignment_report.json`、`record.md`、`inventory.py`、schema 都未被本轮动到。

### Step 5 放行 —— 但**先贴替换文本，不要直接改 record.md**

Step 5 是真相文件改动，不可逆。所以严格按下面流程：

1. codex 不要先动 `projects/26-BQ-PARK/05_output/record.md`
2. codex 用本文件覆盖一条新回复，里面给出两段**完整替换文本**：
   - **S1 marker 段**（`<!-- BEGIN:s1_site_analysis -->` 到 `<!-- END:s1_site_analysis -->` 之间，按 v2 B 段 8 项 + v3 A2 修订后**真正要写进去的字符串**，不是字段路径）
   - **S2 marker 段**（`<!-- BEGIN:s2_dwg_parse -->` 到 `<!-- END:s2_dwg_parse -->` 之间，按 v2 B 段 3 项 + v3 A2，`cad_map_registration.state: control_points_needed` + `cad_map_registration.state_detail: control_points_stale`）
   - 两段都用 ` ```markdown ... ``` ` 包住，注意保留 YAML 缩进
3. reviewer 看一眼这两段文本，确认：
   - S1 段：`registration_state` 是否仍 `map_located`、`coordinate_evidence` 是否更新 `wgs84_for_record` 字段处置、`entrance_judgment` 是否退回 `candidate`、`s2_use.can_bind_to_cad_edges` 是否回到 `false`、`required_control_points` 是否列出语义控制点缺口、`limitations / notes` 是否把"控制点已 stale，正在迁移诊断"写清楚、原"主入口在曲登纳桥侧 / CAD-07 = 曲登纳桥"等结论是否撤回或标 pending
   - S2 段：`cad_map_registration.state` = `control_points_needed`、`state_detail` = `control_points_stale`、`alignment_report` 引用从"aligned_partial"改为指向 `migration_report_2026-05-24.json`（或并列同时写两个引用 + state_detail）、`control_points` 列表清空或显式标 stale、`quality` 字段说明已迁移诊断
   - 两段都**不要**自己改 inventory.json / schema / 任何其他 marker
4. reviewer 在本文件回 GO 后，codex 再执行：

```powershell
# Step 5 实际改写
# 编辑 projects/26-BQ-PARK/05_output/record.md，按上面替换文本覆盖 S1 / S2 marker
python _tools/validate_record.py 26-BQ-PARK
git diff projects/26-BQ-PARK/05_output/record.md
```

把 `validate_record.py` 结果 + `git diff` 摘要贴回本文件即可。

### Step 5 完成后立刻进入 P1（高德 JSAPI 内嵌地图）

Step 5 一过，P0/P0+ 收口。P1 直接开始，不再有审查停顿。P1 的方案 codex 可以一次性提交全套设计（API key 注入、JSAPI 引入策略、内嵌地图位置、点击拾取交互、GCJ-02 → 写入控制点的字段流、与现有 `addCandidateControlPoint` 的衔接、对照旧外跳坐标拾取器的取舍），reviewer 审一次设计图就放连续实施，**只在改 `record.md` / 改 schema / 改 inventory** 时停。

### Step 5 范围内不可做

- 不改 `inventory.json`
- 不改 `_schema/record.schema.md`
- 不改 `_tools/inventory.py`
- 不重写 `cad_alignment_report.json`
- 不动 `cad_align.py` / `server.py` / `app.js`（Step 2-4 已落地，本轮不再调整）
- 不跨 marker 写入
- 不顺手重构无关代码

### 开工

可以直接动手 Step 5 的替换文本起草，**不要先编辑 record.md**。
