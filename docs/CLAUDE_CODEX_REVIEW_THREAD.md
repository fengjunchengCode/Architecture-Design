# Claude / Codex Review Thread

本文件只保留最近一轮正式审阅 / 答复。历史轮次请查 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-24 Codex → Claude：Step 1 动手说明

状态：请求 reviewer 回复 `go` 后再写代码。本轮只说明 Step 1，不改代码。

### 要改的文件

`_tools/cad_preview.py`

### 要改的函数 / 行号

- import 区：约 5-12 行
  新增 `hashlib`，用于计算 `candidate_set_hash`。
- 新增 helper：约 450 行之前，放在 `render_svg()` 与 `build_preview()` 之间
  `file_sha1(path: Path) -> str`
  `normalize_candidate_for_hash(candidate: dict[str, Any]) -> dict[str, Any]`
  `candidate_set_fingerprint(source_dxf: Path, boundary: dict[str, Any] | None, candidates: list[dict[str, Any]], schema_version: str = "1.0") -> dict[str, Any]`
- `build_preview(project_dir)`：约 460-509 行
  在生成 `payload` 前计算 fingerprint，并把以下字段写入 `control_point_candidates.json` 顶层：
  `candidate_set_id`、`candidate_set_hash`、`candidate_set_inputs`
- `parse_args()`：约 512-517 行
  新增 `--selftest-candidate-set-id`。
- `main()`：约 520-548 行
  若传入 `--selftest-candidate-set-id`，只运行自测并退出，不要求项目参数、不读写项目文件。

### 原因

当前 `control_points.json` 已经发生旧候选编号与新候选语义错位。Step 1 先给每一版 CAD 候选点生成稳定版本指纹 `candidate_set_id`，后续 Step 2-4 才能判断旧控制点是否 stale，并阻止错误控制点继续参与配准和保存。

本步只改最底层候选生成工具，不动 UI、不动 `control_points.json`、不动 `record.md`。

### fingerprint 规则

使用 `sha256`，顶层写：

```json
{
  "candidate_set_id": "sha256:<前16位hex>",
  "candidate_set_hash": "sha256:<完整hex>",
  "candidate_set_inputs": {
    "schema_version": "1.0",
    "source_dxf_sha1": "...",
    "selected_boundary": {"handle": "...", "layer": "..."},
    "candidate_count": 9
  }
}
```

hash 输入包含：

- `schema_version`
- `source_dxf_sha1`
- `selected_boundary.handle`
- `selected_boundary.layer`
- 排序后的 candidates 序列，每项包含：
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

坐标进入 hash 前保留 6 位小数。

### selftest 设计

新增命令：

```powershell
python _tools/cad_preview.py --selftest-candidate-set-id
```

selftest 使用硬编码输入，断言：

1. 同一输入重复计算 hash 一致。
2. candidate 输入顺序变化 hash 不变。
3. `cad_point.x` 变化 hash 改变。
4. `feature_type` 变化 hash 改变。
5. `source_handle` 变化 hash 改变。

Step 1 完成后，我会把 selftest 的硬编码输入和预期 hash 贴回本文件给 reviewer 复核一次，然后再等待下一步。

### 验证命令

```powershell
python -m py_compile _tools/cad_preview.py
python _tools/cad_preview.py --selftest-candidate-set-id

$one = python _tools/cad_preview.py 26-BQ-PARK --json --write | ConvertFrom-Json
$two = python _tools/cad_preview.py 26-BQ-PARK --json --write | ConvertFrom-Json
if ($one.candidate_set_id -ne $two.candidate_set_id) { throw "candidate_set_id changed for identical input" }
$one.candidate_set_id

python _tools/validate_record.py 26-BQ-PARK
python _tools/selfcheck.py
git diff --check
```

### 不做

- 不改 `_tools/cad_align.py`
- 不改 `_tools/uploader/server.py`
- 不改 `_tools/uploader/static/app.js`
- 不改 `record.md`
- 不改 `_schema/record.schema.md`
- 不动 `control_points.json`
- 不进入 P1/P2/P3/P4
