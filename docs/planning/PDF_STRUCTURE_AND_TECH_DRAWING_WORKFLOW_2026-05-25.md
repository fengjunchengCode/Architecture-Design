# PDF Structure And Technical Drawing Workflow

Date: 2026-05-25

This document summarizes two reference report PDFs, the failed CAD-only drawing POC, and the proposed workflow for producing architectural report/PPT technical diagrams from project assets.

## Reference PDFs

The two reference PDFs are now included in the repository for remote review:

- `docs/reference_pdfs/report_examples/202600520西藏长江大厦建设项目-4.pdf`
- `docs/reference_pdfs/report_examples/20260410西藏启泰直销市场建设项目-3.pdf`

Original local sources:

- `D:\建筑设计资料集\文本\202600520西藏长江大厦建设项目-4.pdf`
- `D:\建筑设计资料集\文本\20260410西藏启泰直销市场建设项目-3.pdf`

They are large but below the GitHub single-file limit:

- 长江大厦 PDF: 113 pages, about 59,619 extracted text chars, about 68.8 MB.
- 启泰市场 PDF: 170 pages, about 93,561 extracted text chars, about 68.8 MB.

Both PDFs contain a usable text layer. Many visual pages still require rendered page images for layout and graphic analysis.

## Public Structure Found In Both PDFs

The two PDFs share a highly similar report/deck structure:

1. Cover
2. Contents
3. Front procedures / approval attachments
4. Meeting review and response to comments
5. Design proposal
6. Technical drawings
7. Design description
8. Comparison schemes

More detailed common structure:

- Cover and metadata
- Contents
- 前置手续
  - design qualification certificates
  - Tibet registration procedures
  - land certificate / real estate certificate
  - construction land planning permit
  - land redline drawing
  - planning conditions and attachments
  - design index comparison table
- 会议审查及修改情况
  - expert review comments
  - response items
  - drawing/text amendments
- 设计方案
  - project overview
  - location analysis
  - existing site conditions
  - base information and planning requirements
  - urban/architectural style zone
  - design objective
  - master plan and economic indicators
  - bird-eye renderings and perspective renderings
  - sunlight, greenery, function, traffic, fire, vertical, sponge city, accessibility, civil defense
  - product/building design
  - cultural element extraction
  - facade materials
- 技术图纸
  - plans, elevations, sections, roof, basement, title blocks
- 设计说明
  - general design description
  - site planning
  - architecture
  - structure
  - water supply and drainage
  - electrical
  - HVAC
  - energy/carbon
  - fire protection
  - green building
  - civil defense
- 对比方案
  - scheme 1
  - scheme 2

## Key Pages In 启泰市场 PDF

The following pages are especially useful as templates for future workflow analysis:

- P37: 区位分析
- P38: 基地现状与条件
- P39: 基地基本信息
- P40: 风貌区位图
- P41-P42: 风貌设计对比
- P43: 设计目标
- P44: 总平面图与经济技术指标
- P45-P49: 鸟瞰/透视图
- P50: 日照分析专篇
- P51: 绿化设计专篇
- P52: 功能分区
- P53: 景观绿地规划设计分析图
- P54: 交通组织方案分析图及主次出入口示意图
- P55: 消防流线
- P56: 场地设计竖向分析图
- P57: 配套分析专篇
- P58: 海绵城市专篇
- P59: 无障碍设计专篇
- P60: 人防设计专篇
- P61-P63: 单体设计、文化元素、立面材料
- P64-P105: 技术图纸
- P106-P159: 设计说明
- P160-P170: 对比方案

## Lessons From The POC

We tested the raw CAD and effect-image assets from the two reference projects.

Source CAD/effect assets:

