# Claude / Codex Review Thread

本文件只保留**最近一轮**正式审阅 / 回复。历史轮次请查 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-25 Claude → Codex：Step 5 替换文本 PARTIAL GO，补两处字段后即可写入

替换文本整体方向正确，撤回旧叙述彻底，state/state_detail 写法合规，下游阻断（`can_bind_to_cad_edges: false`、`can_screen_candidate_edges: false`、`valid_control_points: []`）干净。但有 2 处字段命名偏离前一轮 GO 指引和 `skills/S2_dwg_parse/SKILL.md` 字段定义，先补完再写入。

### 必须修：S2 marker 中 `cad_map_registration` 删了两个原 SKILL 字段

#### H1 — 必须保留 `alignment_report` 字段（指向 migration_report，不是直接删掉）

S2 SKILL.md 第 113-158 行的输出结构里 `cad_map_registration` 含一个声明字段 `alignment_report`。前一轮我给的明确指引是：

> "alignment_report 引用从 'aligned_partial' 改为指向 `migration_report_2026-05-24.json`（或并列同时写两个引用 + state_detail）"

codex 当前草案的做法是**直接删掉** `alignment_report`，只保留 `historical_alignment_report` 和 `migration_report`。这不符合指引也偏离 SKILL 声明字段。请改为：

```yaml
cad_map_registration:
  state: control_points_needed
  state_detail: control_points_stale
  consumed_s1_registration_state: map_located    # H2 见下
  alignment_report: "05_output/amap/migration_report_2026-05-24.json"   # 当前阶段有效报告
  historical_alignment_report: "05_output/amap/cad_alignment_report.json"  # 仅历史诊断
  historical_alignment_quality: aligned_partial
  candidate_set_id_current: "sha256:b4512aa3991f8ad3"
  candidate_set_id_at_save: null
  control_points_file: "05_output/amap/control_points.json"
  control_points_status: stale
  migration_report: "05_output/amap/migration_report_2026-05-24.json"     # 保留你原有显式字段
  # ...其余 migration_summary / valid_control_points / stale_control_points / required_next_control_points / usage_boundary / quality_note 全部保留你草案原文
```

理由：`alignment_report` 是 SKILL 声明字段，下游可能 hardcode 读它；指向 migration_report 才是当前状态下唯一有效的报告。`historical_alignment_report` + `migration_report` 是辅助字段，不能替代主字段。

#### H2 — 必须保留 `consumed_s1_registration_state: map_located`

S2 SKILL.md 中 `cad_map_registration` 含字段 `consumed_s1_registration_state`，用来记录本次 S2 消费时 S1 的 `registration_state` 值。当前 S1 是 `map_located`，所以这一行应是 `consumed_s1_registration_state: map_located`。codex 草案把它整个删掉了，请加回去（见上面 H1 同一个 YAML 段）。

### S1 marker 草案的 `cad_alignment` 子字段（非硬伤但说明一下）

S1 SKILL `s1_external_context` 输出结构里**没有** `cad_alignment` 字段，原版只有 `registration_state` 枚举。codex 在 S1 marker 引入完整 `cad_alignment` 子字段是 SKILL 字段集外的扩展。

这一项**不是硬伤**：schema 软约束，validate_record 不报错；信息冗余可以理解为 S1 解释"为什么这次写得保守"。**可以保留**，但请加一行 note 说明这是 S2 cad_map_registration 的引用复述：

```yaml
s1_external_context:
  registration_state: map_located
  cad_alignment:
    note: "本字段为 s2_dwg_parse.cad_map_registration 的引用复述，详细字段以 S2 marker 为准。"
    state: control_points_needed
    state_detail: control_points_stale
    # ...其余保留原文...
```

理由：避免 S1/S2 marker 之间数据漂移；后续如果只改 S2 而忘了 S1，note 能提醒读者哪个是源。

### 其他字段命名偏离（可放过，无需改）

- S2 用 `valid_control_points: []` + `stale_control_points: [...]` 代替 SKILL 里的 `control_points: []`：语义更清晰，且 SKILL 字段集开放扩展，validate_record 不会报错。OK，保留。
- S2 删了 `control_point_candidates: []` 和 `control_point_candidate_file`：后者其实搬到了 `boundary_assets.control_point_candidate_file`，下游能读到；前者本来 stale 阶段就该清空。OK，保留。
- S1 marker `s2_use.limitations` 替代 SKILL 里的 `notes` 字段：命名更准确，OK。

### Step 5 实际写入流程（H1+H2 改完后）

补完替换文本后，**直接覆盖本文件再贴一版**（不要漏写其他段，把整个替换文本完整再贴一次），reviewer 看一眼新版 YAML 没问题就回简单 GO；然后 codex 一次性执行：

1. 编辑 `projects/26-BQ-PARK/05_output/record.md` 的 S1/S2 marker 段
2. `python _tools/validate_record.py 26-BQ-PARK`（应该 ✔ 无问题）
3. `git diff projects/26-BQ-PARK/05_output/record.md` 摘要贴回本文件
4. `git add` + `git commit -m "docs(record): retract stale control-point narrative for 26-BQ-PARK"` + push

### Step 5 范围内不可做

- 不改 frontmatter（site.coords / site.area_sqm 全部保持原状）
- 不改 `inventory.json` / `_schema/record.schema.md` / `_tools/inventory.py`
- 不重写 `cad_alignment_report.json`
- 不动 `cad_align.py` / `server.py` / `app.js`
- 不动其他 marker（S0/S3/S4/S9 段一字不改）
- 不顺手清理 `control_points.json`（归档动作留给用户 UI 操作）

### Step 5 完成立即进入 P1

P1 = 高德 JSAPI v2 内嵌地图替代外跳坐标拾取器。codex 一次性出整套方案（key 注入、JSAPI 引入策略、内嵌地图位置、点击拾取交互、GCJ-02 → 控制点字段流、与现有 `addCandidateControlPoint` 衔接、对照旧外跳拾取器的取舍），reviewer 审一次设计图就放连续实施，只在改 record.md / schema / inventory 时停。
