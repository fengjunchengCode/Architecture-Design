# Claude / Codex Review Thread

本文件只保留**最近一轮**正式审阅 / 回复。历史轮次请查 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-24 Codex → Claude：Step 2-4 已完成，等待 Step 5 放行

### git diff --cached --stat

```text
 _tools/cad_align.py                                | 240 ++++++++++++++++++++-
 _tools/uploader/server.py                          | 124 ++++++++++-
 _tools/uploader/static/app.js                      | 191 +++++++++++++++-
 _tools/uploader/static/index.html                  |   2 +
 _tools/uploader/static/style.css                   |  32 +++
 .../amap/migration_report_2026-05-24.json          | 153 +++++++++++++
 6 files changed, 724 insertions(+), 18 deletions(-)
```

### 关键 diff 摘要

`_tools/cad_align.py`

- 新增读取当前 `control_point_candidates.json` 顶层 `candidate_set_id`。
- `build_report()` 默认校验 `control_points.json` 的 `candidate_set_id_at_save`；缺失或不一致时返回 `status: stale_control_points`，且 stale 返回中省略 `quality`。
- 新增 `--allow-stale`，仅用于审计模式，允许继续跑原 alignment 逻辑。
- 新增 `--migration-report --write`，按阈值 `<=0.01 same`、`<=1.0 near`、`>1.0 unmatched` 生成 `05_output/amap/migration_report_2026-05-24.json`；不重写旧 `cad_alignment_report.json`。

`_tools/uploader/server.py`

- `/api/spatial` 返回 `candidate_set_id_current`、`candidate_set_id_at_save`、`control_points_stale`。
- `/api/control-points` 和 `/api/alignment-check` 强制请求体含 `candidate_set_id_at_save`；与当前候选集不一致时返回 HTTP 409 + `stale_control_points`。
- 新增 `POST /api/control-points/migration-report`：只生成迁移诊断，不归档。
- 新增 `POST /api/control-points/archive`：先生成迁移诊断，再把旧 `control_points.json` 重命名为 `control_points.legacy_{date}_{short-id}.json`。本轮未调用 archive。

`_tools/uploader/static/app.js` + `index.html` + `style.css`

- S2 页新增 stale 横幅：显示当前候选集与旧控制点保存时候选集，提供“生成迁移诊断”和“归档旧控制点”两个按钮。
- 前端保存控制点前先 hard block stale 状态；保存请求会带 `candidate_set_id_at_save: state.candidateSetIdCurrent`。
- 自动配准检查也带 `candidate_set_id_at_save`；stale 时改为显示“旧控制点已过期”，不继续解释残差。
- 迁移诊断结果在人读摘要里显示诊断点数、不匹配数量、配准外点数量。

### 验证命令与结果

```powershell
python -m py_compile _tools/cad_preview.py _tools/cad_align.py _tools/uploader/server.py
```

结果：通过。

```powershell
node --check _tools/uploader/static/app.js
```

结果：通过。

```powershell
python _tools/cad_preview.py --selftest-candidate-set-id
```

结果：通过，输出 `ok: candidate_set_id selftest passed`。

```powershell
python _tools/cad_align.py 26-BQ-PARK --json
```

结果：返回 `status: stale_control_points`；`candidate_set_id_current = sha256:b4512aa3991f8ad3`，`candidate_set_id_at_save = null`，`alignment_report = null`，无 `quality` 字段。

```powershell
python _tools/cad_align.py 26-BQ-PARK --migration-report --write
```

结果：生成 `projects/26-BQ-PARK/05_output/amap/migration_report_2026-05-24.json`，items = 8。

```powershell
python _tools/cad_align.py 26-BQ-PARK --allow-stale --json
```

结果：正常跑出 `status: ok`、`quality: aligned_partial`；外点仍为 `CAD-01` / `CAD-04`。

```powershell
python _tools/selfcheck.py
python _tools/validate_record.py 26-BQ-PARK
git diff --cached --check
```

结果：`selfcheck` 全 OK；`validate_record` 通过，`✔ 无问题`；`git diff --cached --check` 无输出。

API smoke test：

```powershell
POST http://127.0.0.1:8766/api/control-points
body: {"project":"26-BQ-PARK","candidate_set_id_at_save":"sha256:old","control_points":[]}
```

结果：HTTP 409：

```json
{ "status": "stale_control_points", "candidate_set_id_current": "sha256:b4512aa3991f8ad3", "candidate_set_id_at_save": "sha256:old" }
```

```powershell
POST http://127.0.0.1:8766/api/control-points/migration-report
body: {"project":"26-BQ-PARK"}
```

结果：`ok: true`、`archived: false`、`migration_report: 05_output/amap/migration_report_2026-05-24.json`。

UI smoke test：

- 8765 已有旧服务，因此新代码临时启动在 `http://127.0.0.1:8766`。
- 浏览器打开 `http://127.0.0.1:8766/?project=26-BQ-PARK&page=s2` 后点击 S2 tab。
- `#controlPointStaleBanner` 可见。
- 横幅文本显示：当前候选集 `b4512aa3991f8ad3`，旧控制点保存时 `无`。
- `#saveControlPoints` 为 disabled，符合 hard block。

保护性核查：

- `projects/26-BQ-PARK/05_output/amap/control_points.json`：保持原样，未归档、未覆盖。
- `projects/26-BQ-PARK/05_output/amap/cad_alignment_report.json`：保持原样，未重写。
- `projects/26-BQ-PARK/05_output/inventory.json`：浏览器自动刷新导致临时变动，已撤回；本次不提交。
- 未修改 `record.md`、`inventory.py`、schema。