- `D:\建筑设计资料集\0520资料汇总\0519总平面图_t8_t8_t8.dwg`
- `D:\建筑设计资料集\0520资料汇总\5.18单体图_t8_t8_t8.dwg`
- `D:\建筑设计资料集\西藏启泰直销市场建设项目成果汇总0410\总平面图+指标\总图20260405_t8_t8(1).dwg`
- `D:\建筑设计资料集\西藏启泰直销市场建设项目成果汇总0410\单体平面\0403子项平面_t8_t8(1).dwg`
- `D:\建筑设计资料集\西藏启泰直销市场建设项目成果汇总0410\单体平面\人防-地下室平面图20260403_t8(1).dwg`
- `D:\建筑设计资料集\西藏启泰直销市场建设项目成果汇总0410\效果图\db2f534f5132c354e436f0f134201846.jpg`

Observed results:

- ODA File Converter + ezdxf can convert all tested DWGs to DXF.
- CAD layer extraction works technically.
- 启泰总平 CAD contains a usable redline layer `A-总图-红线`; extracted area is about 48,512.86 sqm, close to the PDF value 48,439 sqm.
- CAD-only redraw is not sufficient for report-quality technical drawings.
- The first script-based POC produced poor drawings because it mechanically redrew layers and did not understand design intent.
- Even using the rendered master-plan image as a background, manual hardcoded overlays still failed where they did not follow the actual road geometry.

Conclusion:

Pure script-based drawing generation is not the right target. The agent should not pretend it can infer traffic, landscape, or functional logic from CAD lines alone.

## Why The Rendered Master Plan Matters

For 启泰市场, the image below is not just a rendering; it is the design-intent carrier:

`D:\建筑设计资料集\西藏启泰直销市场建设项目成果汇总0410\效果图\db2f534f5132c354e436f0f134201846.jpg`

This image encodes:

- building identities and labels
- trading center groups
- parking building
- apartment/support building
- comprehensive building
- main entrance
- pedestrian entrance
- vehicle/fire entrances
- internal roads
- parking bands
- green buffers
- landscape pockets
- central plaza-like white paving zone

The PDF technical analysis pages appear to be derived from this visual master-plan base plus additional vector overlays, not from raw CAD linework alone.

Therefore, future drawing production should use the rendered master plan, exported CAD plan, or clean SU top view as the visual base, then add semantic overlays.

## Proposed Workflow

The correct workflow should be:

1. Use a visual base
   - rendered master plan
   - CAD-exported clean plan
   - SU top view or bird-eye view
2. Detect or manually sketch design intent
   - roads
   - entrances
   - functional zones
   - landscape nodes
   - fire routes
   - parking areas
   - elevation points
3. Store sketch objects as semantic JSON
4. Convert semantic JSON into finished HTML technical pages
5. Export HTML pages to PNG/PDF/PPTX

The user’s latest proposed direction is better than previous attempts:

- User draws rough sketches on the base image.
- Agent converts rough sketches into polished technical drawings.
- Different technical drawing types have specialized conversion skills.
- HTML is used as the editing/rendering layer before exporting to PDF/PPT.

This means human design intent and agent formatting responsibilities are separated.

## Proposed UI: Technical Drawing Annotation Workbench

The system should provide a small UI before trying to auto-generate full report drawings.

Core UI:

- choose base image
- choose drawing type
- draw/edit geometry on top of the base
- save semantic objects as JSON
- preview finished HTML drawing
- export PNG/PDF

Initial drawing types:

- `functional_zoning`
- `traffic_analysis`
- `landscape_analysis`
- `fire_route`
- `vertical_analysis`

Object primitives:

- point
- polyline
- polygon
- arrow
- label
- node circle
- buffer band

Coordinates should use normalized image coordinates from 0 to 1, not raw pixels. This makes output stable across preview, PDF, and PPT export.

Example semantic JSON:

```json
{
  "drawing_type": "traffic_analysis",
  "base_image": "assets/base/master_plan_render.jpg",
  "objects": [
    {
      "type": "vehicle_flow",
      "points": [[0.18, 0.85], [0.31, 0.62], [0.72, 0.58]],
      "label": "车行流线"
    },
    {
      "type": "pedestrian_flow",
      "points": [[0.43, 0.18], [0.45, 0.44], [0.48, 0.70]],
      "label": "人行流线"
    },
    {
      "type": "main_entrance",
      "point": [0.17, 0.87],
      "label": "园区主入口"
    }
  ]
}
```

## Specialized Skills Needed

