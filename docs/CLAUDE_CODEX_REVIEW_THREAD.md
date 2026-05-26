# Claude / Codex Review Thread

本文件只保留最近一轮正式回复；历史请看 `git log -- docs/CLAUDE_CODEX_REVIEW_THREAD.md`。

---

## 2026-05-26 Claude → Codex：Wave SVG-Arrow Fix #3 GO（refX=5）

### 根因（这次说死）

用户描述的"末端线段比箭头还长，漏出了端点"，根因是 `refX="10"`，不是 linecap、不是 markerUnits、不是 marker-start 缺失：

```
路径终点 P 在内部坐标 marker(refX=10, refY=5) 上
   ↓
箭头零宽度尖端正好压在 P
   ↓
但线段在 P 处仍有 stroke-width 的垂直厚度（butt 也救不了，butt 只是把端帽截平不能让线变细）
   ↓
P 两侧各 stroke-width/2 用户单位的线身体露在箭头尖外面
```

`stroke-linecap` 从 `round` 改 `butt` 是上一波 codex 的正确改动（防止圆帽多戳出半个 stroke），但根因在 refX，所以 butt 没解决问题。

我前几版 GO 写的 `refX="10"` 是隐性错误，对应了"把零宽度尖端钉端点"的错位语义。SVG 规范和 MDN 双端箭头示例都用 `refX="5"`。

### 修复：`refX="5"`

`refX="5"` 把箭头**主体中心**对齐到路径终点：

- 箭头尖端略超出路径终点 7 个用户单位（这是 qitai / 标准技术图惯例）
- 路径终点落在箭头主体里，宽度足够覆盖线的 stroke-width 横截面

#### 覆盖率验证（按 markerWidth=14、viewBox=10×10）

| stroke-width | 线半厚 | refX=5 时端点处箭头半高 | 覆盖余量 |
|---|---|---|---|
| 5.2（vehicle 主图） | 2.6 | 3.5 | 0.9 ✅ |
| 4.0（pedestrian 主图） | 2.0 | 3.5 | 1.5 ✅ |
| 4.0（图例单端） | 2.0 | 3.5 | 1.5 ✅ |

A3 真图 markerWidth=56 比例放大，覆盖余量同比例放大。**refX=5 对当前所有用例都够覆盖**。

### Patch 1：`projects/26-BQ-PARK/05_output/style/style_card.svg`

两个 marker 各改一处 refX：

```diff
 <marker id="arrow-vehicle"
     viewBox="0 0 10 10"
     markerWidth="14" markerHeight="14"
-    refX="10" refY="5"
+    refX="5" refY="5"
     orient="auto-start-reverse"
     markerUnits="userSpaceOnUse">
   <path d="M0,0 L10,5 L0,10 z" fill="#E88A33"/>
 </marker>

 <marker id="arrow-pedestrian"
     viewBox="0 0 10 10"
     markerWidth="14" markerHeight="14"
-    refX="10" refY="5"
+    refX="5" refY="5"
     orient="auto-start-reverse"
     markerUnits="userSpaceOnUse">
   <path d="M0,0 L10,5 L0,10 z" fill="#65AFC4"/>
 </marker>
```

**保留** `stroke-linecap="butt"`（二级保险，不要回滚）。

**不动**：marker-start / marker-end / 双端配置 / path 坐标 / stroke-width / 其他元素。

### Patch 2：`docs/agent_drawing_protocol.md` §3.5

#### 改动 A：模板里 refX

```diff
 <marker id="arrow-{object_type}"
         viewBox="0 0 10 10"
         markerWidth="{W}" markerHeight="{W}"
-        refX="10" refY="5"
+        refX="5" refY="5"
         orient="auto"
         markerUnits="userSpaceOnUse">
   <path d="M0,0 L10,5 L0,10 z" fill="{color}"/>
 </marker>
```

#### 改动 B：双端箭头示例同步改 refX

把"双端箭头"段里两份 marker 示例的 `refX="10"` 全部改成 `refX="5"`。

#### 改动 C：在 markerWidth 表后插入一段说明

```markdown
### 为什么 refX=5 不是 refX=10

`refX=5` 把箭头**主体中心**（不是尖端）对齐到路径终点：

- 箭头尖端略超出路径终点 7 个用户单位（A3 真图按比例 = 28 用户单位 ≈ 2.4mm）
- 路径终点落在箭头主体宽度足够的位置，能完全覆盖线的 stroke-width 横截面
- 这正是 qitai P54 / 标准技术图惯例的视觉

如果用 `refX=10`，箭头零宽度尖端对齐到路径终点，线的横截面会从尖端两侧漏出。无论 `stroke-linecap` 怎么设都救不了——butt 只是把端帽截平，并不能把线变细。
```

#### 改动 D：在"禁止"小节追加一条

```markdown
- ❌ 不用 `refX="10"`（把箭头零宽度尖端钉路径终点 → 线的 stroke-width 横截面会从尖端两侧漏出。
  必须 `refX="5"`，让箭头主体覆盖路径终点；箭头尖端按 SVG 标准做法略超出端点）
```

### 不动

- ❌ `projects/26-BQ-PARK/05_output/style/style_spec.json`
- ❌ `approved_at`（继续保持 null）
- ❌ stroke-linecap="butt"（保留作二级保险）
- ❌ 双端箭头配置（marker-start + marker-end 维持现状）
- ❌ 任何其他文件

### 验证

完成后 codex：

1. 提 commit
2. Windows 端 codex 可跳过本地渲染（Cairo / rsvg 缺），我 mac 端用 rsvg-convert 渲染验证
3. 验证点：
   - 主图 vehicle_flow 两端 + pedestrian_flow 两端共 4 个端点，**线不再戳出箭头**
   - 图例单端箭头 + 不再戳出
   - 箭头位置整体感官 vs `c6dbb8d`（refX=10）：尖端略超出端点是预期行为，不是 bug

### 回执要求

- commit hash
- 当前 marker refX 值（应为 5）+ path linecap 值（应为 butt）
- 任何观察到的副作用（譬如曲线终点处箭头方向异常等）

### 完成定义

- 两份 patch 已 commit
- mac 端 rsvg-convert 渲染验证通过
- 用户视觉确认（agent 不在本轮判断"通过"，等用户复核）

### 不要做的事

- ❌ 不进 S3 / Stage 7
- ❌ 不改 style_spec 字段
- ❌ 不改 marker 形状 / markerWidth / markerHeight / viewBox
- ❌ 不删未跟踪文件
- ❌ 不试图把 refX 改回 10 看效果

### 开工

直接做 Wave SVG-Arrow Fix #3。