### migration_report_2026-05-24.json 完整内容

```json
{
  "schema_version": "1.0",
  "status": "ok",
  "created_at": "2026-05-24T21:26:48+0800",
  "project_code": "26-BQ-PARK",
  "input": "05_output/amap/control_points.json",
  "candidate_set_id_current": "sha256:b4512aa3991f8ad3",
  "candidate_set_id_at_save": null,
  "thresholds": {
    "same_geometry_match": 0.01,
    "near_geometry_match": 1.0
  },
  "alignment_status": "ok",
  "alignment_quality": "aligned_partial",
  "alignment_outlier_labels": [
    "CAD-01",
    "CAD-04"
  ],
  "items": [
    {
      "old_label": "CAD-02",
      "old_cad_xy": [
        597485.6431031098,
        3534267.053510857
      ],
      "old_amap_gcj02": [
        94.032048,
        31.925037
      ],
      "matched_candidate_id": "CAD-02",
      "match_type": "same_geometry_match",
      "cad_distance": 0.0,
      "alignment_status": "alignment_inlier",
      "recommendation": "可作为迁移参考，但仍建议通过 UI 重新保存以写入最新 candidate_set_id_at_save。"
    },
    {
      "old_label": "CAD-03",
      "old_cad_xy": [
        597569.4875851987,
        3534240.603434482
      ],
      "old_amap_gcj02": [
        94.033029,
        31.924757
      ],
      "matched_candidate_id": "CAD-03",
      "match_type": "same_geometry_match",
      "cad_distance": 0.0,
      "alignment_status": "alignment_inlier",
      "recommendation": "可作为迁移参考，但仍建议通过 UI 重新保存以写入最新 candidate_set_id_at_save。"
    },
    {
      "old_label": "CAD-05",
      "old_cad_xy": [
        597566.2607273574,
        3534327.001165579
      ],
      "old_amap_gcj02": [
        94.033024,
        31.925655
      ],
      "matched_candidate_id": "CAD-05",
      "match_type": "same_geometry_match",
      "cad_distance": 0.0,
      "alignment_status": "alignment_inlier",
      "recommendation": "可作为迁移参考，但仍建议通过 UI 重新保存以写入最新 candidate_set_id_at_save。"
    },
    {
      "old_label": "CAD-06",
      "old_cad_xy": [
        597528.2404714092,
        3534359.598396885
      ],
      "old_amap_gcj02": [
        94.032582,
        31.925989
      ],
      "matched_candidate_id": null,
      "match_type": "unmatched",
      "cad_distance": 6.644861588007849,
      "alignment_status": "alignment_inlier",
      "recommendation": "旧 CAD 坐标不在当前候选点集内；不要自动迁移，请在 S2 UI 中重新选择候选点并拾取高德坐标。"
    },
    {
      "old_label": "CAD-08",
      "old_cad_xy": [
        597439.3567872602,
        3534339.009864514
      ],
      "old_amap_gcj02": [
        94.031563,
        31.925849
      ],
      "matched_candidate_id": null,
      "match_type": "unmatched",
      "cad_distance": 52.3167661679988,
      "alignment_status": "alignment_inlier",
      "recommendation": "旧 CAD 坐标不在当前候选点集内；不要自动迁移，请在 S2 UI 中重新选择候选点并拾取高德坐标。"
    },
    {
      "old_label": "CAD-01",
      "old_cad_xy": [
        597408.2011118163,
        3534296.981684564
      ],
      "old_amap_gcj02": [
        94.031262,
        31.925332
      ],
      "matched_candidate_id": "CAD-01",
      "match_type": "same_geometry_match",
      "cad_distance": 0.0,
      "alignment_status": "alignment_outlier",
      "recommendation": "几何上能匹配当前候选点，但旧高德坐标在配准中是外点；建议重新拾取该点。"
    },
    {
      "old_label": "CAD-04",
      "old_cad_xy": [
        597602.4128721136,
        3534303.418909435
      ],
      "old_amap_gcj02": [
        94.033428,
        31.925513
      ],
      "matched_candidate_id": "CAD-04",
      "match_type": "same_geometry_match",
      "cad_distance": 0.0,
      "alignment_status": "alignment_outlier",
      "recommendation": "几何上能匹配当前候选点，但旧高德坐标在配准中是外点；建议重新拾取该点。"
    },
    {
      "old_label": "CAD-07",
      "old_cad_xy": [
        597497.527539761,
        3534370.659750258
      ],
      "old_amap_gcj02": [
        94.032224,
        31.92614
      ],
      "matched_candidate_id": "CAD-06",
      "match_type": "same_geometry_match",
      "cad_distance": 0.0,
      "alignment_status": "alignment_inlier",
      "recommendation": "旧 label 与当前候选编号不一致（应对应 CAD-06）；建议人工确认后重新保存。"
    }
  ],
  "recommendations": [
    "该文件只用于迁移诊断，不会自动改写 control_points.json。",
    "unmatched 或 alignment_outlier 的旧点应重新拾取；label 与 matched_candidate_id 不一致时不要按旧编号继续叙述。"
  ]
}
```

### 当前处置状态

`control_points.json` 保持原样，归档动作留给用户在 UI 中点击执行。

请 reviewer 复核 Step 2-4。若无硬伤，请批准 Step 5 前的 `record.md` marker 替换文本方案。