The conversion from sketch to finished drawing should be split by drawing type.

### Functional Zoning Skill

Inputs:

- base image
- user polygons or labels
- CAD area and building names
- project program from `record.md`

Outputs:

- polished color regions
- legend
- functional explanation
- unresolved labels list

### Traffic Analysis Skill

Inputs:

- base image
- user-drawn vehicle/pedestrian/fire routes
- entrance point objects
- road/entrance facts from S1/S2/S4

Outputs:

- snapped or smoothed route arrows
- entrance symbols
- line hierarchy
- legend
- traffic text

Important: the route geometry must follow the user sketch or detected road geometry. It must not be invented by a script.

### Landscape Analysis Skill

Inputs:

- base image
- user-drawn landscape axes and nodes
- visual recognition of green/open spaces
- project design concept

Outputs:

- primary/secondary landscape axes
- primary/secondary nodes
- node labels
- supporting text

### Fire Route Skill

Inputs:

- base image
- user-drawn fire loop
- turning radius labels
- fire entrance points

Outputs:

- fire route drawing for presentation
- explicit professional-review disclaimer

### Vertical Analysis Skill

Inputs:

- base image or CAD topography
- elevation points
- slope arrows
- record/S2 terrain information

Outputs:

- elevation labels
- slope arrows
- drainage direction
- confidence boundary

## Relation To Current S1-S10 Workflow

S1/S2 should not be expected to produce all drawing decisions. They provide context and geometry:

- S1: location, surrounding roads/water/POIs, primary approach directions.
- S2: CAD geometry, redline, base plan, terrain and candidate control points.
- S3: design concept and functional strategy.
- S4: unresolved questions and risk boundaries.
- S5: concept plan and functional zoning.
- S6: technical drawing extraction and drafting tasks.
- S7: model/rendering interpretation.
- S9: report text and page structure.
- S10: PPT/PDF production.

The technical drawing workbench should sit mainly between S5-S7 and S9/S10:

- It consumes S1-S7 assets.
- It produces finished page visuals.
- S9/S10 then lay out report/PPT pages.

## Revised Strategy

Do not pursue “agent automatically generates all technical drawings from CAD.”

Use:

- agent-assisted drafting
- user sketching
- visual recognition
- CAD calibration
- HTML-based editable output
- drawing-type-specific skills

The architecture should be:

```text
base image / CAD / SU / render
        ↓
visual + CAD feature extraction
        ↓
annotation workbench
        ↓
semantic drawing JSON
        ↓
specialized technical drawing skill
        ↓
HTML finished page
        ↓
PNG / PDF / PPTX
```

## Immediate POC Proposal

Build a minimal `technical_drawing_workbench` POC:

1. Load one base image.
2. Support two drawing types:
   - `traffic_analysis`
   - `functional_zoning`
3. Let user draw:
   - points
   - polylines
   - polygons
   - labels
4. Save normalized JSON.
5. Render one finished HTML page.
6. Export PNG/PDF.

Do not attempt automatic road detection in POC 1. Let the user draw rough intent first, then agent normalizes it.

## Questions For Claude Review

Please review feasibility and architecture:

1. Is the proposed “HTML annotation workbench + semantic JSON + specialized conversion skills” the right direction?
2. Should this be implemented as part of the existing uploader UI or as a separate local tool first?
3. What is the minimum schema for semantic drawing JSON?
4. Should the drawing JSON become part of `record.md`, or remain as derived files under `05_output/drawings/`?
5. How should S5/S6/S7 skills consume and produce these drawings?
6. What should be the first POC: traffic analysis, functional zoning, or both?
7. Are the two reference PDFs sufficient for template-learning, or should we add source PPT/CAD/SU examples too?

## Current Recommendation

Start with a separate POC tool, not a full workflow rewrite:

- `05_output/drawings/` for semantic JSON and generated HTML/PNG/PDF.
- UI page for drawing annotations on a base image.
- Renderer for `functional_zoning` and `traffic_analysis`.
- Later integrate into S5/S6/S7 and S9/S10.

This keeps the experiment reversible and avoids breaking the current project execution flow.
