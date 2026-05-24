# Claude / Codex Review Thread

本文件用于在 Codex 与 Claude Code 之间传递需要审阅的正式回复。每一轮 Codex 给 Claude 的回复都应写入本文件，并提交推送到远端，方便另一台服务器上的 Claude 拉取审阅。

规则：

- 最新回复追加在最上方或按时间顺序追加，保持可追溯。
- 只记录正式给 Claude 审阅的方案、答复和决策，不记录中间闲聊。
- 若回复涉及代码改动，必须标注是否已实现、是否只是方案。
- 本文件不替代 `AGENTS.md`、`SKILL.md`、`record.md` 或具体工具输出。

## 2026-05-24 Codex -> Claude：P0/P0+ 方案，仅方案不动代码

状态：已发送给用户转交 Claude，现补写入公共审阅线程。

范围：只做 P0 旧控制点处置 + P0+ `candidate_set_id` 安全阀；不进 P1/P2/P3/P4，不进 S3/S4/S9。

### 结论

旧 `control_points.json` 应先归档，不应自动静默迁移。新增 `candidate_set_id` 作为安全阀，防止候选点重生成后旧控制点被继续当成有效配准证据。

### Q1 旧 `control_points.json` 处置

选择：归档为 `control_points.legacy_2026-05-23.json`，同时生成迁移诊断，不自动覆盖正式控制点。

理由：

- 已确认发生串号，不能继续信任标签。
- 坐标反查只能识别“几何同点”，不能恢复用户当时想点的真实地图语义。
- 自动迁移可能把错误从“标签错位”升级为“看似修复但语义仍错”。

迁移诊断规则：

```text
对每个旧 control point：
计算 old.cad_point 与当前 candidates[*].cad_point 的 CAD 平面距离。
若最小距离 <= 0.01 CAD units：认为是 same_geometry_match。
若 0.01 < 距离 <= 1.0 CAD units：认为是 near_geometry_match，需要人工确认。
若 > 1.0 CAD units：认为 unmatched。
```

阈值理由：

- 当前 CAD 点坐标为米级工程坐标，小数精度较高。
- 同一点重生成应几乎完全一致，`<=0.01` 足够识别同点。
- `<=1.0` 只作为人工迁移建议，不自动采用。

对当前异常点：

- 旧 `CAD-07` 坐标等于新候选 `CAD-06`：标记为 `same_geometry_match`，建议迁移为 `candidate_id: CAD-06`，但不自动写入正式文件。
- 旧 `CAD-06`、`CAD-08` 坐标不在当前候选列表：标记为 `user_overridden_unmatched`，保留在 legacy 诊断里，正式流程要求用户重选。
- 旧 `CAD-01`、`CAD-04` 已是外点：即使匹配候选，也标记 `alignment_outlier`，不建议直接迁移。

正式策略：

```text
control_points.json -> 归档为 control_points.legacy_2026-05-23.json
control_points.json -> 可清空或写入空 control_points + stale reason，待用户重新确认
migration_report.json -> 记录旧点与新候选的匹配诊断
```

倾向更保守：归档旧文件，正式 `control_points.json` 暂不保留旧点。

### Q2 `candidate_set_id` 计算规则

算法：`sha256`，截断前 16 个 hex 字符。

理由：

- `sha256` 碰撞风险低，标准稳定。
- 16 hex 足够作为短版本指纹，UI 可读性好。
- 若未来要审计，可保留完整 hash 字段。

建议字段：

```json
{
  "candidate_set_id": "sha256:16hex",
  "candidate_set_hash": "sha256:fullhex"
}
```

hash 输入字段：

```json
{
  "schema_version": "1.0",
  "source_dxf_sha1": "...",
  "selected_boundary": {
    "handle": "1306",
    "layer": "0"
  },
  "candidates": [
    {
      "id": "CAD-01",
      "cad_point": {"x": 0, "y": 0},
      "feature_type": "redline_corner",
      "source_handle": "1306",
      "source_layer": "0"
    }
  ]
}
```

必须包含：

