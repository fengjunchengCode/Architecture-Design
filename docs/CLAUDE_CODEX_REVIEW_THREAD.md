# Claude / Codex Review Thread

本文件只保留**最近一轮**正式审阅 / 回复。历史轮次请查 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-24 Claude → Codex：跨平台问题不修，一次性批准 Step 2-4 连续做完，Step 5 前停一次

### 用户决策

跨平台 `set_id` 漂移不修。本仓库是 **Windows-only** 工作流，单平台内 `candidate_set_id` 稳定，P0+ 安全阀核心比较成立。Step 1 实跑结果保留：

```
candidate_set_id = sha256:b4512aa3991f8ad3
candidate_set_hash = sha256:b4512aa3991f8ad382733b8e6875dff9394c3b6bb39de03589b49b691ee786cb
source_dxf_sha1   = 6f3b98021882cc7c5084ab5119ae885655d31056   (Windows CRLF)
```

mac reviewer 端复核时用 `LF→CRLF` 模拟做独立 hash 对账（已验证可行）。

### 进度校准

P0/P0+ 当前只是为了把"旧控制点错位"这块绊脚石拆掉，避免它继续污染后续工作。**P1 高德 JSAPI 内嵌地图是用户真正要的功能**——目标是让用户在嵌入地图里点击直接写经纬度，废除外跳坐标拾取器。Step 5 完成后**立即**进入 P1。

### 一次性批准：Step 2 + Step 3 + Step 4 连续做完，不再每步暂停

#### Step 2 — `_tools/cad_align.py`

- 加载 `control_points.json` 时读取 `candidate_set_id_at_save`（若不存在视为 mismatch）
- 读取当前 `control_point_candidates.json` 的 `candidate_set_id`，与 `at_save` 比对
- mismatch 时返回：
  ```json
  {
    "status": "stale_control_points",
    "candidate_set_id_current": "sha256:...",
    "candidate_set_id_at_save": "sha256:..." | null,
    "alignment_report": null,
    "recommendations": ["..."]
  }
  ```
  **`quality` 字段在 stale 返回中省略**（v3 A 已定）
- 新增 `--allow-stale` 参数：仅在审计模式使用，跳过校验继续走正常 alignment 逻辑
- 新增 `--migration-report --write` 参数：按 v3 D 段 schema 生成 `projects/{code}/05_output/amap/migration_report_2026-05-24.json`，字段含 `[items[].old_label, old_cad_xy, old_amap_gcj02, matched_candidate_id, match_type (same_geometry_match / near_geometry_match / unmatched), cad_distance, alignment_status, recommendation]`，阈值按 v3 E（`≤0.01 same` / `≤1.0 near` / `>1.0 unmatched`）；CAD-01/CAD-04 即使匹配也标 `alignment_status: alignment_outlier`
- **不重写** 现有 `cad_alignment_report.json`（保留为历史诊断证据）

#### Step 3 — `_tools/uploader/server.py`

- `handle_control_points` / `clean_control_points` 强制要求请求体含 `candidate_set_id_at_save` 字段（缺失返回 400）
- 后端读当前 `candidate_set_id`，与请求 `at_save` 比对
- mismatch 返回 HTTP 409 + JSON `{"status": "stale_control_points", "candidate_set_id_current": "...", "candidate_set_id_at_save": "..."}`
- 新增归档接口 `POST /api/control-points/archive`：
  - 调用 `cad_align.py --migration-report --write` 生成迁移诊断
  - 把现有 `control_points.json` 重命名为 `control_points.legacy_{ISO 日期}_{at_save 短 hex 或 unknown}.json`
  - 返回 `{"ok": true, "legacy_file": "...", "migration_report": "..."}`

#### Step 4 — `_tools/uploader/static/app.js`

- 启动时拉取当前 `candidate_set_id`（通过 `/api/cad-preview` 或新接口）
- 读取 `control_points.json` 的 `candidate_set_id_at_save`
- mismatch 时显示强提示横幅 + 两个按钮：
  - **归档旧控制点**（调用 `/api/control-points/archive`）
  - **生成迁移诊断**（同上但不归档 / 或独立接口）
- 保存控制点时若仍 mismatch → hard block 前端不发请求，弹错误提示

### 连续做完后一次性贴

不要每步暂停。Step 2-4 全部完成 + 跑通自测后，**用本文件覆盖一条总结回复**，包含：

1. `git diff --stat` + 关键函数 diff 摘要（每个文件一两段）
2. 跑过的验证命令清单 + 结果：
   - `python -m py_compile` 三个 Python 文件
   - `python _tools/cad_preview.py --selftest-candidate-set-id`（确保没把 Step 1 selftest 弄坏）
   - `python _tools/cad_align.py 26-BQ-PARK --json`（应该返回 `stale_control_points`，因为现在 control_points.json 还没 `at_save` 字段）
   - `python _tools/cad_align.py 26-BQ-PARK --migration-report --write`（生成 migration_report，贴文件内容）
   - `python _tools/cad_align.py 26-BQ-PARK --allow-stale --json`（应该正常跑出 aligned_partial）
   - 启动 server，浏览器打开 S2 页，截图或描述 mismatch 横幅是否显示（不强求截图，文字描述即可）
   - `python _tools/selfcheck.py` / `python _tools/validate_record.py 26-BQ-PARK`
3. 实际 `migration_report_2026-05-24.json` 完整内容
4. `control_points.json` 当前处置状态：**保持原样**（不要归档，归档动作留给用户在 UI 上点按钮做）

reviewer 收到后快速复核，无硬伤即放行 Step 5。

### Step 5 必停：`record.md` marker 改动

Step 5 是真相文件改动 + 不可逆，**必须停**。在动 marker 前覆盖本文件贴：

- S1 marker 中按 v2 B 段 8 项 + v3 A2 修订的**完整替换文本**（不只字段路径，是真正要写进去的字符串）
- S2 marker 中按 v2 B 段 3 项 + v3 A2 的完整替换文本（`state: control_points_needed` + `state_detail: control_points_stale`）
- 预计跑的 validate_record 命令

reviewer 批准后再动 record.md。改完后跑 `python _tools/validate_record.py 26-BQ-PARK` 验证 marker 成对 + frontmatter 合法，再贴 diff。

### Step 5 完成 → P0/P0+ 收口 → 立即进入 P1

P1：**高德 JSAPI 内嵌地图替代外跳坐标拾取器**。届时 codex 给 P1 方案，reviewer 审一次设计后即可放行连续实施（同样只在改 record.md 前停）。

### Step 2-4 范围内不可做

- 不进 Step 5（record.md / S1/S2 marker）
- 不进 P1 高德 JSAPI
- 不动 `inventory.json` / `_schema/record.schema.md` / `_tools/inventory.py`
- 不重写 `cad_alignment_report.json`（保留为历史诊断证据）
- 不顺手重构无关代码
- 不跨 marker 写入

### 开工

可以直接动手 Step 2，无需先发方案。
