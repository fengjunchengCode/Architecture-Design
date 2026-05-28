(function () {
  const DEFAULT_DRAWING_TYPE = "functional_zoning";
  const DRAWING_STATUS = new Set(["enabled", "planned", "deprecated"]);
  const DRAWING_CATEGORY = new Set(["analysis_a", "context_b", "other"]);
  const GEOMETRY_OPTIONS = [
    { value: "polygon", label: "多边形" },
    { value: "arrow", label: "箭头" },
    { value: "polyline", label: "折线" },
    { value: "point", label: "点" },
  ];
  const SOURCE_OPTIONS = [
    { value: "user_sketch", label: "用户手绘" },
    { value: "vision_inferred", label: "视觉识别" },
    { value: "cad_extracted", label: "CAD 提取" },
  ];
  const UNDO_LIMIT = 50;
  const PALETTE_FALLBACK = [
    "#D6CBB8",
    "#C2D0DB",
    "#E0D2C2",
    "#CFD4BF",
  ];
  const DEFAULT_ZONE_STYLE = {
    fill_color: "#DCE8C8",
    fill_enabled: true,
    border_style: "solid",
    stroke_width: 0.003,
  };
  const ZONE_STROKE_WIDTHS = {
    thin: 0.002,
    medium: 0.003,
    bold: 0.0045,
  };
  const ZONE_EDIT_WIDTH = 0.003;
  const HANDLE_BASE_R_PX = 6;
  const CLOSE_HANDLE_R_PX = 10;
  const RECENT_COLOR_LIMIT = 6;
  const CANVAS_ZOOM_MIN = 0.5;
  const CANVAS_ZOOM_MAX = 4;
  const CANVAS_ZOOM_STEP = 0.25;
  const CANVAS_WHEEL_ZOOM_FACTOR = 1.1;
  const DRAWING_WORKBENCHES = {
    functional_zoning: {
      status: "enabled",
      category: "analysis_a",
      label: "功能分区",
      title: "功能分区工作台",
      description: "标注功能区边界、功能名称和必要标签，保存为后续精绘分区图的语义证据。",
      fixedObjectType: "functional_zone",
      fixedGeometry: "polygon",
      fixedSource: "user_sketch",
      hideCanvasLabels: true,
      paletteFallback: PALETTE_FALLBACK,
      objectTypes: [
        { value: "functional_zone", label: "功能区", defaultGeometry: "polygon" },
      ],
      taskButtonLabel: "生成分区图任务包",
      agentNotesPlaceholder: "例如：请把不同功能区整理为低饱和分区色块，并生成底部图例。",
    },
    traffic_analysis: {
      status: "enabled",
      category: "analysis_a",
      label: "交通分析",
      title: "交通分析工作台",
      description: "标注车行、人行、入口和关键流线，保存为后续精绘交通组织图的语义证据。",
      objectTypes: [
        { value: "vehicle_flow", label: "车行流线", defaultGeometry: "arrow" },
        { value: "pedestrian_flow", label: "人行流线", defaultGeometry: "arrow" },
        { value: "main_entrance", label: "主入口", defaultGeometry: "point" },
        { value: "label", label: "标签", defaultGeometry: "point" },
      ],
      taskButtonLabel: "生成交通图任务包",
      agentNotesPlaceholder: "例如：请将橙色理解为车行主流线，蓝绿色为人行流线。",
    },
    landscape_analysis: {
      status: "planned",
      category: "analysis_a",
      label: "景观分析",
      title: "景观分析工作台",
      description: "待设计：景观节点、视线廊道、活动场景、水系关系等。",
    },
    fire_route: {
      status: "planned",
      category: "analysis_a",
      label: "消防流线",
      title: "消防流线工作台",
      description: "待设计：消防车道、登高面、回车场、消防出入口等。",
    },
    vertical_analysis: {
      status: "planned",
      category: "analysis_a",
      label: "竖向分析",
      title: "竖向分析工作台",
      description: "待设计：场地高差、坡向、台地、挡墙和排水组织等。",
    },
  };

  const state = {
    project: "",
    drawing: null,
    currentDrawingType: DEFAULT_DRAWING_TYPE,
    objects: [],
    currentPoints: [],
    selectedId: "",
    loadedBaseUrl: "",
    svgExists: false,
    svgUrl: "",
    styleSpec: null,
    dirty: false,
    undoStacks: {},
    redoStacks: {},
    zoneDraftStyle: { ...DEFAULT_ZONE_STYLE },
    zoneDraftLabel: "",
    zoneRecentColors: [],
    canvasZoom: 1,
    imageLoadToken: 0,
    overlayRetryPending: false,
    arcDrag: null,
  };

  const $ = (selector) => document.querySelector(selector);
  const api = (path, options = {}) => {
    if (window.architectureUploader && window.architectureUploader.api) {
      return window.architectureUploader.api(path, options);
    }
    return fetch(path, options).then(async (response) => {
      const data = await response.json();
      if (!response.ok) throw new Error(data.error || "request failed");
      return data;
    });
  };

  validateRegistry();

  function validateRegistry() {
    Object.entries(DRAWING_WORKBENCHES).forEach(([key, config]) => {
      if (!DRAWING_STATUS.has(config.status)) {
        console.warn(`[workbench] unknown drawing status: ${key} -> ${config.status}`);
      }
      if (!DRAWING_CATEGORY.has(config.category)) {
        console.warn(`[workbench] unknown drawing category: ${key} -> ${config.category}`);
      }
    });
  }

  function projectCode() {
    const appProject =
      window.architectureUploader && window.architectureUploader.getProject
        ? window.architectureUploader.getProject()
        : "";
    return appProject || new URLSearchParams(window.location.search).get("project") || "";
  }

  function initialDrawingType() {
    const requested = new URLSearchParams(window.location.search).get("drawing");
    return DRAWING_WORKBENCHES[requested] ? requested : DEFAULT_DRAWING_TYPE;
  }

  function drawingType() {
    const hidden = $("#drawingType");
    return state.currentDrawingType || (hidden && hidden.value) || DEFAULT_DRAWING_TYPE;
  }

  function drawingConfig(type = drawingType()) {
    return DRAWING_WORKBENCHES[type] || DRAWING_WORKBENCHES[DEFAULT_DRAWING_TYPE];
  }

  function isFunctionalZoning(type = drawingType()) {
    return type === "functional_zoning";
  }

  function isEnabled(type = drawingType()) {
    return drawingConfig(type).status === "enabled";
  }

  function basePath() {
    const input = $("#baseImagePath");
    return (input && input.value.trim()) || "05_output/drawings/base/master_plan.jpg";
  }

  function setStatus(message, ok = true) {
    const el = $("#workbenchStatus");
    if (!el) return;
    el.textContent = message;
    el.style.color = ok ? "var(--muted)" : "var(--accent-2)";
  }

  function setTaskStatus(message, ok = true) {
    const el = $("#taskPackStatus");
    if (!el) return;
    el.textContent = message;
    el.style.color = ok ? "var(--muted)" : "var(--accent-2)";
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
  }

  function optionHtml(options, selected = "") {
    return options
      .map(
        (item) =>
          `<option value="${escapeHtml(item.value)}" ${item.value === selected ? "selected" : ""}>${escapeHtml(
            item.label,
          )}</option>`,
      )
      .join("");
  }

  function syncDrawingUrl(type) {
    const params = new URLSearchParams(window.location.search);
    params.set("drawing", type);
    const next = `${window.location.pathname}?${params.toString()}${window.location.hash || ""}`;
    window.history.replaceState(null, "", next);
  }

  function markDirty() {
    if (!isEnabled()) return;
    state.dirty = true;
    renderWorkspaceMeta();
  }

  function clearDirty() {
    state.dirty = false;
    renderWorkspaceMeta();
  }

  function stackFor(kind, type = drawingType()) {
    const stacks = kind === "redo" ? state.redoStacks : state.undoStacks;
    if (!stacks[type]) stacks[type] = [];
    return stacks[type];
  }

  function snapshotState() {
    return {
      objects: JSON.parse(JSON.stringify(state.objects)),
      currentPoints: JSON.parse(JSON.stringify(state.currentPoints)),
      selectedId: state.selectedId,
      zoneDraftStyle: { ...state.zoneDraftStyle },
      zoneDraftLabel: state.zoneDraftLabel,
    };
  }

  function restoreSnapshot(snapshot) {
    state.objects = JSON.parse(JSON.stringify(snapshot.objects || []));
    state.currentPoints = JSON.parse(JSON.stringify(snapshot.currentPoints || []));
    state.selectedId = snapshot.selectedId || "";
    state.zoneDraftStyle = normalizeZoneStyle(snapshot.zoneDraftStyle || state.zoneDraftStyle);
    state.zoneDraftLabel = snapshot.zoneDraftLabel || "";
    renderCanvasLayers("restore-snapshot");
    renderObjectList();
    renderSpecificTools();
    refreshLegendPreview();
    markDirty();
  }

  function pushUndoSnapshot() {
    const stack = stackFor("undo");
    stack.push(snapshotState());
    if (stack.length > UNDO_LIMIT) stack.shift();
    state.redoStacks[drawingType()] = [];
  }

  function resetHistory(type = drawingType()) {
    state.undoStacks[type] = [];
    state.redoStacks[type] = [];
  }

  function undoHistory() {
    const undoStack = stackFor("undo");
    if (!undoStack.length) {
      setStatus("没有可撤销的操作。", false);
      return;
    }
    const redoStack = stackFor("redo");
    redoStack.push(snapshotState());
    if (redoStack.length > UNDO_LIMIT) redoStack.shift();
    restoreSnapshot(undoStack.pop());
    setStatus("已撤销。");
  }

  function redoHistory() {
    const redoStack = stackFor("redo");
    if (!redoStack.length) {
      setStatus("没有可重做的操作。", false);
      return;
    }
    const undoStack = stackFor("undo");
    undoStack.push(snapshotState());
    if (undoStack.length > UNDO_LIMIT) undoStack.shift();
    restoreSnapshot(redoStack.pop());
    setStatus("已重做。");
  }

  function resetInteraction() {
    state.currentPoints = [];
    state.selectedId = "";
  }

  async function confirmDirtySwitch() {
    if (!state.dirty) return true;
    const action = await askDirtyAction();
    if (action === "save") {
      await saveDrawing();
      return true;
    }
    return action === "discard";
  }

  function askDirtyAction() {
    const dialog = $("#dirtyDialog");
    const save = $("#dirtySaveSwitch");
    const discard = $("#dirtyDiscardSwitch");
    const cancel = $("#dirtyCancelSwitch");
    if (!dialog || !save || !discard || !cancel) {
      return Promise.resolve("cancel");
    }
    dialog.hidden = false;
    return new Promise((resolve) => {
      const cleanup = (value) => {
        dialog.hidden = true;
        save.removeEventListener("click", onSave);
        discard.removeEventListener("click", onDiscard);
        cancel.removeEventListener("click", onCancel);
        document.removeEventListener("keydown", onKeydown);
        resolve(value);
      };
      const onSave = () => cleanup("save");
      const onDiscard = () => cleanup("discard");
      const onCancel = () => cleanup("cancel");
      const onKeydown = (event) => {
        if (event.key === "Escape") cleanup("cancel");
      };
      save.addEventListener("click", onSave);
      discard.addEventListener("click", onDiscard);
      cancel.addEventListener("click", onCancel);
      document.addEventListener("keydown", onKeydown);
    });
  }

  async function setCurrentDrawing(type, options = {}) {
    const next = DRAWING_WORKBENCHES[type] ? type : DEFAULT_DRAWING_TYPE;
    const changed = next !== state.currentDrawingType;
    if (changed && !options.skipDirty) {
      const canLeave = await confirmDirtySwitch().catch((err) => {
        setStatus(err.message, false);
        return false;
      });
      if (!canLeave) {
        renderDrawingTabs();
        return false;
      }
    }

    state.currentDrawingType = next;
    const hidden = $("#drawingType");
    if (hidden) hidden.value = next;
    syncDrawingUrl(next);
    resetInteraction();
    setCanvasZoom(1, { render: false });
    state.dirty = false;
    renderDrawingTabs();
    renderDrawingWorkspace();

    if (isEnabled(next) && options.load !== false) {
      await loadDrawing();
    } else if (!isEnabled(next)) {
      state.drawing = null;
      state.objects = [];
      state.svgExists = false;
      state.svgUrl = "";
      renderObjects();
      renderObjectList();
      renderSvgDraft();
      setStatus("该图纸工作台待设计，暂不能保存或打包。");
      setTaskStatus("该图纸工作台待设计，暂不能生成 task_pack。", false);
    }
    return true;
  }

  function renderDrawingTabs() {
    const tabs = $("#drawingTabs");
    if (!tabs) return;
    tabs.innerHTML = Object.entries(DRAWING_WORKBENCHES)
      .map(([key, config]) => {
        const active = key === drawingType();
        const planned = config.status !== "enabled";
        const suffix = config.status === "planned" ? " · 待设计" : config.status === "deprecated" ? " · 已停用" : "";
        return `
          <button
            class="drawing-tab ${active ? "active" : ""} ${planned ? "planned" : "enabled"}"
            type="button"
            role="tab"
            aria-selected="${active ? "true" : "false"}"
            data-drawing-type="${escapeHtml(key)}"
          >
            <span>${escapeHtml(config.label)}</span>
            ${suffix ? `<small>${escapeHtml(suffix)}</small>` : ""}
          </button>
        `;
      })
      .join("");
    tabs.querySelectorAll("[data-drawing-type]").forEach((button) => {
      button.addEventListener("click", () => {
        setCurrentDrawing(button.dataset.drawingType).catch((err) => setStatus(err.message, false));
      });
    });
  }

  function renderDrawingWorkspace() {
    renderWorkspaceMeta();
    renderSpecificTools();
    renderAvailability();
  }

  function renderWorkspaceMeta() {
    const config = drawingConfig();
    const title = $("#drawingWorkspaceTitle");
    const description = $("#drawingWorkspaceDescription");
    const stateEl = $("#drawingWorkspaceState");
    const planned = $("#plannedWorkspace");
    const plannedTitle = $("#plannedTitle");
    const plannedDescription = $("#plannedDescription");
    if (title) title.textContent = config.title || `${config.label}工作台`;
    if (description) description.textContent = config.description || "";
    if (stateEl) {
      stateEl.className = `eyebrow workspace-state ${config.status}`;
      stateEl.textContent =
        config.status === "enabled" ? (state.dirty ? "有未保存修改" : "可编辑") : "待设计";
    }
    if (planned) {
      planned.hidden = config.status === "enabled";
      if (plannedTitle) plannedTitle.textContent = `${config.label}工作台待设计`;
      if (plannedDescription) {
        plannedDescription.textContent =
          config.description || "请在对话中定义该图纸的对象类型、输入方式和输出目标后再启用。";
      }
    }
  }

  function renderSpecificTools() {
    const tools = $("#drawingSpecificTools");
    if (!tools) return;
    const config = drawingConfig();
    if (config.status !== "enabled") {
      tools.innerHTML = "";
      return;
    }
    if (isFunctionalZoning()) {
      renderFunctionalZoningTools(tools);
      return;
    }
    const currentObject = $("#objectType") && $("#objectType").value;
    const objectTypes = config.objectTypes || [];
    const selectedObject = objectTypes.some((item) => item.value === currentObject)
      ? currentObject
      : (objectTypes[0] && objectTypes[0].value) || "label";
    const selectedGeometry =
      (objectTypes.find((item) => item.value === selectedObject) || {}).defaultGeometry || "point";
    tools.innerHTML = `
      <label>
        <span>对象类型</span>
        <select id="objectType">${optionHtml(objectTypes, selectedObject)}</select>
      </label>
      <label>
        <span>几何类型</span>
        <select id="geometryKind">${optionHtml(GEOMETRY_OPTIONS, selectedGeometry)}</select>
      </label>
      <label>
        <span>标签文本</span>
        <input id="objectLabel" placeholder="如：主入口 / 休闲活动区">
      </label>
      <label>
        <span>来源</span>
        <select id="objectSource">${optionHtml(SOURCE_OPTIONS, "user_sketch")}</select>
      </label>
    `;
    const objectType = $("#objectType");
    if (objectType) objectType.addEventListener("change", setDefaultGeometry);
    setDefaultGeometry();
  }

  function renderFunctionalZoningTools(tools) {
    const selected = selectedObject();
    const activeStyle = selected ? normalizeZoneStyle(selected.style_hints) : normalizeZoneStyle(state.zoneDraftStyle);
    const palette = zonePaletteItems();
    const recentColors = state.zoneRecentColors.filter(isHexColor);
    const label = selected ? selected.label || "" : state.zoneDraftLabel || "";
    tools.innerHTML = `
      <label class="zone-name-field">
        <span>分区名称 <small>名称只进图例，不显示在图中</small></span>
        <input id="objectLabel" placeholder="如：中心广场 / 活动草坪" value="${escapeHtml(label)}">
      </label>
      <div class="zone-tool-group">
        <span>填充颜色</span>
        <div class="zone-palette" id="zonePalette">
          ${palette
            .map(
              (item, index) => `
                <button
                  type="button"
                  class="zone-swatch ${item.color.toUpperCase() === activeStyle.fill_color ? "active" : ""} ${
                    item.fallback ? "fallback" : ""
                  }"
                  style="--swatch:${escapeHtml(item.color)}"
                  title="${item.fallback ? "补足色，后续风格协商会替换" : "风格色"}"
                  aria-label="选择颜色 ${index + 1}"
                  data-zone-color="${escapeHtml(item.color)}"
                ></button>
              `,
            )
            .join("")}
        </div>
        ${
          recentColors.length
            ? `
              <div class="zone-recent-colors" aria-label="最近使用颜色">
                <span class="zone-recent-label">最近使用</span>
                ${recentColors
                  .map(
                    (color) => `
                      <button
                        type="button"
                        class="zone-swatch zone-swatch-recent ${color === activeStyle.fill_color ? "active" : ""}"
                        style="--swatch:${escapeHtml(color)}"
                        title="最近使用颜色"
                        aria-label="选择最近使用颜色 ${escapeHtml(color)}"
                        data-zone-color="${escapeHtml(color)}"
                      ></button>
                    `,
                  )
                  .join("")}
              </div>
            `
            : ""
        }
        <input id="zoneCustomColor" type="color" value="${escapeHtml(activeStyle.fill_color)}" aria-label="自定义填充颜色">
      </div>
      <div class="zone-tool-group">
        <span>填充</span>
        <div class="segmented-control" id="zoneFillMode">
          <button type="button" class="${activeStyle.fill_enabled ? "active" : ""}" data-fill-enabled="true">有填充</button>
          <button type="button" class="${!activeStyle.fill_enabled ? "active" : ""}" data-fill-enabled="false">无填充</button>
        </div>
      </div>
      <div class="zone-tool-group">
        <span>边框</span>
        <div class="segmented-control" id="zoneBorderStyle">
          <button type="button" class="${activeStyle.border_style === "solid" ? "active" : ""}" data-border-style="solid">实线</button>
          <button type="button" class="${activeStyle.border_style === "dashed" ? "active" : ""}" data-border-style="dashed">虚线</button>
          <button type="button" class="${activeStyle.border_style === "none" ? "active" : ""}" data-border-style="none">无边框</button>
        </div>
      </div>
      <div class="zone-tool-group">
        <span>线宽 <small id="zoneStrokeWidthValue">${formatStrokeWidth(activeStyle.stroke_width)}</small></span>
        <input
          id="zoneStrokeWidth"
          type="range"
          min="0.001"
          max="0.012"
          step="0.0005"
          value="${escapeHtml(String(activeStyle.stroke_width))}"
          aria-label="分区边框线宽"
        >
      </div>
      <div class="zone-legend-preview" id="zoneLegendPreview">
        <h4>图例预览</h4>
        ${renderFunctionalZoneLegendPreview()}
      </div>
      <div class="zone-tool-group">
        <h4>对象明细</h4>
      </div>
    `;
    bindFunctionalZoningTools();
  }

  function buildFunctionalZoneLegendGroups(objects) {
    const groups = new Map();
    let invisibleCount = 0;
    objects.forEach((obj) => {
      if (obj.type !== "functional_zone") return;
      const style = normalizeZoneStyle(obj.style_hints);
      const isInvisible = !style.fill_enabled && style.border_style === "none";
      if (isInvisible) {
        invisibleCount++;
        return;
      }
      // 按可见性归一 key
      const key = JSON.stringify({
        fill: style.fill_enabled ? style.fill_color : null,
        border: style.border_style,
        stroke_width: style.border_style === "none" ? null : style.stroke_width,
      });
      if (!groups.has(key)) {
        groups.set(key, { style, objects: [] });
      }
      groups.get(key).objects.push(obj);
    });
    return { groups: Array.from(groups.values()), invisibleCount };
  }

  function renderFunctionalZoneLegendPreview() {
    const { groups, invisibleCount } = buildFunctionalZoneLegendGroups(state.objects);
    if (groups.length === 0 && invisibleCount === 0) {
      return '<p class="zone-legend-empty">暂无功能分区</p>';
    }
    const items = groups.map((group) => {
      const firstObj = group.objects[0];
      const labels = group.objects.map((obj) => obj.label).filter(Boolean);
      const uniqueLabels = [...new Set(labels)];
      let groupName = "";
      let nameHint = "";
      if (uniqueLabels.length === 0) {
        groupName = "功能分区";
      } else if (uniqueLabels.length === 1) {
        groupName = uniqueLabels[0];
      } else {
        groupName = `${uniqueLabels[0]} 等 ${uniqueLabels.length} 类`;
        nameHint = '<p class="zone-legend-hint">同一样式下存在多个名称，最终图例将按样式合并</p>';
      }
      const count = group.objects.length;
      const style = group.style;
      const hasBorder = style.border_style !== "none";
      const borderColor = hasBorder ? style.fill_color : "transparent";
      // swatch viewBox 24x16，映射 stroke_width 到 1-3px 范围以区分线宽差异
      const borderWidth = hasBorder ? Math.max(1, Math.min(3, Math.round(style.stroke_width * 300))) : 0;
      const dashArray = style.border_style === "dashed" ? "4 3" : "";
      return `
        <div class="zone-legend-item">
          <svg class="zone-legend-swatch" viewBox="0 0 24 16" aria-hidden="true">
            <rect x="1" y="1" width="22" height="14" rx="2"
              fill="${style.fill_enabled ? style.fill_color : 'none'}"
              fill-opacity="${style.fill_enabled ? '0.42' : '0'}"
              stroke="${borderColor}"
              stroke-width="${borderWidth}"
              ${dashArray ? `stroke-dasharray="${dashArray}"` : ''}
            />
          </svg>
          <span class="zone-legend-label">${escapeHtml(groupName)}</span>
          ${count > 1 ? `<span class="zone-legend-count">x ${count}</span>` : ''}
          ${nameHint}
        </div>
      `;
    }).join("");
    const invisibleHint = invisibleCount > 0
      ? `<p class="zone-legend-invisible-hint">有 ${invisibleCount} 个不可见对象未进入图例</p>`
      : "";
    return `${items}${invisibleHint}`;
  }

  function refreshLegendPreview() {
    const container = $("#zoneLegendPreview");
    if (!container) return;
    container.innerHTML = `
      <h4>图例预览</h4>
      ${renderFunctionalZoneLegendPreview()}
    `;
  }

  function selectedObject() {
    return state.objects.find((obj) => obj.id === state.selectedId) || null;
  }

  function zonePaletteItems() {
    const fromSpec = Object.values((state.styleSpec && state.styleSpec.palette && state.styleSpec.palette.functional_zones) || {})
      .filter(isHexColor)
      .map((color) => color.toUpperCase());
    const colors = fromSpec.length >= 10 ? fromSpec.slice(0, 10) : [...fromSpec, ...PALETTE_FALLBACK].slice(0, 10);
    return colors.map((color, index) => ({ color, fallback: index >= fromSpec.length }));
  }

  function zonePaletteColorSet() {
    return new Set(zonePaletteItems().map((item) => item.color.toUpperCase()));
  }

  function normalizeHexColor(value) {
    return isHexColor(value) ? String(value).trim().toUpperCase() : "";
  }

  function addRecentColor(value) {
    const color = normalizeHexColor(value);
    if (!color || zonePaletteColorSet().has(color)) return;
    state.zoneRecentColors = state.zoneRecentColors.filter((item) => item !== color);
    state.zoneRecentColors.push(color);
    if (state.zoneRecentColors.length > RECENT_COLOR_LIMIT) {
      state.zoneRecentColors = state.zoneRecentColors.slice(-RECENT_COLOR_LIMIT);
    }
  }

  function pruneRecentColors() {
    const palette = zonePaletteColorSet();
    state.zoneRecentColors = state.zoneRecentColors
      .map(normalizeHexColor)
      .filter((color, index, colors) => color && !palette.has(color) && colors.indexOf(color) === index)
      .slice(-RECENT_COLOR_LIMIT);
  }

  function rebuildRecentColorsFromObjects() {
    if (!isFunctionalZoning()) return;
    state.objects.forEach((obj) => addRecentColor(obj.style_hints && obj.style_hints.fill_color));
    pruneRecentColors();
  }

  function normalizeZoneStyle(style = {}) {
    const palette = zonePaletteItems();
    const fallbackColor = (palette[0] && palette[0].color) || DEFAULT_ZONE_STYLE.fill_color;
    const fillColor = isHexColor(style.fill_color) ? String(style.fill_color).toUpperCase() : fallbackColor;
    const borderStyle = ["solid", "dashed", "none"].includes(style.border_style)
      ? style.border_style
      : DEFAULT_ZONE_STYLE.border_style;
    const strokeWidth = normalizeStrokeWidth(style.stroke_width ?? ZONE_STROKE_WIDTHS[style.stroke_width_key]);
    return {
      fill_color: fillColor,
      fill_enabled: typeof style.fill_enabled === "boolean" ? style.fill_enabled : DEFAULT_ZONE_STYLE.fill_enabled,
      border_style: borderStyle,
      stroke_width: strokeWidth,
    };
  }

  function normalizeStrokeWidth(value) {
    const number = Number(value);
    if (!Number.isFinite(number)) return DEFAULT_ZONE_STYLE.stroke_width;
    return Math.min(0.012, Math.max(0.001, Number(number.toFixed(4))));
  }

  function formatStrokeWidth(value) {
    return normalizeStrokeWidth(value).toFixed(4);
  }

  function isHexColor(value) {
    return typeof value === "string" && /^#[0-9a-fA-F]{6}$/.test(value.trim());
  }

  function bindFunctionalZoningTools() {
    const labelInput = $("#objectLabel");
    if (labelInput) {
      labelInput.addEventListener("input", () => {
        if (!selectedObject()) state.zoneDraftLabel = labelInput.value;
      });
      labelInput.addEventListener("change", () => {
        const selected = selectedObject();
        if (!selected) {
          state.zoneDraftLabel = labelInput.value.trim();
          return;
        }
        const next = labelInput.value.trim();
        if ((selected.label || "") === next) return;
        pushUndoSnapshot();
        selected.label = next;
        markDirty();
        renderObjectList();
        refreshLegendPreview();
        setStatus("已更新分区名称。");
      });
    }

    document.querySelectorAll("#zonePalette [data-zone-color], .zone-recent-colors [data-zone-color]").forEach((button) => {
      button.addEventListener("click", () => updateZoneStyle({ fill_color: button.dataset.zoneColor }));
    });
    $("#zoneCustomColor")?.addEventListener("change", (event) => updateZoneStyle({ fill_color: event.target.value }));
    $("#zoneFillMode")?.querySelectorAll("[data-fill-enabled]").forEach((button) => {
      button.addEventListener("click", () => updateZoneStyle({ fill_enabled: button.dataset.fillEnabled === "true" }));
    });
    $("#zoneBorderStyle")?.querySelectorAll("[data-border-style]").forEach((button) => {
      button.addEventListener("click", () => updateZoneStyle({ border_style: button.dataset.borderStyle }));
    });
    $("#zoneStrokeWidth")?.addEventListener("input", (event) => {
      updateZoneStyle({ stroke_width: event.target.value }, { renderTools: false });
      const value = $("#zoneStrokeWidthValue");
      if (value) value.textContent = formatStrokeWidth(event.target.value);
    });
  }

  function updateZoneStyle(patch, options = {}) {
    const selected = selectedObject();
    const current = selected ? normalizeZoneStyle(selected.style_hints) : normalizeZoneStyle(state.zoneDraftStyle);
    const next = normalizeZoneStyle({ ...current, ...patch });
    if (JSON.stringify(current) === JSON.stringify(next)) return;
    pushUndoSnapshot();
    if (selected) {
      selected.style_hints = next;
      state.zoneDraftStyle = next;
      setStatus("已更新选中分区样式。");
    } else {
      state.zoneDraftStyle = next;
      setStatus("已更新新分区默认样式。");
    }
    if (Object.prototype.hasOwnProperty.call(patch, "fill_color")) addRecentColor(next.fill_color);
    markDirty();
    renderCanvasLayers("zone-style-update");
    renderObjectList();
    if (options.renderTools !== false) renderSpecificTools();
    refreshLegendPreview();
  }

  function renderAvailability() {
    const enabled = isEnabled();
    const layout = $("#workbenchLayout");
    if (layout) layout.hidden = !enabled;
    [
      "#workbenchSave",
      "#finishObject",
      "#undoPoint",
      "#redoAction",
      "#deleteObject",
      "#clearDraft",
      "#sendToAgent",
      "#exportDrawing",
      "#canvasZoomOut",
      "#canvasZoomReset",
      "#canvasZoomIn",
      "#canvasZoomFit",
    ].forEach((selector) => {
      const el = $(selector);
      if (el) el.disabled = !enabled || (selector === "#exportDrawing" && !state.svgExists);
    });
    const notes = $("#taskUserNotes");
    if (notes) notes.placeholder = drawingConfig().agentNotesPlaceholder || "";
    const send = $("#sendToAgent");
    if (send) send.textContent = drawingConfig().taskButtonLabel || "发给 agent 出图";
    const finish = $("#finishObject");
    if (finish) finish.textContent = isFunctionalZoning() ? "完成分区" : "完成对象";
    const undo = $("#undoPoint");
    if (undo) undo.textContent = isFunctionalZoning() ? "撤销" : "撤销最后一点";
    updateCanvasZoomUi();
  }

  function setCanvasZoom(value, options = {}) {
    const next = Math.min(CANVAS_ZOOM_MAX, Math.max(CANVAS_ZOOM_MIN, Number(value) || 1));
    state.canvasZoom = Number(next.toFixed(2));
    applyCanvasZoom();
    updateCanvasZoomUi();
    if (options.render !== false) renderCanvasLayers("zoom");
  }

  function applyCanvasZoom() {
    const stage = $("#workbenchStage");
    if (stage) stage.style.width = `${state.canvasZoom * 100}%`;
  }

  function adjustCanvasZoom(delta) {
    setCanvasZoom(state.canvasZoom + delta);
  }

  function updateCanvasZoomUi() {
    const reset = $("#canvasZoomReset");
    if (reset) reset.textContent = `${Math.round(state.canvasZoom * 100)}%`;
    const out = $("#canvasZoomOut");
    const zoomIn = $("#canvasZoomIn");
    if (out) out.disabled = !isEnabled() || state.canvasZoom <= CANVAS_ZOOM_MIN;
    if (zoomIn) zoomIn.disabled = !isEnabled() || state.canvasZoom >= CANVAS_ZOOM_MAX;
  }

  function renderCanvasLayers(reason = "", options = {}) {
    applyCanvasZoom();
    renderObjects();
    if (options.selfHeal !== false) scheduleOverlaySelfHeal(reason);
  }

  function scheduleOverlaySelfHeal(reason) {
    if (state.overlayRetryPending || !state.objects.length) return;
    const overlay = $("#sketchOverlay");
    if (!overlay || overlay.children.length) return;
    state.overlayRetryPending = true;
    requestAnimationFrame(() => {
      state.overlayRetryPending = false;
      const currentOverlay = $("#sketchOverlay");
      if (state.objects.length && currentOverlay && !currentOverlay.children.length) {
        console.warn("[workbench] overlay empty after render; retrying", reason);
        renderObjects();
      }
    });
  }

  function handleCanvasWheel(event) {
    if (!workbenchIsActive() || !isEnabled() || !(event.ctrlKey || event.metaKey)) return;
    const viewport = $("#workbenchCanvas");
    const stage = $("#workbenchStage");
    if (!viewport || !stage) return;
    event.preventDefault();
    const rect = stage.getBoundingClientRect();
    if (!rect.width || !rect.height) return;
    const xRatio = Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width));
    const yRatio = Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height));
    const factor = event.deltaY < 0 ? CANVAS_WHEEL_ZOOM_FACTOR : 1 / CANVAS_WHEEL_ZOOM_FACTOR;
    setCanvasZoom(state.canvasZoom * factor, { render: false });
    const nextRect = stage.getBoundingClientRect();
    viewport.scrollLeft += nextRect.left + xRatio * nextRect.width - event.clientX;
    viewport.scrollTop += nextRect.top + yRatio * nextRect.height - event.clientY;
    renderCanvasLayers("wheel-zoom");
  }

  async function loadStyle() {
    const project = projectCode();
    if (!project) {
      renderStyleStrip(null);
      return;
    }
    const params = new URLSearchParams({ project });
    const data = await api(`/api/style/load?${params}`);
    state.styleSpec = data.exists ? data.style_spec : null;
    renderStyleStrip(data);
    if (isFunctionalZoning()) {
      state.zoneDraftStyle = normalizeZoneStyle(state.zoneDraftStyle);
      state.objects = state.objects.map((obj) =>
        obj.type === "functional_zone" ? { ...obj, style_hints: normalizeZoneStyle(obj.style_hints) } : obj,
      );
      rebuildRecentColorsFromObjects();
      renderSpecificTools();
      renderObjectList();
      renderCanvasLayers("style-loaded");
    }
  }

  function renderStyleStrip(data, error = "") {
    const el = $("#styleStrip");
    if (!el) return;
    if (error) {
      el.textContent = `当前风格：读取失败，${error}`;
      return;
    }
    if (!data || !data.exists) {
      el.textContent = "当前风格：未建立 style_spec。修改风格请到对话窗口与 agent 协商。";
      return;
    }
    const spec = data.style_spec || {};
    const palette = spec.palette || {};
    const primary = palette.primary || palette.main || "未指定";
    const updated = spec.updated_at || "未知时间";
    const approved = spec.approved_at ? "已批准" : "待批准";
    el.textContent = `当前风格：${approved}，主色 ${primary}，上次更新 ${updated}。修改风格请到对话窗口与 agent 协商。`;
  }

  function objectStyle(type) {
    const styles = {
      functional_zone: { stroke: "#256d4f", fill: "rgba(60,145,110,0.28)" },
      vehicle_flow: { stroke: "#f97316", fill: "none" },
      pedestrian_flow: { stroke: "#0f766e", fill: "none" },
      main_entrance: { stroke: "#dc2626", fill: "#dc2626" },
      label: { stroke: "#111827", fill: "#111827" },
    };
    return styles[type] || styles.label;
  }

  function objectName(type) {
    for (const config of Object.values(DRAWING_WORKBENCHES)) {
      const item = (config.objectTypes || []).find((entry) => entry.value === type);
      if (item) return item.label;
    }
    return type;
  }

  function geometryName(kind) {
    const item = GEOMETRY_OPTIONS.find((entry) => entry.value === kind);
    return item ? item.label : kind;
  }

  function setDefaultGeometry() {
    const objectType = $("#objectType");
    const geometryKind = $("#geometryKind");
    if (!objectType || !geometryKind) return;
    const config = drawingConfig();
    const next = ((config.objectTypes || []).find((item) => item.value === objectType.value) || {}).defaultGeometry;
    if (next) geometryKind.value = next;
  }

  async function loadDrawing() {
    if (!isEnabled()) {
      setStatus("该图纸工作台待设计，暂不能加载语义草图。", false);
      return;
    }
    const project = projectCode();
    if (!project) {
      setStatus("请先打开或创建项目，再加载工作台。", false);
      return;
    }
    state.project = project;
    const params = new URLSearchParams({ project, drawing_type: drawingType() });
    const data = await api(`/api/drawing/load?${params}`);
    state.drawing = data.drawing;
    state.objects = Array.isArray(data.drawing.objects) ? data.drawing.objects : [];
    if (isFunctionalZoning()) {
      state.objects = state.objects
        .filter((obj) => obj.type === "functional_zone" && obj.geometry && obj.geometry.kind === "polygon")
        .map((obj) => ({ ...obj, source: "user_sketch", style_hints: normalizeZoneStyle(obj.style_hints) }));
      state.zoneDraftStyle = normalizeZoneStyle(state.zoneDraftStyle);
      rebuildRecentColorsFromObjects();
    }
    resetInteraction();
    resetHistory();
    state.svgExists = !!data.svg_exists;
    state.svgUrl = data.svg_url || "";
    clearDirty();
    const pathInput = $("#baseImagePath");
    if (pathInput) pathInput.value = data.drawing.base_image.path || basePath();
    const hasBaseImage = loadBaseImage(data.base_image_url, data.base_image_exists);
    renderSvgDraft();
    loadStyle().catch((err) => renderStyleStrip(null, err.message));
    renderCanvasLayers("load-drawing-sync");
    renderObjectList();
    refreshLegendPreview();
    renderAvailability();
    if (hasBaseImage) {
      setStatus(data.exists ? "已加载已保存的草图。" : "已初始化空白草图。");
      requestAnimationFrame(() => renderCanvasLayers("load-drawing-raf"));
    }
  }

  function loadBaseImage(url, exists) {
    const image = $("#baseImage");
    const empty = $("#workbenchEmpty");
    const stage = $("#workbenchStage");
    if (!image || !empty) return false;
    const token = state.imageLoadToken + 1;
    state.imageLoadToken = token;
    console.log("[workbench] loadBaseImage", { url, exists });
    if (!exists || !url) {
      image.removeAttribute("src");
      if (stage) stage.classList.remove("has-image");
      state.loadedBaseUrl = "";
      empty.hidden = false;
      empty.textContent = "未找到底图。请上传 JPG/PNG，或填写 05_output/drawings/base/ 下的底图路径。";
      setStatus("底图不存在，请先上传底图或填写已存在的底图路径。", false);
      return false;
    }
    state.loadedBaseUrl = `${url}&_=${Date.now()}`;
    let readyRendered = false;
    const markReady = (reason) => {
      if (token !== state.imageLoadToken || readyRendered) return;
      readyRendered = true;
      if (stage) stage.classList.add("has-image");
      setStatus(`底图已加载 ${image.naturalWidth}×${image.naturalHeight}。`);
      console.log("[workbench] base image ready", reason, image.naturalWidth, image.naturalHeight);
      requestAnimationFrame(() => renderCanvasLayers(`base-image-${reason}`));
    };
    image.onload = () => {
      markReady("onload");
    };
    image.onerror = () => {
      if (token !== state.imageLoadToken) return;
      if (stage) stage.classList.remove("has-image");
      setStatus(`底图加载失败：${state.loadedBaseUrl}`, false);
      console.error("[workbench] base image error", state.loadedBaseUrl);
    };
    image.src = state.loadedBaseUrl;
    if (image.complete && image.naturalWidth > 0) {
      markReady("complete");
    }
    empty.hidden = true;
    return true;
  }

  function buildDrawing() {
    const image = $("#baseImage");
    const naturalWidth = (image && image.naturalWidth) || (state.drawing && state.drawing.base_image.natural_width) || 1;
    const naturalHeight =
      (image && image.naturalHeight) || (state.drawing && state.drawing.base_image.natural_height) || 1;
    const objects = state.objects
      .filter((obj) => !isFunctionalZoning() || (obj.type === "functional_zone" && obj.geometry && obj.geometry.kind === "polygon"))
      .map((obj) => {
        if (isFunctionalZoning()) {
          const geometry = { kind: "polygon", coords: obj.geometry.coords };
          // T1: 仅含 ≥1 条真弧（quadratic）才持久化 segments
          if (obj.geometry.segments && obj.geometry.segments.some((s) => s.kind === "quadratic")) {
            geometry.segments = obj.geometry.segments;
            geometry.coords = sampleSegments(obj.geometry.segments);
          }
          return {
            id: obj.id,
            type: "functional_zone",
            geometry,
            label: obj.label || "",
            confidence: obj.confidence || "medium",
            source: "user_sketch",
            style_hints: normalizeZoneStyle(obj.style_hints),
          };
        }
        return {
          id: obj.id,
          type: obj.type,
          geometry: obj.geometry,
          label: obj.label || "",
          confidence: obj.confidence || "medium",
          source: obj.source || "user_sketch",
          style_hints: {},
        };
      });
    // T1: 条件写版本号 — 仅含 ≥1 条真弧（quadratic）才标 1.1
    const hasSegments = objects.some((obj) => obj.geometry && obj.geometry.segments);
    return {
      schema_version: hasSegments ? "1.1" : "1.0",
      drawing_type: drawingType(),
      project_code: state.project || projectCode(),
      base_image: {
        path: basePath(),
        natural_width: naturalWidth,
        natural_height: naturalHeight,
        source: "user_upload",
      },
      created_at: (state.drawing && state.drawing.created_at) || new Date().toISOString(),
      last_edited_by: "user",
      objects,
    };
  }

  function sampleSegments(segments) {
    if (!segments || !segments.length) return [];
    const coords = [segments[0].from];
    for (const segment of segments) {
      if (segment.kind === "line") {
        coords.push(segment.to);
      } else if (segment.kind === "quadratic") {
        const [fx, fy] = segment.from;
        const [cx, cy] = segment.control;
        const [tx, ty] = segment.to;
        const steps = 16;
        for (let i = 1; i <= steps; i++) {
          const t = i / steps;
          const mt = 1 - t;
          coords.push([
            Number((mt * mt * fx + 2 * mt * t * cx + t * t * tx).toFixed(6)),
            Number((mt * mt * fy + 2 * mt * t * cy + t * t * ty).toFixed(6)),
          ]);
        }
      }
    }
    // T2: 开环 — 去掉等于首点的尾点，保证 ≥3 点
    if (coords.length > 3) {
      const first = coords[0];
      const last = coords[coords.length - 1];
      if (Math.abs(first[0] - last[0]) < 1e-5 && Math.abs(first[1] - last[1]) < 1e-5) {
        coords.pop();
      }
    }
    return coords;
  }

  async function saveDrawing() {
    if (!isEnabled()) {
      setStatus("该图纸工作台待设计，暂不能保存。", false);
      return null;
    }
    const project = projectCode();
    if (!project) {
      setStatus("请先打开或创建项目，再保存。", false);
      return null;
    }
    state.project = project;
    const drawing = buildDrawing();
    const data = await api("/api/drawing/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project, drawing }),
    });
    state.drawing = data.drawing;
    clearDirty();
    setStatus(`已保存草图：${data.path}`);
    return data;
  }

  async function uploadBaseImage() {
    const project = projectCode();
    if (!project) {
      setStatus("请先打开或创建项目，再上传底图。", false);
      return;
    }
    const input = $("#baseImageFile");
    if (!input || !input.files || !input.files.length) {
      setStatus("请选择 JPG 或 PNG 底图文件。", false);
      return;
    }
    const form = new FormData();
    form.append("file", input.files[0]);
    const params = new URLSearchParams({ project });
    const data = await api(`/api/drawing/base/upload?${params}`, {
      method: "POST",
      body: form,
    });
    const pathInput = $("#baseImagePath");
    if (pathInput) pathInput.value = data.path;
    if (state.drawing) {
      state.drawing.base_image.path = data.path;
    }
    loadBaseImage(data.url, true);
    setStatus(`底图已上传：${data.path}`);
  }

  async function sendToAgent() {
    if (!isEnabled()) {
      setTaskStatus("该图纸工作台待设计，暂不能生成 task_pack。", false);
      return;
    }
    const project = projectCode();
    if (!project) {
      setStatus("请先打开或创建项目，再打包。", false);
      return;
    }
    if (state.currentPoints.length) {
      const proceed = window.confirm("当前还有未完成对象点位，生成任务包不会包含这些点。是否继续？");
      if (!proceed) return;
    }
    await saveDrawing();
    const notes = $("#taskUserNotes");
    const data = await api("/api/drawing/task-pack", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project,
        drawing_type: drawingType(),
        user_notes: notes ? notes.value.trim() : "",
      }),
    });
    setTaskStatus(`已生成：${data.task_pack}。请到对话窗口找 agent 处理该 task_pack。`);
    setStatus("已打包草图证据，等待 agent 精绘 SVG。");
  }

  async function exportDrawing() {
    if (!isEnabled()) {
      setStatus("该图纸工作台待设计，暂不能导出。", false);
      return;
    }
    const project = projectCode();
    if (!project) {
      setStatus("请先打开或创建项目，再导出。", false);
      return;
    }
    const params = new URLSearchParams({ project, drawing_type: drawingType() });
    const data = await api(`/api/drawing/export?${params}`, { method: "POST" });
    const outputs = data.outputs || {};
    setStatus(`已导出：${outputs.png || "PNG 未生成"}，${outputs.pdf || "PDF 未生成"}`);
  }

  function normalizedPoint(event) {
    const image = $("#baseImage");
    const stage = $("#workbenchStage");
    if (!image || !image.src || !image.naturalWidth || !isEnabled()) return null;
    if (!stage) return null;
    const rect = stage.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    if (x < 0 || x > 1 || y < 0 || y > 1) return null;
    return [Number(x.toFixed(6)), Number(y.toFixed(6))];
  }

  function addPoint(event) {
    if (event.target.closest && event.target.closest(".zone-arc-handle")) return;
    const point = normalizedPoint(event);
    if (!point) return;
    pushUndoSnapshot();
    if (!state.currentPoints.length && state.selectedId) {
      const selected = selectedObject();
      if (isFunctionalZoning() && selected) {
        state.zoneDraftStyle = normalizeZoneStyle(selected.style_hints);
      }
      state.selectedId = "";
    }
    if (isFunctionalZoning()) {
      state.currentPoints.push(point);
      markDirty();
      renderCanvasLayers("add-zone-point");
      renderObjectList();
      renderSpecificTools();
      return;
    }
    const geometryKind = $("#geometryKind");
    if (!geometryKind) return;
    state.currentPoints.push(point);
    markDirty();
    if (geometryKind.value === "point") finishObject();
    else renderObjects();
  }

  function finishObject() {
    if (!isEnabled()) return;
    if (isFunctionalZoning()) {
      finishFunctionalZone();
      return;
    }
    const geometryKind = $("#geometryKind");
    const objectType = $("#objectType");
    const objectLabel = $("#objectLabel");
    const objectSource = $("#objectSource");
    if (!geometryKind || !objectType || !objectSource) return;
    const kind = geometryKind.value;
    const minimum = { point: 1, polyline: 2, arrow: 2, polygon: 3 }[kind] || 1;
    if (state.currentPoints.length < minimum) {
      setStatus(`${geometryName(kind)} 至少需要 ${minimum} 个点。`, false);
      return;
    }
    pushUndoSnapshot();
    const index = state.objects.length + 1;
    const id = nextObjectId();
    const label = (objectLabel && objectLabel.value.trim()) || `${objectName(objectType.value)} ${index}`;
    const object = {
      id,
      type: objectType.value,
      geometry: { kind, coords: state.currentPoints.slice() },
      label,
      confidence: "medium",
      source: objectSource.value,
      style_hints: {},
    };
    state.objects.push(object);
    state.selectedId = id;
    state.currentPoints = [];
    markDirty();
    renderCanvasLayers("finish-object");
    renderObjectList();
    setStatus(`已添加：${label}`);
  }

  function finishFunctionalZone() {
    const minimum = 3;
    if (state.currentPoints.length < minimum) {
      setStatus(`多边形至少需要 ${minimum} 个点。`, false);
      return;
    }
    pushUndoSnapshot();
    const index = state.objects.length + 1;
    const id = nextObjectId();
    const labelInput = $("#objectLabel");
    const label = (labelInput && labelInput.value.trim()) || state.zoneDraftLabel.trim() || `功能区 ${index}`;
    const style = normalizeZoneStyle(state.zoneDraftStyle);
    const object = {
      id,
      type: "functional_zone",
      geometry: { kind: "polygon", coords: state.currentPoints.slice() },
      label,
      confidence: "medium",
      source: "user_sketch",
      style_hints: style,
    };
    state.objects.push(object);
    state.selectedId = id;
    state.zoneDraftStyle = style;
    state.zoneDraftLabel = "";
    state.currentPoints = [];
    markDirty();
    renderCanvasLayers("finish-zone");
    renderObjectList();
    renderSpecificTools();
    refreshLegendPreview();
    if (!style.fill_enabled && style.border_style === "none") {
      setStatus("该分区在图中不可见（无边框 + 无填充）。", false);
    } else {
      setStatus(`已添加分区：${label}`);
    }
  }

  function nextObjectId() {
    const max = state.objects.reduce((current, obj) => {
      const match = /^obj-(\d+)$/.exec(obj.id || "");
      return match ? Math.max(current, Number(match[1])) : current;
    }, 0);
    return `obj-${String(max + 1).padStart(3, "0")}`;
  }

  function undoPoint() {
    undoHistory();
  }

  function deleteSelected() {
    if (!state.selectedId) return;
    pushUndoSnapshot();
    state.objects = state.objects.filter((obj) => obj.id !== state.selectedId);
    state.selectedId = "";
    markDirty();
    renderCanvasLayers("delete-selected");
    renderObjectList();
    renderSpecificTools();
    refreshLegendPreview();
    setStatus("已删除选中对象。");
  }

  function clearDraft() {
    if (!state.objects.length && !state.currentPoints.length) return;
    pushUndoSnapshot();
    state.objects = [];
    state.currentPoints = [];
    state.selectedId = "";
    markDirty();
    renderCanvasLayers("clear-draft");
    renderObjectList();
    renderSpecificTools();
    refreshLegendPreview();
    setStatus("已清空当前草图。");
  }

  function renderObjects() {
    const overlay = $("#sketchOverlay");
    if (!overlay) return;
    overlay.innerHTML = [...state.objects.map(renderObjectSvg), renderDraftSvg()].join("");
    bindOverlaySelection(overlay);
  }

  function renderObjectSvg(obj) {
    if (isFunctionalZoning() && obj.type === "functional_zone") {
      return renderFunctionalZoneSvg(obj);
    }
    const style = objectStyle(obj.type);
    const selected = obj.id === state.selectedId;
    const width = selected ? 0.012 : 0.008;
    const coords = obj.geometry.coords;
    const points = coords.map((point) => point.join(",")).join(" ");
    const labelPoint = coords[Math.floor(coords.length / 2)] || coords[0];
    let shape = "";
    if (obj.geometry.kind === "polygon") {
      shape = `<polygon points="${points}" fill="${style.fill}" stroke="${style.stroke}" stroke-width="${width}"></polygon>`;
    } else if (obj.geometry.kind === "point") {
      const [x, y] = coords[0];
      shape = `<circle cx="${x}" cy="${y}" r="0.012" fill="${style.stroke}" stroke="#fff" stroke-width="0.004"></circle>`;
    } else {
      shape = `<polyline points="${points}" fill="none" stroke="${style.stroke}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round"></polyline>`;
    }
    return `${shape}${renderSvgLabel(obj.label, labelPoint, style.stroke)}`;
  }

  function renderFunctionalZoneSvg(obj) {
    const selected = obj.id === state.selectedId;
    const style = normalizeZoneStyle(obj.style_hints);
    const coords = obj.geometry.coords;
    const segments = obj.geometry.segments;
    const fill = style.fill_enabled ? style.fill_color : "none";
    const fillOpacity = style.fill_enabled ? "0.42" : "1";
    const strokeColor = style.border_style === "none" ? "none" : (selected ? darkenHex(style.fill_color, 0.2) : style.fill_color);
    const strokeWidth = style.border_style === "none" ? 0 : (style.stroke_width || ZONE_EDIT_WIDTH);
    const dash = style.border_style === "dashed" ? ' stroke-dasharray="0.014 0.01"' : "";

    // 有 segments 用 <path>，无 segments 用 <polygon>
    let visibleShape = "";
    let hitShape = "";
    if (segments && segments.length > 0) {
      const pathD = segmentsToPathD(segments);
      visibleShape = `
        <path
          d="${pathD}"
          fill="${fill}"
          fill-opacity="${fillOpacity}"
          stroke="${strokeColor}"
          stroke-width="${strokeWidth}"
          stroke-linejoin="round"${dash}
          pointer-events="none"
        ></path>
      `;
      const isDrawing = state.currentPoints.length > 0;
      if (!isDrawing) {
        const hasVisibleBorder = style.border_style !== "none";
        const hasVisibleFill = style.fill_enabled;
        if (hasVisibleBorder) {
          hitShape = `
            <path
              class="zone-hit"
              data-object-id="${escapeHtml(obj.id)}"
              d="${pathD}"
              fill="none"
              stroke="transparent"
              stroke-width="${getZoneHitStrokeWidth(style)}"
              pointer-events="stroke"
            ></path>
          `;
        } else if (hasVisibleFill) {
          hitShape = `
            <path
              class="zone-hit"
              data-object-id="${escapeHtml(obj.id)}"
              d="${pathD}"
              fill="transparent"
              stroke="none"
              pointer-events="fill"
            ></path>
          `;
        }
      }
    } else {
      const points = coords.map((point) => point.join(",")).join(" ");
      visibleShape = `
        <polygon
          points="${points}"
          fill="${fill}"
          fill-opacity="${fillOpacity}"
          stroke="${strokeColor}"
          stroke-width="${strokeWidth}"
          stroke-linejoin="round"${dash}
          pointer-events="none"
        ></polygon>
      `;
      const isDrawing = state.currentPoints.length > 0;
      if (!isDrawing) {
        const hasVisibleBorder = style.border_style !== "none";
        const hasVisibleFill = style.fill_enabled;
        if (hasVisibleBorder) {
          hitShape = `
            <polygon
              class="zone-hit"
              data-object-id="${escapeHtml(obj.id)}"
              points="${points}"
              fill="none"
              stroke="transparent"
              stroke-width="${getZoneHitStrokeWidth(style)}"
              pointer-events="stroke"
            ></polygon>
          `;
        } else if (hasVisibleFill) {
          hitShape = `
            <polygon
              class="zone-hit"
              data-object-id="${escapeHtml(obj.id)}"
              points="${points}"
              fill="transparent"
              stroke="none"
              pointer-events="fill"
            ></polygon>
          `;
        }
      }
    }

    // 选中时显示 handles
    let handles = "";
    if (selected) {
      // vertex handles
      handles = coords.map(([x, y]) => renderHandleSvg(x, y, "#fff", darkenHex(style.fill_color, 0.28))).join("");
      // 从 coords 初始化 segments（如果还没有）
      const segs = ensureSegments(obj);
      handles += renderSegmentHandles(obj.id, segs, style);
    }
    return `${visibleShape}${hitShape}${handles}`;
  }

  function segmentsToPathD(segments) {
    if (!segments || !segments.length) return "";
    let d = `M ${segments[0].from[0]} ${segments[0].from[1]}`;
    for (const seg of segments) {
      if (seg.kind === "line") {
        d += ` L ${seg.to[0]} ${seg.to[1]}`;
      } else if (seg.kind === "quadratic") {
        d += ` Q ${seg.control[0]} ${seg.control[1]} ${seg.to[0]} ${seg.to[1]}`;
      }
    }
    d += " Z";
    return d;
  }

  function renderSegmentHandles(objectId, segments, style) {
    let html = "";
    const handleColor = darkenHex(style.fill_color, 0.28);
    segments.forEach((seg, i) => {
      if (seg.kind === "line") {
        // 直线边：中点空心圆点（可拖出弧）
        const [mx, my] = [(seg.from[0] + seg.to[0]) / 2, (seg.from[1] + seg.to[1]) / 2];
        html += renderArcHandle(mx, my, objectId, i, false);
      } else if (seg.kind === "quadratic") {
        // quadratic 边：实心圆点（控制点）+ 辅助线
        html += renderArcHandle(seg.control[0], seg.control[1], objectId, i, true, handleColor);
        html += renderControlGuide(seg.from, seg.control, seg.to, handleColor);
      }
    });
    return html;
  }

  function renderArcHandle(x, y, objectId, segmentIndex, isQuadratic, fillColor) {
    const rx = getHandleRadiusX();
    const ry = getHandleRadiusY();
    const strokeW = getHandleStrokeWidth();
    const color = fillColor || "#fff";
    if (isQuadratic) {
      return `
        <ellipse
          class="zone-arc-handle"
          data-object-id="${escapeHtml(objectId)}"
          data-segment-index="${segmentIndex}"
          cx="${x}" cy="${y}" rx="${rx}" ry="${ry}"
          fill="${color}"
          stroke="#fff"
          stroke-width="${strokeW}"
          style="cursor:grab"
        ></ellipse>
      `;
    }
    return `
      <ellipse
        class="zone-arc-handle"
        data-object-id="${escapeHtml(objectId)}"
        data-segment-index="${segmentIndex}"
        cx="${x}" cy="${y}" rx="${rx}" ry="${ry}"
        fill="white"
        stroke="${darkenHex('#fff', 0.3)}"
        stroke-width="${strokeW}"
        style="cursor:grab"
      ></ellipse>
    `;
  }

  function renderControlGuide(from, control, to, color) {
    return `
      <polyline
        points="${from.join(",")} ${control.join(",")} ${to.join(",")}"
        fill="none"
        stroke="${color}"
        stroke-width="${getHandleStrokeWidth()}"
        stroke-dasharray="0.006 0.004"
        opacity="0.5"
        pointer-events="none"
      ></polyline>
    `;
  }

  /**
   * 计算功能分区命中 stroke-width。
   * SVG viewBox="0 0 1 1" 且 preserveAspectRatio="none"，单个 stroke-width 无法同时做到 x/y 屏幕恒定。
   * 此处按 stage 短边换算，是有意的宽松命中容差。
   */
  function getZoneHitStrokeWidth(style) {
    const baseWidth = style.stroke_width || ZONE_EDIT_WIDTH;
    const stage = $("#workbenchStage");
    if (!stage) return baseWidth + 0.02;
    const rect = stage.getBoundingClientRect();
    const shortSide = Math.min(rect.width, rect.height);
    // 约 2px 屏幕容差，按短边换算为 viewBox 单位
    const tolerance = shortSide > 0 ? 2 / shortSide : 0.02;
    return baseWidth + tolerance;
  }

  function renderDraftSvg() {
    if (!state.currentPoints.length) return "";
    const points = state.currentPoints.map((point) => point.join(",")).join(" ");
    const strokeWidth = isFunctionalZoning() ? ZONE_EDIT_WIDTH : 0.006;
    const zoneStyle = normalizeZoneStyle(state.zoneDraftStyle);
    const circles = state.currentPoints
      .map(([x, y], index) =>
        isFunctionalZoning()
          ? index === 0 && state.currentPoints.length >= 3
            ? renderCloseHandleSvg(x, y, zoneStyle.fill_color)
            : renderHandleSvg(x, y, "#111827", "none")
          : `<circle cx="${x}" cy="${y}" r="0.009" fill="#111827"></circle>`,
      )
      .join("");
    return `<polyline points="${points}" fill="none" stroke="#111827" stroke-width="${strokeWidth}" stroke-dasharray="0.014 0.012"></polyline>${circles}`;
  }

  function renderHandleSvg(x, y, fill, stroke) {
    const strokeAttr = stroke === "none" ? 'stroke="none"' : `stroke="${stroke}" stroke-width="${getHandleStrokeWidth()}"`;
    return `<ellipse cx="${x}" cy="${y}" rx="${getHandleRadiusX()}" ry="${getHandleRadiusY()}" fill="${fill}" ${strokeAttr}></ellipse>`;
  }

  function renderCloseHandleSvg(x, y, fill) {
    return `
      <ellipse
        class="zone-close-hit"
        data-close-zone="true"
        cx="${x}"
        cy="${y}"
        rx="${getHandleRadiusX(CLOSE_HANDLE_R_PX)}"
        ry="${getHandleRadiusY(CLOSE_HANDLE_R_PX)}"
        fill="transparent"
        pointer-events="all"
      ></ellipse>
      <ellipse
        class="zone-close-ring"
        data-close-zone="true"
        cx="${x}"
        cy="${y}"
        rx="${getHandleRadiusX()}"
        ry="${getHandleRadiusY()}"
        fill="${fill}"
        stroke="${darkenHex(fill, 0.35)}"
        stroke-width="${getHandleStrokeWidth()}"
        pointer-events="all"
      ></ellipse>
    `;
  }

  function getHandleRadiusX(radiusPx = HANDLE_BASE_R_PX) {
    const stage = $("#workbenchStage");
    const stageWidth = (stage && stage.getBoundingClientRect().width) || 1;
    return Number((radiusPx / stageWidth).toFixed(6));
  }

  function getHandleRadiusY(radiusPx = HANDLE_BASE_R_PX) {
    const stage = $("#workbenchStage");
    const stageHeight = (stage && stage.getBoundingClientRect().height) || 1;
    return Number((radiusPx / stageHeight).toFixed(6));
  }

  function getHandleStrokeWidth() {
    const stage = $("#workbenchStage");
    const stageWidth = (stage && stage.getBoundingClientRect().width) || 1;
    return Number((2 / stageWidth).toFixed(6));
  }

  function bindOverlaySelection(overlay) {
    overlay.querySelectorAll("[data-close-zone]").forEach((shape) => {
      shape.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        finishFunctionalZone();
      });
    });
    overlay.querySelectorAll("[data-object-id]:not(.zone-arc-handle)").forEach((shape) => {
      shape.addEventListener("click", (event) => {
        event.stopPropagation();
        selectObject(shape.dataset.objectId);
      });
    });
    // arc handle: pointerdown 设状态 + click/dblclick 拦截
    overlay.querySelectorAll(".zone-arc-handle").forEach((handle) => {
      handle.addEventListener("pointerdown", (event) => {
        event.stopPropagation();
        event.preventDefault();
        state.arcDrag = {
          objectId: handle.dataset.objectId,
          segIndex: Number(handle.dataset.segmentIndex),
          startX: event.clientX,
          startY: event.clientY,
          moved: false,
        };
      });
      handle.addEventListener("click", (event) => {
        event.stopPropagation();
        event.preventDefault();
      });
      handle.addEventListener("dblclick", (event) => {
        event.stopPropagation();
        const objectId = handle.dataset.objectId;
        const segIndex = Number(handle.dataset.segmentIndex);
        convertSegmentToLine(objectId, segIndex);
      });
    });
  }

  function clampUnit(p) {
    if (!p) return null;
    return [
      Number(Math.max(0, Math.min(1, p[0])).toFixed(6)),
      Number(Math.max(0, Math.min(1, p[1])).toFixed(6)),
    ];
  }


  function getSelectedObject() {
    return state.objects.find((obj) => obj.id === state.selectedId) || null;
  }

  function ensureSegments(obj) {
    if (obj.geometry.segments && obj.geometry.segments.length > 0) {
      return obj.geometry.segments;
    }
    // 不可变：只计算并返回全 line 的临时 segments，不写回 obj
    const coords = obj.geometry.coords;
    const segments = [];
    for (let i = 0; i < coords.length; i++) {
      segments.push({
        kind: "line",
        from: coords[i],
        to: coords[(i + 1) % coords.length],
      });
    }
    return segments;
  }

  function materializeQuadratic(objectId, segIndex, control) {
    const obj = state.objects.find((o) => o.id === objectId);
    if (!obj) return;
    // 若 obj 尚无 segments → 用 ensureSegments 实例化写入
    if (!obj.geometry.segments || obj.geometry.segments.length === 0) {
      obj.geometry.segments = ensureSegments(obj);
    }
    const seg = obj.geometry.segments[segIndex];
    if (!seg || seg.kind !== "line") return;
    seg.kind = "quadratic";
    seg.control = [Number(control[0].toFixed(6)), Number(control[1].toFixed(6))];
  }

  function convertSegmentToLine(objectId, segIndex) {
    const obj = state.objects.find((o) => o.id === objectId);
    if (!obj || !obj.geometry.segments) return;
    pushUndoSnapshot();
    const seg = obj.geometry.segments[segIndex];
    if (!seg || seg.kind !== "quadratic") return;
    seg.kind = "line";
    delete seg.control;
    // 若已无任何 quadratic → 回到 coords-only
    const hasQuadratic = obj.geometry.segments.some((s) => s.kind === "quadratic");
    if (!hasQuadratic) {
      delete obj.geometry.segments;
    }
    markDirty();
    renderCanvasLayers("convert-to-line");
    refreshLegendPreview();
  }


  function selectObject(id) {
    state.selectedId = id || "";
    state.currentPoints = [];
    renderCanvasLayers("select-object");
    renderObjectList();
    renderSpecificTools();
  }

  function darkenHex(color, amount) {
    if (!isHexColor(color)) return color;
    const next = [1, 3, 5]
      .map((start) => {
        const value = parseInt(color.slice(start, start + 2), 16);
        return Math.max(0, Math.round(value * (1 - amount)))
          .toString(16)
          .padStart(2, "0");
      })
      .join("");
    return `#${next}`.toUpperCase();
  }

  function renderSvgLabel(label, point, color) {
    if (!label || !point) return "";
    const x = Math.min(Math.max(point[0] + 0.012, 0.01), 0.82);
    const y = Math.min(Math.max(point[1] - 0.012, 0.035), 0.96);
    return `<text x="${x}" y="${y}" fill="${color}" font-size="0.025" font-weight="700">${escapeHtml(label)}</text>`;
  }

  function renderObjectList() {
    const list = $("#objectList");
    if (!list) return;
    if (!state.objects.length) {
      list.innerHTML = '<div class="control-empty">还没有语义对象。</div>';
      return;
    }
    if (isFunctionalZoning()) {
      list.innerHTML = state.objects.map(renderFunctionalZoneRow).join("");
      list.querySelectorAll("[data-object-id]").forEach((button) => {
        button.addEventListener("click", () => selectObject(button.dataset.objectId));
      });
      list.querySelectorAll("[data-delete-object]").forEach((button) => {
        button.addEventListener("click", (event) => {
          event.stopPropagation();
          state.selectedId = button.dataset.deleteObject;
          deleteSelected();
        });
      });
      return;
    }
    list.innerHTML = state.objects
      .map(
        (obj) => `
          <button class="object-row ${obj.id === state.selectedId ? "active" : ""}" data-object-id="${escapeHtml(obj.id)}">
            <b>${escapeHtml(obj.label || obj.id)}</b>
            <span>${escapeHtml(objectName(obj.type))} / ${escapeHtml(geometryName(obj.geometry.kind))}</span>
          </button>
        `,
      )
      .join("");
    list.querySelectorAll("[data-object-id]").forEach((button) => {
      button.addEventListener("click", () => {
        selectObject(button.dataset.objectId);
      });
    });
  }

  function renderFunctionalZoneRow(obj) {
    const style = normalizeZoneStyle(obj.style_hints);
    const fill = style.fill_enabled ? style.fill_color : "transparent";
    const borderColor = style.border_style === "none" ? "transparent" : style.fill_color;
    return `
      <button class="object-row zone-row ${obj.id === state.selectedId ? "active" : ""}" data-object-id="${escapeHtml(obj.id)}">
        <span class="zone-row-main">
          <i class="zone-row-swatch" style="--swatch:${escapeHtml(fill)};--swatch-border:${escapeHtml(borderColor)}"></i>
          <b>${escapeHtml(obj.label || obj.id)}</b>
        </span>
        <span>用户手绘 / 多边形</span>
        <span class="object-row-delete" data-delete-object="${escapeHtml(obj.id)}" role="button" aria-label="删除 ${escapeHtml(obj.label || obj.id)}">删除</span>
      </button>
    `;
  }

  function renderSvgDraft() {
    const preview = $("#svgDraftPreview");
    const status = $("#svgDraftStatus");
    const exportButton = $("#exportDrawing");
    if (!preview || !status || !exportButton) return;
    if (!state.svgExists || !state.svgUrl || !isEnabled()) {
      preview.hidden = true;
      preview.removeAttribute("data");
      status.textContent = isEnabled() ? "等待 agent 生成。" : "该图纸工作台待设计。";
      exportButton.disabled = true;
      return;
    }
    const url = `${state.svgUrl}&_=${Date.now()}`;
    preview.setAttribute("data", url);
    preview.hidden = false;
    status.textContent = "已加载 agent SVG 草稿。";
    exportButton.disabled = false;
  }

  function isEditableElement(element) {
    if (!element) return false;
    const tag = element.tagName;
    return tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT" || element.isContentEditable;
  }

  function workbenchIsActive() {
    if (!$("#drawingWorkbench")) return false;
    if (window.architectureUploader && window.architectureUploader.getPage) {
      return window.architectureUploader.getPage() === "workbench";
    }
    return new URLSearchParams(window.location.search).get("page") === "workbench";
  }

  function handleShortcuts(event) {
    if (!workbenchIsActive() || !isEnabled()) return;
    const modifier = event.ctrlKey || event.metaKey;
    const editable = isEditableElement(document.activeElement);
    if (modifier && event.key.toLowerCase() === "z" && !isEditableElement(document.activeElement)) {
      event.preventDefault();
      if (event.shiftKey) redoHistory();
      else undoHistory();
      return;
    }
    if (!modifier && event.key === "Enter" && !editable && isFunctionalZoning() && state.currentPoints.length >= 3) {
      event.preventDefault();
      finishFunctionalZone();
      return;
    }
    if (!modifier && (event.key === "Delete" || event.key === "Backspace") && !editable) {
      if (event.key === "Backspace") event.preventDefault();
      if (state.selectedId) {
        event.preventDefault();
        deleteSelected();
      }
      return;
    }
    if (!modifier && event.key === "Escape" && !editable) {
      if (state.currentPoints.length) {
        pushUndoSnapshot();
        state.currentPoints = [];
        state.selectedId = "";
        markDirty();
        renderCanvasLayers("escape-cancel-draft");
        renderObjectList();
        renderSpecificTools();
        setStatus("已取消未完成点位。");
      } else if (state.selectedId) {
        state.selectedId = "";
        renderCanvasLayers("escape-clear-selection");
        renderObjectList();
        renderSpecificTools();
        setStatus("已取消当前选择。");
      }
    }
  }

  function bind() {
    if (!$("#drawingWorkbench")) return;
    state.currentDrawingType = initialDrawingType();
    renderDrawingTabs();
    renderDrawingWorkspace();

    $("#workbenchLoad").addEventListener("click", () => loadDrawing().catch((err) => setStatus(err.message, false)));
    $("#workbenchSave").addEventListener("click", () => saveDrawing().catch((err) => setStatus(err.message, false)));
    $("#uploadBaseImage").addEventListener("click", () => uploadBaseImage().catch((err) => setStatus(err.message, false)));
    $("#sendToAgent").addEventListener("click", () => sendToAgent().catch((err) => setTaskStatus(err.message, false)));
    $("#exportDrawing").addEventListener("click", () => exportDrawing().catch((err) => setStatus(err.message, false)));
    $("#finishObject").addEventListener("click", finishObject);
    $("#undoPoint").addEventListener("click", undoPoint);
    $("#redoAction").addEventListener("click", redoHistory);
    $("#deleteObject").addEventListener("click", deleteSelected);
    $("#clearDraft").addEventListener("click", clearDraft);
    $("#canvasZoomOut").addEventListener("click", () => adjustCanvasZoom(-CANVAS_ZOOM_STEP));
    $("#canvasZoomReset").addEventListener("click", () => setCanvasZoom(1));
    $("#canvasZoomIn").addEventListener("click", () => adjustCanvasZoom(CANVAS_ZOOM_STEP));
    $("#canvasZoomFit").addEventListener("click", () => setCanvasZoom(1));
    $("#sketchOverlay").addEventListener("click", addPoint);
    $("#sketchOverlay").addEventListener("dblclick", (event) => {
      event.preventDefault();
      if (!isFunctionalZoning()) finishObject();
    });
    $("#workbenchCanvas").addEventListener("wheel", handleCanvasWheel, { passive: false });
    document.addEventListener("keydown", handleShortcuts);
    // arc drag: one-time document-level pointer handlers (survive re-render)
    document.addEventListener("pointermove", (event) => {
      if (!state.arcDrag) return;
      const stage = $("#workbenchStage");
      if (!stage) return;
      const rect = stage.getBoundingClientRect();
      const p = clampUnit(normalizedPoint(event));
      if (!p) return;
      const dx = (event.clientX - state.arcDrag.startX) / rect.width;
      const dy = (event.clientY - state.arcDrag.startY) / rect.height;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const shortSide = Math.min(rect.width, rect.height) || 1;
      const START_THRESHOLD = 3 / shortSide;
      if (!state.arcDrag.moved && dist < START_THRESHOLD) return;
      if (!state.arcDrag.moved) {
        state.arcDrag.moved = true;
        pushUndoSnapshot();
      }
      const obj = state.objects.find((o) => o.id === state.arcDrag.objectId);
      if (!obj) return;
      const seg = obj.geometry.segments
        ? obj.geometry.segments[state.arcDrag.segIndex]
        : null;
      if (!seg || seg.kind === "line") {
        materializeQuadratic(state.arcDrag.objectId, state.arcDrag.segIndex, p);
      } else {
        seg.control = [Number(p[0].toFixed(6)), Number(p[1].toFixed(6))];
      }
      markDirty();
      renderCanvasLayers("arc-drag");
    });
    document.addEventListener("pointerup", () => {
      if (!state.arcDrag) return;
      state.arcDrag = null;
      markDirty();
      refreshLegendPreview();
    });
    document.addEventListener("pointercancel", () => {
      state.arcDrag = null;
    });
    window.addEventListener("uploader:state", (event) => {
      const newProject = (event.detail && event.detail.project) || "";
      const newPage = event.detail && event.detail.page;
      const shouldReload =
        newPage === "workbench" && newProject && (newProject !== state.project || !state.drawing);
      state.project = newProject;
      if (shouldReload) {
        setCurrentDrawing(initialDrawingType(), { skipDirty: true }).catch((err) => setStatus(err.message, false));
      }
    });

    state.project = projectCode();
    if (
      state.project &&
      window.architectureUploader &&
      window.architectureUploader.getPage &&
      window.architectureUploader.getPage() === "workbench"
    ) {
      setCurrentDrawing(state.currentDrawingType, { skipDirty: true }).catch((err) => setStatus(err.message, false));
    }
  }

  bind();
})();
