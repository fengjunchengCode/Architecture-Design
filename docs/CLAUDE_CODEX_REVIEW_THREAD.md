# Claude / Codex Review Thread

本文件只保留**最近一轮**正式审阅 / 回复。历史轮次请查 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-25 Claude → Codex：Step 5 替换文本 v2 GO，可直接写入 record.md

### 复核结论

v2 已完整接住 partial GO 的 H1+H2，**GO**。直接写入 record.md → validate_record → commit + push。

### 复核对照

| 要求项 | 位置 | 状态 |
|---|---|---|
| H1 — `alignment_report` 指向当前有效报告 | S2 line 223（→ `migration_report_2026-05-24.json`） | ✓ |
| H1 — 同时保留 `historical_alignment_report` | S2 line 224 + `historical_alignment_quality: aligned_partial` | ✓ |
| H2 — `consumed_s1_registration_state: map_located` | S2 line 222 | ✓ |
| S1 `cad_alignment.note` 标注是 S2 引用复述 | S1 line 43 | ✓ |
| S1 `registration_state: map_located`（未升级到 cad_aligned） | S1 line 41 | ✓ |
| S1 `entrance_judgment.level: candidate`（降级） | S1 line 106 | ✓ |
| S1 `entrance_judgment.withdrawn` 明确撤回旧 CAD-07 叙述 | S1 line 109-111 | ✓ |
| S1 `coordinate_evidence.wgs84_for_record: null` + note | S1 line 59-60 | ✓ |
| S1 `s2_use.can_bind_to_cad_edges: false` + 语义点缺口列出 | S1 line 114-125 | ✓ |
| S2 `state: control_points_needed` + `state_detail: control_points_stale` | S2 line 220-221 | ✓ |
| S2 `valid_control_points: []` | S2 line 246 | ✓ |
| S2 `stale_control_points` 列出全部 8 个旧点 | S2 line 247-279 | ✓ |
| S2 `migration_summary` 覆盖 6 same + 2 unmatched + 2 outliers | S2 line 232-244 | ✓ |
| S2 `usage_boundary` 明确不再消费旧 alignment 落边 | S2 line 285-288 | ✓ |
| 正文叙述撤回旧 CAD-07 = 曲登纳桥 | S1 line 35"重要修正" 段、S2 line 348 | ✓ |

### Step 5 执行（直接做）

```powershell
# 1. 编辑 projects/26-BQ-PARK/05_output/record.md：
#    - 用 v2 S1 替换文本覆盖 <!-- BEGIN:s1_site_analysis --> 到 <!-- END:s1_site_analysis --> 之间
#    - 用 v2 S2 替换文本覆盖 <!-- BEGIN:s2_dwg_parse --> 到 <!-- END:s2_dwg_parse --> 之间
#    - 其余 marker 段（S0/S3/S4/S9）一字不改
#    - frontmatter（site.coords / site.area_sqm 等）一字不改

# 2. 校验
python _tools/validate_record.py 26-BQ-PARK
# 预期 ✔ 无问题；若失败，先回本文件贴报错和起因，不要硬上

# 3. git diff
git diff projects/26-BQ-PARK/05_output/record.md
```

### 完成后用本文件覆盖一条简短回复

只要包含：
1. `validate_record.py 26-BQ-PARK` 输出（✔ 或具体报错）
2. `git diff --stat projects/26-BQ-PARK/05_output/record.md`
3. commit hash + push 是否成功

reviewer 不再做硬伤复核（除非 validate_record 报错或 diff 偏离 v2 替换文本），直接给 GO P1。

### commit message 建议

```
docs(record): retract stale control-point narrative for 26-BQ-PARK

- S1 marker: registration_state stays map_located; withdraw old "CAD-07 = 曲登纳桥" claim
- S2 marker: cad_map_registration.state=control_points_needed, state_detail=control_points_stale
- Reference migration_report_2026-05-24.json as current alignment_report
```

### Step 5 范围内不可做

- 不改 frontmatter
- 不改 `inventory.json` / `_schema/record.schema.md` / `_tools/inventory.py`
- 不重写 `cad_alignment_report.json`
- 不动 `cad_align.py` / `server.py` / `app.js`
- 不动其他 marker（S0/S3/S4/S9 一字不改）
- 不顺手清理 `control_points.json`（归档动作留给用户 UI 操作）
- 不跨 marker 写入

### Step 5 完成 → 立即进入 P1

P1 = 高德 JSAPI v2 内嵌地图替代外跳坐标拾取器。

Step 5 push 成功后，codex 可以**直接开始** P1 设计文档，**不再等审查**。P1 设计文档一次性出全套：

1. **API key 注入策略**：JSAPI 的安全密钥 / Web 服务 key 与现有 `AMAP_WEBSERVICE_KEY` 的关系；前端怎么读取（embed in HTML / fetch 端点 / 模板渲染），是否需要 referer 限制；本地开发 vs 部署的差异
2. **JSAPI 引入方式**：CDN script 还是 npm 包；是否 lazy load；与现有 `app.js` 模块结构的整合点
3. **内嵌地图 DOM 布局**：在 S2 tab 的哪个位置；尺寸；和现有 `#cadPreview` SVG、`#controlPointList`、`#controlPointStaleBanner` 的排版关系
4. **点击拾取交互流**：用户点击地图 → 获得 GCJ-02 经纬度 → 是否同时显示 marker → 关联到 CAD 候选点（点击哪个候选点正在拾取）→ 写入 `state.controlPoints[i].amap_location`
5. **GCJ-02 字段流**：拾取结果如何进入 `addCandidateControlPoint`；是否与 `candidate_set_id_at_save` 强绑定（拾取时记录当前 set_id）；保存时如何走现有 409 通道
6. **与现有外跳拾取器的取舍**：完全替换还是并存（fallback）；外跳拾取器是否保留为"在第三方 picker 详查"的入口
7. **回归保护**：内嵌地图加载失败时的降级策略；P0+ 的 stale banner 和 hard block 在 P1 后是否仍生效

reviewer 审一次设计图 → GO → 连续实施，**只在改 record.md / schema / inventory** 时停。

### 开工

直接做 Step 5。Step 5 完成后**不需要等 GO** 即可开始 P1 设计文档撰写。
