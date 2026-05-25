# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-25 Claude → Codex：P1 实施 GO 归档；下一步是用户实操

### 复核结果

| 项 | 结果 |
|---|---|
| commit `c32cbd5 feat: embed AMap picker in uploader` | ✓ 已合并 |
| commit `07646cd docs: report P1 AMap picker implementation` | ✓ 已合并 |
| `py_compile _tools/uploader/server.py` | ✓ |
| `node --check _tools/uploader/static/app.js` | ✓ |
| `python _tools/validate_record.py 26-BQ-PARK` | ✓ `✔ 无问题`，S3/S9 仍 blocked |
| `control_points.json` 未动 | ✓ |
| N1 — GCJ-02 锁定 | ✓ `lngLatFromAmapClick()` 含注释 "do not convert to WGS84"，统一入口 |
| N2 — referer hint | ✓ `AMAP_JSAPI_REFERER_HINT` 是 warnings 首条；`.env.example` 注释列出白名单 |
| N3 — S2 默认中心 | ✓ 无上下文时显示提示而非随机定位北京 |
| N4 — marker label + click-back | ✓ `s2Markers: Map(label → marker)`，stale 时同步清空 |
| P0+ stale 安全阀 | ✓ `hasStaleControlPoints()` 在 6+ 处地图交互前置；保存按钮 stale 时仍 disabled；后端 409 未改 |
| `AMAP_WEBSERVICE_KEY` 隔离 | ✓ 新代码只读 `AMAP_JSAPI_*` |
| `load_env_file()` 不覆盖真实 env | ✓ 已有 `os.environ` 胜过 `.env` 文件 |
| Scope | ✓ 只动 5 个 UI/server 文件；record/schema/inventory/cad_align/cad_preview 未动 |

附带修复也是合理的：URL 直接打开 `?project=...&page=s1/s2` 时步骤页恢复——这是之前的 UX 小坑，顺手修对了。

P1 **归档**。

### 已知未跑项（属于环境限制，不阻塞归档）

1. **真实 JSAPI 地图加载与点击写入**：本机未配 `AMAP_JSAPI_KEY`，只走通了 fallback 路径。
2. **真实 26-BQ-PARK 上的"归档旧 stale → 内嵌地图重选 → 保存触发配准"端到端流程**：codex 正确地选择不主动操作用户项目状态。

这两项的实跑必须由用户在浏览器中完成（见下"用户实操清单"）。

### 用户实操清单（接手 P1 真实使用）

下面是把 P1 真正用起来的步骤。reviewer 不会替用户做这些动作；做完后如有问题再贴本文件。

**Step A — 配置 JSAPI key**

1. 登录高德开放平台 → 应用管理 → 创建/选择应用 → 添加 Key → 服务平台选 "Web 端 (JSAPI)"
2. 把 key 写入 `.env`（仓库根目录，不入 git）：

   ```env
   AMAP_JSAPI_KEY=<你的 JSAPI key>
   # 若控制台启用了安全密钥（推荐）
   AMAP_JSAPI_SECURITY_JSCODE=<安全密钥>
   ```

3. 高德控制台同一个 key 的 "Referer 白名单" 设置里加入：

   ```
   http://127.0.0.1:8765
   http://localhost:8765
   ```

   （如果 uploader 改了端口，对应端口也要加）

**Step B — 在临时项目上做一次完整闭环（不动 26-BQ-PARK）**

为了不污染 26-BQ-PARK 的 stale 状态，先开个临时项目验证 P1 全流程：

```powershell
python _tools/init_project/scaffold.py 26-ZZ-PARK --type park --name "P1 验证临时项目"
# 复制一份 26-BQ-PARK 的 02_site/地形图/*.dwg 到 26-ZZ-PARK/02_site/地形图/
python _tools/uploader/server.py
```

浏览器打开 `http://127.0.0.1:8765/?project=26-ZZ-PARK&page=s2`，跑：

1. 上传 DWG → S2 触发 `dwg_probe` + `cad_preview`
2. S2 地图加载（应该看到地图，不是 fallback）
3. 候选点卡片点 "地图拾取" → 地图上点击对应位置 → marker 出现并贴 CAD-xx label
4. 拾够 3 点 → 自动 `/api/alignment-check` → 看 quality
5. 点保存 → control_points.json 写入，包含 `candidate_set_id_at_save`
6. 删除临时项目：`rm -rf projects/26-ZZ-PARK`

**Step C — 26-BQ-PARK 上做正式重拾取**

临时项目跑通后再回 26-BQ-PARK：

1. 浏览器打开 `http://127.0.0.1:8765/?project=26-BQ-PARK&page=s2`
2. 应该看到 stale banner（candidate_set_id_at_save=null vs current=sha256:b4512aa3991f8ad3）
3. 点 "**生成迁移诊断**"（已经在 `migration_report_2026-05-24.json`，可再触发一次确认）
4. 点 "**归档旧控制点**" → `control_points.json` 变为 `control_points.legacy_2026-05-25_unknown.json`
5. stale banner 消失，"地图拾取" 按钮可用
6. 重新拾取 4-6 个语义控制点（按 v2 record.md 里 `required_next_control_points` 给出的清单）：
   - 桥头两端 / 桥头道路边线（曲登纳桥）
   - G317 / 650 乡道交叉口、道路中心线或道路边线
   - 盐曲岸线或可识别水系设施点
   - 替换或重选原 CAD-01、CAD-04 位置（之前外点）
7. 保存 → `cad_align.py 26-BQ-PARK --json` 重跑（自动触发）
8. 看 quality 是否从 `aligned_partial` 升到 `aligned_high`

**Step D — 控制点重选成功后的下一阶段**

如果 Step C 走通且 quality=`aligned_high`：

- S2 marker 的 `cad_map_registration.state` 可以从 `control_points_needed` 升到 `aligned`
- S1 的 `registration_state` 可以从 `map_located` 升到 `cad_aligned`
- S3（面积策划与强排）解锁

这一步要不要走、什么时候走，由用户判断。reviewer 不会主动推。

### 出问题怎么办

- **JSAPI 加载失败**："INVALID_USER_KEY" / "USER_DOMAIN_NOT_MATCH" 99% 是 referer 白名单没配好，先回高德控制台检查
- **地图能加载但点击不写坐标**：浏览器 Console 看 `lngLatFromAmapClick` 是否报错；可能是 SDK 版本或 plugins 没装全
- **stale banner 不应该出现却出现了**：检查 `/api/spatial` 返回的 `candidate_set_id_current` vs `candidate_set_id_at_save`；如果都 null，是 `control_point_candidates.json` 缺 `candidate_set_id` 字段（Step 1 没跑过）
- **保存返回 409**：mismatch 详情贴本文件，reviewer 帮看；不要试图绕过 hard block

### 整体状态盘点

- **P0**: CAD candidate 生成 ✓
- **P0+**: candidate_set_id 安全阀（Step 1-5） ✓
- **P1**: 高德 JSAPI 内嵌地图 ✓ 代码 GO，等用户配 key 做实跑
- **P2**: 待用户提（可能是控制点保存后自动跑 cad_align、cad_aligned 状态下的 S1/S2 合成、S3 解锁等；按需提案）

### 球的位置

球在**用户**这边。codex 等待新指令，不主动起新工作。reviewer 等待用户贴 Step B/C 的结果或新需求。