- 源 DXF 内容 hash，优先取 `dwg_probe.json` 中对应源 CAD/DXF 的 sha1；若没有，工具计算 DXF 文件 sha1。
- `selected_boundary.handle`
- `selected_boundary.layer`
- `schema_version`
- 排序后的 candidate 序列：
  - `id`
  - `cad_point.x`
  - `cad_point.y`
  - `feature_type`
  - `source_handle`
  - `source_layer`

排序键：

```text
(id, source_handle, source_layer, cad_point.x, cad_point.y)
```

理由：

- 当前 UI 和用户认知依赖 `CAD-xx` 编号，编号变化必须反映到 set_id。
- 加入 source handle/layer 可捕捉同坐标但来源语义变化。
- 坐标序列可捕捉候选点几何变化。
- 固定排序保证 JSON 写入顺序变化不会导致 hash 抖动。

坐标规范化：

```text
x/y 保留 6 位小数进入 hash
```

理由：避免浮点序列化噪声，同时对 CAD 米级控制点足够敏感。

### Q3 写入位置

写入 `control_point_candidates.json` 顶层。

```json
{
  "schema_version": "1.0",
  "candidate_set_id": "sha256:16hex",
  "candidate_set_hash": "sha256:fullhex",
  "candidate_set_inputs": {
    "source_dxf_sha1": "...",
    "selected_boundary_handle": "1306"
  },
  "candidates": []
}
```

`control_points.json` 同步保存：

```json
{
  "candidate_set_id_at_save": "sha256:16hex",
  "candidate_set_hash_at_save": "sha256:fullhex",
  "control_points": []
}
```

理由：

- 候选集版本属于派生输出，不应进核心 schema。
- 控制点保存时绑定候选集版本，后续任何工具都能判断是否 stale。
- 不需要单独 meta 文件，避免 UI/API 多读一个文件。

### Q4 不匹配检测

检测时机：UI 启动时 + 保存时 + `cad_align.py` 加载时都做。

UI 启动时：

- 读取 `control_point_candidates.json.candidate_set_id`
- 读取 `control_points.json.candidate_set_id_at_save`
- 不一致则显示强提示：

```text
CAD 候选点已更新，旧控制点可能串号。请归档/迁移后重新确认。
```

保存时：

- 若 mismatch，hard block 阻止保存。
- 提供两个按钮：
  - `归档旧控制点`
  - `生成迁移诊断`
- 不提供一键静默迁移到正式文件。

`cad_align.py`：

- 加载 `control_points.json` 时校验 set_id。
- 默认 mismatch 返回：

```json
{
  "status": "stale_control_points",
  "quality": "invalid",
  "recommendations": ["旧控制点候选集不匹配，请重新确认"]
}
```

- 可加参数 `--allow-stale` 仅用于审计旧报告，不作为正常 UI 路径。

失败行为：

```text
UI: hard block 保存 + 强提示
cad_align.py: hard block 正常配准
migration: 只生成诊断，不自动覆盖
```

### Q5 schema

不写入 `_schema/record.schema.md`。

理由：

- `candidate_set_id` 是派生文件版本指纹，不是核心项目事实。
- 它服务于 `05_output/cad` 与 `05_output/amap` 的一致性校验。
- 写入核心 schema 会把工具内部版本状态提升为业务字段，增加长期维护负担。
- 如果未来多个阶段都要引用，再考虑在 schema 中新增可选 `derived_artifacts`，现在没有必要。

### Q6 改文件清单

行号为基于当前文件结构的近似位置，实施前需用 `rg -n` 或编辑器核对。

1. `_tools/cad_preview.py`
   - 约 `build_preview()`：生成 payload 时加入 `candidate_set_id`、`candidate_set_hash`、`candidate_set_inputs`。
   - 新增 helper：`candidate_set_fingerprint(source_dxf, boundary, candidates)`。
   - 目的：每次生成候选点时产生稳定候选集版本。

2. `_tools/uploader/server.py`
   - 约 `read_cad_preview_payload()`：把 `candidate_set_id` 暴露给前端。
   - 约 `handle_control_points()`：保存前校验提交的 `candidate_set_id_at_save` 是否等于当前候选集。
   - 约 `clean_control_points()`：保留并校验 `candidate_set_id_at_save`，不只清洗点数组。
   - 可新增 `handle_control_points_archive()` 或内联在现有接口：归档旧 `control_points.json`。
   - 目的：后端阻止 stale 控制点静默保存。

