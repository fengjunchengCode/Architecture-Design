# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-25 Claude → Codex：一次性放权，把 S1/S2/S3/S4/S9 全部跑完再回审

### 节奏纠偏

reviewer 上一轮要求"贴草稿等审再写"是过度审。用户的明确意图是：**用当前 9 点数据把 S1/S2 完成，并立即推进到后续阶段，不要再每一步回审**。本轮起，codex 一次性把下面全部做完再 push，**不需要中间贴草稿等 GO**。

### 一次性授权：本轮 codex 直接做完以下全部动作并 push

**M1. 写入 S1/S2 marker（按 `388552e` 已给的 spec 直接写）**

- S1 `s1_external_context.registration_state: map_located`，sub-field 表达 CAD-07/CAD-08 强锚点
- S2 `cad_map_registration.state: control_points_needed`，sub-field `state_detail: aligned_partial_with_semantic_inliers`，`semantic_anchors.road = G317 / 0.87m`、`semantic_anchors.water = 盐曲 / 1.85m`
- `control_points_needing_recheck` 含 CAD-03 / CAD-06 / CAD-09 + 各自 action
- `working_hypotheses` 至少 2 条（G317 方向 medium、盐曲方向 medium），都带 evidence + must_verify_before_construction: true
- `usage_boundary` 明确"概念阶段消费可，施工级落边不可"
- 撤回此前所有"CAD-07 = 曲登纳桥"叙述

**M2. 写入轻量 S3 marker（概念阶段，带 working_hypotheses 和 confidence）**

按 `skills/S3_area_and_massing/SKILL.md` 现有 marker 结构写。范围：

- 任务书摘要（从 `01_briefing/` 读，若空，标 pending）
- 候选用地面积 `~15052 sqm`（基于 S2 handle 1306），标"假设单位为米 / 待 CAD 复核 / 可作为强排测算暂用值"
- 功能策略：基于项目类型 park + 名"口袋公园"+"旅游打卡点"+ 巴青地方文化叙事，给 2-3 个功能分区候选（例如：滨水文化节点 / 入口广场 / 慢行游线 / 公共活动场），每个带 rationale + confidence
- 用户/使用场景：居民日常 + 游客打卡 + 节庆活动
- 强排约束摘要：场地长宽 `194m x 130m`、不规则多边形、存在高差、G317 主到达侧（medium）、盐曲滨水侧（medium）
- working_hypotheses：2-3 条概念方向假设（不出图，纯文字结构）
- 阻塞项：哪些不能等（直接进 S4 提问）、哪些不影响 S9 骨架推进

S3 不要画 CAD、不要算精确面积分配、不要写施工级控制，只输出"概念阶段方向"。

**M3. 写入 S4 marker（问题清单）**

按 `skills/S4_questions_summary/SKILL.md` 现有 marker 结构写。范围：

- 把 S1/S2/S3 的所有 low_confidence / pending / must_verify_before_construction 集中
- 分类：
  - `confirm_with_owner`（甲方）：例如"任务书是否要求多少日间游客容量"、"是否保留场地内疑似水利设施"
  - `confirm_with_survey`（测绘）：例如"DWG 单位是否为米"、"CAD-03/06/09 复核"、"高差具体数值"
  - `confirm_with_design_lead`（设计负责）：例如"主入口落具体哪一段红线"、"是否需要补 1-2 个桥头/交叉口语义控制点"
- 每条标 `soft_block` 或 `hard_block_for_construction_phase`
- 不要让任何 `soft_block` 阻塞 S9 骨架推进

**M4. 写入 S9 骨架 marker（汇报文档大纲）**

按 `skills/S9_report_outline/SKILL.md` 现有结构写。范围：

- **只写大纲和每节要点 bullet**，不写完整汇报正文（正文留给后续 S9 增强 skill 跑）
- 章节结构按用户战略文档 §5 给的 10 节：前期分析 / 场地认知 / 设计理念 / 规划结构 / 功能分区 / 流线与入口 / 景观/文化策略 / 专项设计 / 投资估算或实施建议 / 待确认问题
- 每节标"信息源 = S1/S2/S3/S4 哪些字段"，让后续 S9 增强 skill 知道去哪里读
- 配图清单只列"需要什么类型的图"，例如"区位关系示意图、场地照片拼贴、概念分区图、入口/流线示意图、节点透视参考"
- 不调用 `anthropic-skills:pptx`，PPT 阶段后置

**M5. 更新 workflow_state + completeness**

- 删除所有"S3 blocked by S1/S2 未确认"、"S9 blocked by S3 未执行"等过时阻塞
- `ready_for: [S3, S4, S5, S9]`（本轮 S3/S4/S9 都已落 marker，可以 ready）
- S5/S6/S7 标 `soft_block`，reason 写明"概念阶段可降级；待 S9 骨架反馈后再决定"
- 字段名以现有 schema 为准，**不动 `_schema/record.schema.md`**
- `low_confidence_count` / `pending_count` / `files_indexed_count` / `filled_required_pct` 按本轮实际更新

**M6. 验证 + commit + push**

```powershell
python _tools/validate_record.py 26-BQ-PARK
```

通过后：

```powershell
git add projects/26-BQ-PARK/05_output/record.md
git commit -m "docs(record): finalize S1/S2 9-point; draft light S3/S4/S9 skeletons"
git push origin main
```

如果 validate 报错，**就地修字段**，不要回本文件等审。schema 真的撑不住才回来。

**M7. 在本文件覆盖一条简短回执**

只要包含：
- commit hash + push 是否成功
- `validate_record.py 26-BQ-PARK` 输出尾部 3-5 行
- `git diff --stat HEAD~1..HEAD` 摘要
- 简短列：S1/S2/S3/S4/S9 各自 marker 已写入 ✓/✗

### 本轮硬约束（仍不能破）

- 不改 S1/S2 SKILL.md state 枚举（`map_located` / `cad_aligned`、`cad_only` / `control_points_needed` / `aligned`）
- 不改 `_schema/record.schema.md`
- 不动 P0+ 安全阀代码（`cad_align.py` / `server.py` / `app.js`）
- 不动 inventory.json（与 marker 改动无关）
- 不裸读 DWG / DOC 二进制
- 不要顺手新建 S6/S7/S10 SKILL.md（先在 S9 骨架的"专项设计"小节用文字 placeholder 占位）
- 不要在 S9 骨架里编造没有的历史汇报资料；如果 `03_references/` 还没历史汇报参考，就在该节标 pending

### 后续节奏（本轮 push 后会做什么）

reviewer 收到 M7 回执后**只看硬伤**（marker 越界、state 枚举值破坏、schema 违规）。无硬伤就放行下一阶段：

- **下一阶段 = S9 增强 skill 建设**：把 `skills/S9_report_outline/SKILL.md` 从"骨架生成"升级为"读 S1-S4 + 03_references 历史资料 + 标准模板 → 生成汇报正文"。这一阶段允许 codex 独立设计 + 实施 + 自测，**reviewer 只在 skill 影响多个项目的契约（例如改公共 schema、改其他 skill 的 marker 边界）时停**。
- 再下一阶段 = S10 PPT 大纲 skill + 接入 `anthropic-skills:pptx` 生成 .pptx。

### 开工

立即按 M1-M7 顺序做完一次性 push。不要再贴草稿等审。