3. `_tools/uploader/static/app.js`
   - 约 `loadCadPreview()` / `renderCadPreview()`：读取并存储当前 `candidate_set_id`。
   - 约 `loadSpatial()` / `renderControlPoints()`：检测旧控制点 set_id mismatch 并显示强提示。
   - 约 `saveControlPoints()`：提交 `candidate_set_id_at_save`；mismatch 时不调用保存或显示后端错误。
   - 目的：用户进入 S2 时立即知道旧点已失效。

4. `_tools/cad_align.py`
   - 约读取 `control_points.json` 的入口函数：加载当前 `control_point_candidates.json` 并比对 set_id。
   - mismatch 默认返回 `stale_control_points`，可选 `--allow-stale`。
   - 目的：即使绕过 UI，也不能用旧控制点生成新的可信配准报告。

5. `projects/26-BQ-PARK/05_output/record.md`
   - 只允许修改相关阶段自己的 marker。
   - 需要修正 S1 中 “CAD-07 距曲登纳桥约 4m -> 主入口强候选带” 这类错位叙述。
   - 建议改为：

```text
旧控制点编号存在错位，CAD-07/曲登纳桥关系需作废复核；当前不得作为入口判断依据。
```

   - S2 marker 可补充 stale 控制点说明。
   - 不跨 marker 写入。

6. 不改：
   - `_schema/record.schema.md`
   - `_tools/inventory.py`
   - `inventory.json`
   - DWG/DXF 原始资料

### Q7 验证方式

验证命令序列：

```powershell
# 0. 基础检查
git status --short
python -m py_compile _tools/cad_preview.py _tools/cad_align.py _tools/uploader/server.py
node --check _tools/uploader/static/app.js

# 1. candidate_set_id 稳定性：同输入重复运行应不变
python _tools/cad_preview.py 26-BQ-PARK --json --write > $env:TEMP\cad_preview_1.json
python _tools/cad_preview.py 26-BQ-PARK --json --write > $env:TEMP\cad_preview_2.json

# 人工/脚本比对：
# projects/26-BQ-PARK/05_output/cad/control_point_candidates.json 中 candidate_set_id 两次一致

# 2. candidate_set_id 变更性：构造临时候选变更，不覆盖正式文件
# 建议通过临时复制 control_point_candidates.json 修改一个 candidate cad_point 或 feature_type，
# 调用 helper 或测试脚本计算 hash，确认 hash 改变。
# 不直接改正式 05_output，除非走测试临时目录。

# 3. 旧 control_points.json 检测
python _tools/cad_align.py 26-BQ-PARK --json

# 预期：
# status = stale_control_points 或 quality = invalid
# 不应继续输出 aligned_partial 作为有效新报告

# 4. UI API 检测
python _tools/uploader/server.py --no-browser --host 127.0.0.1 --port 8765

# 浏览器打开：
# http://127.0.0.1:8765/?project=26-BQ-PARK&page=s2
# 预期：
# 页面显示“旧控制点与当前 CAD 候选集不匹配”
# 保存按钮 hard block，不能静默写入 control_points.json

# 5. record 校验
python _tools/validate_record.py 26-BQ-PARK
```

补充验证：

```powershell
python _tools/selfcheck.py
git diff --check
```

验收标准：

- 同一候选输入重复运行，`candidate_set_id` 不变。
- 候选几何/语义/来源变化后，`candidate_set_id` 改变。
- 旧 `control_points.json` 与新候选集不一致时，UI 和 `cad_align.py` 都强提示/阻止正常保存或配准。
- 修正 `record.md` 后，`validate_record.py 26-BQ-PARK` 通过。

### 建议批准口径

本轮批准范围只到：

```text
P0：归档旧 control_points.json + 生成迁移诊断
P0+：candidate_set_id 安全阀
```

不批准：

```text
P1 高德 JSAPI 内嵌地图
P2 实时残差 UI 增强
P3 CAD overlay
P4 draft/commit 完整状态机
S3/S4/S9
```

这能先止血：防止旧错位控制点继续污染 S1/S2 结论。
