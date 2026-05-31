(function () {
  const Model = window.DrawingWorkbenchModel;
  if (!Model) {
    throw new Error("DrawingWorkbenchModel must be loaded before workbench.js");
  }
  const DEFAULT_DRAWING_TYPE = "functional_zoning";
  const DRAWING_STATUS = new Set(["enabled", "planned", "deprecated"]);
  const DRAWING_CATEGORY = new Set(["analysis_a", "context_b", "other"]);
  const GEOMETRY_OPTIONS = [
    { value: "closed_path", label: "多边形" },
    { value: "open_path", label: "线段" },
    { value: "circle", label: "圆形" },
    { value: "triangle", label: "三角形" },
    { value: "text_label", label: "文字" },
  ];
  const GEOMETRY_LABELS = {
    path: "路径",
    circle: "圆形",
    triangle: "三角形",
    point: "点位",
    text: "文字",
    closed_path: "多边形",
    open_path: "线段",
  };
  const TOOL_GEOMETRY = {
    closed_path: { kind: "path", closed: true, minPoints: 3 },
    open_path: { kind: "path", closed: false, minPoints: 2 },
    turning_radius: { kind: "path", closed: false, minPoints: 2 },
    slope_arrow: { kind: "path", closed: false, minPoints: 2 },
    circle: { kind: "circle", minPoints: 1 },
    triangle: { kind: "triangle", minPoints: 1 },
    elevation_marker: { kind: "triangle", minPoints: 1 },
    text_label: { kind: "text", minPoints: 1 },
  };
  const SPECIAL_TOOL_TYPES = new Set(["turning_radius", "elevation_marker", "slope_arrow"]);
  const FLOW_ARROW_OBJECT_TYPES = new Set([
    "vehicle_flow",
    "pedestrian_flow",
    "underground_flow",
    "fire_route_line",
    "runoff_line",
  ]);
  const UNDO_LIMIT = 50;
  const PALETTE_FALLBACK = [
    "#D6CBB8",
    "#C2D0DB",
    "#E0D2C2",
    "#CFD4BF",
  ];
  const DEFAULT_ZONE_STYLE = {
    fill_mode: "translucent",
    fill_color: "#DCE8C8",
    fill_opacity: 0.42,
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
  const CANVAS_ZOOM_MAX = 8;
  const CANVAS_BUTTON_ZOOM_FACTOR = 1.25;
  const CANVAS_WHEEL_ZOOM_FACTOR = 1.1;

  // Registry-loaded data (populated from /api/drawing/registry)
  let DRAWING_WORKBENCHES = {};
  let REGISTRY_OBJECTS = {};
  let registryLoaded = false;
  let registryLoadError = null;

  // Minimal fallback so page doesn't crash if registry fails
  const FALLBACK_WORKBENCHES = {
    functional_zoning: {
      status: "enabled",
      category: "analysis_a",
      label: "功能分区",
      title: "功能分区工作台",
      description: "标注功能区边界、功能名称和必要标签。",
      fixedObjectType: "functional_zone",
      fixedGeometry: "closed_path",
      fixedSource: "user_sketch",
      hideCanvasLabels: true,
      paletteFallback: PALETTE_FALLBACK,
      objectTypes: [
        { value: "functional_zone", label: "功能区", defaultGeometry: "closed_path" },
      ],
      taskButtonLabel: "生成分区图任务包",
      agentNotesPlaceholder: "例如：请把不同功能区整理为低饱和分区色块，并生成底部图例。",
    },
  };

  // Tool label map for display
  const TOOL_LABELS = {
    closed_path: "多边形",
    open_path: "线段",
    circle: "圆形",
    triangle: "三角形",
    turning_radius: "转弯半径",
    elevation_marker: "标高点",
    slope_arrow: "坡度箭头",
    text_label: "文字",
    supporting_images: "配图",
  };
  const PRIMITIVE_STYLE_SPEC = {
    functional_zone: {
      color: true,
      fill: ["none", "translucent", "solid", "hatch"],
      border: ["none", "solid", "dashed", "double"],
      strokeWidth: true,
      legendName: true,
      maxStrokeWidth: 0.012,
    },
    closed_path: {
      color: true,
      fill: ["none", "translucent", "solid", "hatch"],
      border: ["none", "solid", "dashed", "double"],
      strokeWidth: true,
      legendName: true,
    },
    open_path: {
      color: true,
      fill: false,
      border: false,
      strokeStyle: ["solid", "dashed"],
      strokeWidth: true,
      arrows: "flow-only",
      legendName: true,
    },
    circle: {
      color: true,
      fill: ["none", "translucent", "solid"],
      border: ["none", "solid", "dashed", "double"],
      strokeWidth: true,
      radius: true,
      legendName: true,
    },
    triangle: {
      color: true,
      fill: ["none", "translucent", "solid"],
      border: ["none", "solid", "dashed"],
      strokeWidth: true,
      size: true,
      rotation: true,
      legendName: true,
    },
    turning_radius: {
      color: true,
      fill: false,
      border: false,
      strokeStyle: ["solid", "dashed"],
      strokeWidth: true,
      arrows: "flow-only",
      labelBox: true,
      legendName: true,
    },
    elevation_marker: {
      color: true,
      fill: ["none", "translucent", "solid"],
      border: ["none", "solid", "dashed"],
      strokeWidth: true,
      size: true,
      rotation: true,
      labelBox: true,
      legendName: true,
    },
    slope_arrow: {
      color: true,
      fill: false,
      border: false,
      strokeStyle: ["solid", "dashed"],
      strokeWidth: true,
      arrows: "flow-only",
      inlineText: true,
      legendName: true,
    },
    text_label: {
      color: true,
      textContent: true,
      fontSize: true,
    },
  };
  const FILL_LABELS = { none: "无", translucent: "半透明", solid: "实心", hatch: "斜线" };
  const BORDER_LABELS = { none: "无边框", solid: "实线", dashed: "虚线", double: "双实线" };
  const STROKE_STYLE_LABELS = { solid: "实线", dashed: "虚线" };

  const state = {
    project: "",
    drawing: null,
    currentDrawingType: DEFAULT_DRAWING_TYPE,
    objects: [],
    currentPoints: [],
    activeTool: "",
    activeObjectTypes: {},
    styleDrafts: {},
    geometryDrafts: {},
    labelDrafts: {},
    lastStyles: {},
    lastGeometry: {},
    supportingImages: {},
    supportingLoaded: {},
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
    vertexDrag: null,
    moveDrag: null,
    clipboard: null,
    stylePresets: [],
    stylePresetPath: "",
    stylePresetLoadError: "",
    deckLayout: null,
    deckLayoutPath: "",
    pptPreviewMode: false,
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

  // Load registry from backend API
  async function loadRegistry() {
    try {
      const data = await api("/api/drawing/registry");
      if (!data.ok || !data.drawings) {
        throw new Error("registry response invalid");
      }
      // Convert registry format to workbench config format
      const benches = {};
      for (const [dtId, dtInfo] of Object.entries(data.drawings)) {
        const objectTypes = (dtInfo.object_types || []).map(otId => {
          const otInfo = (data.objects || {})[otId] || {};
          const defaultGeometry = otInfo.geometry === "circle" ? "circle" :
                                  otInfo.geometry === "triangle" ? "triangle" :
                                  otInfo.geometry === "text" ? "text_label" :
                                  otInfo.closed === true ? "closed_path" : "open_path";
          return {
            value: otId,
            label: otInfo.label || otId,
            defaultGeometry,
            defaultTool: (dtInfo.tools || []).includes(otId) ? otId : defaultGeometry,
          };
        });
        benches[dtId] = {
          status: dtInfo.status,
          category: dtInfo.category,
          label: dtInfo.label,
          title: `${dtInfo.label}工作台`,
          description: `${dtInfo.label}语义标注工作台。`,
          objectTypes,
          tools: dtInfo.tools || [],
          taskButtonLabel: `生成${dtInfo.label}任务包`,
          agentNotesPlaceholder: `例如：请按照风格规范处理${dtInfo.label}。`,
        };
        // Keep functional_zoning special behavior
        if (dtId === "functional_zoning") {
          benches[dtId].fixedObjectType = "functional_zone";
          benches[dtId].fixedGeometry = "closed_path";
          benches[dtId].fixedSource = "user_sketch";
          benches[dtId].hideCanvasLabels = true;
          benches[dtId].paletteFallback = PALETTE_FALLBACK;
        }
      }
      DRAWING_WORKBENCHES = benches;
      REGISTRY_OBJECTS = data.objects || {};
      registryLoaded = true;
      registryLoadError = null;
    } catch (err) {
      console.error("[workbench] registry load failed, using fallback:", err);
      DRAWING_WORKBENCHES = { ...FALLBACK_WORKBENCHES };
      registryLoaded = false;
      registryLoadError = err.message;
    }
  }

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

  function isFunctionalZoneObject(type) {
    return type === "functional_zone";
  }

  function isEnabled(type = drawingType()) {
    return drawingConfig(type).status === "enabled";
  }

  function drawingTools(type = drawingType()) {
    return (drawingConfig(type).tools || []).filter((toolId) => toolId !== "supporting_images");
  }

  function supportsTool(toolId, type = drawingType()) {
    return (drawingConfig(type).tools || []).includes(toolId);
  }

  function normalizeActiveTool(type = drawingType()) {
    if (isFunctionalZoning(type)) return "closed_path";
    const tools = drawingConfig(type).tools || [];
    if (tools.includes(state.activeTool)) return state.activeTool;
    state.activeTool = drawingTools(type)[0] || tools[0] || "";
    return state.activeTool;
  }

  function toolObjectTypes(toolId = normalizeActiveTool()) {
    const objectTypes = drawingConfig().objectTypes || [];
    if (toolId === "supporting_images") return [];
    if (!toolId) return objectTypes;
    if (SPECIAL_TOOL_TYPES.has(toolId)) return objectTypes.filter((item) => item.value === toolId);
    return objectTypes.filter((item) => (item.defaultTool || item.defaultGeometry) === toolId);
  }

  function selectedToolObjectType(toolId = normalizeActiveTool()) {
    const types = toolObjectTypes(toolId);
    const saved = state.activeObjectTypes[drawingType()];
    if (types.some((item) => item.value === saved)) return saved;
    const current = $("#objectType") && $("#objectType").value;
    if (types.some((item) => item.value === current)) return current;
    return (types[0] && types[0].value) || "label";
  }

  function setActiveTool(toolId) {
    if (!supportsTool(toolId)) return;
    state.activeTool = toolId;
    state.currentPoints = [];
    renderSpecificTools();
    renderAvailability();
    renderCanvasLayers("set-active-tool");
  }

  function defaultObjectStyle(type) {
    return Model.defaultStyleForObjectType(type);
  }

  function objectStyleHints(type, overrides = {}) {
    return Model.normalizeStyleHints(overrides, type);
  }

  function objectStyleValue(style, key, fallback) {
    return style && style[key] !== undefined && style[key] !== null ? style[key] : fallback;
  }

  function dashScale(style) {
    const value = Number(style && style.dash_scale);
    if (!Number.isFinite(value)) return 1;
    return Math.min(2.5, Math.max(0.4, value));
  }

  function dashArray(style, dash = 0.014, gap = 0.01) {
    const scale = dashScale(style);
    return `${Number((dash * scale).toFixed(4))} ${Number((gap * scale).toFixed(4))}`;
  }

  function clampArrowSize(value) {
    return Math.min(0.06, Math.max(0.012, Number(value) || 0.024));
  }

  function computedArrowSize(style) {
    const explicit = Number(style && style.arrow_size);
    if (Number.isFinite(explicit) && explicit > 0) return clampArrowSize(explicit);
    const strokeWidth = Number(style && style.stroke_width);
    const base = (Number.isFinite(strokeWidth) && strokeWidth > 0 ? strokeWidth : 0.004) * 6;
    return clampArrowSize(base);
  }

  function legendDashArray(style, dash = 4, gap = 3) {
    const scale = dashScale(style);
    return `${Number((dash * scale).toFixed(2))} ${Number((gap * scale).toFixed(2))}`;
  }

  function draftKey(toolId, objectType) {
    return `${drawingType()}|${toolId || ""}|${objectType || ""}`;
  }

  function draftStyleFor(objectType, toolId = normalizeActiveTool()) {
    if (isFunctionalZoneObject(objectType)) {
      const selected = selectedObject();
      return normalizeZoneStyle(selected && selected.type === objectType ? selected.style_hints : state.zoneDraftStyle);
    }
    const key = draftKey(toolId, objectType);
    const selected = selectedObject();
    if (selected && selected.type === objectType) {
      return sanitizeArrowStyle(Model.normalizeStyleHints(selected.style_hints, objectType), toolId, objectType);
    }
    if (state.styleDrafts[key]) return sanitizeArrowStyle(state.styleDrafts[key], toolId, objectType);
    if (state.lastStyles[objectType]) return sanitizeArrowStyle(state.lastStyles[objectType], toolId, objectType);
    return sanitizeArrowStyle(Model.defaultStyleForObjectType(objectType), toolId, objectType);
  }

  function draftGeometryFor(objectType, toolId = normalizeActiveTool()) {
    const key = draftKey(toolId, objectType);
    const defaults = {
      radius: 0.035,
      size: 0.055,
      rotation_deg: toolId === "elevation_marker" || objectType === "elevation_marker" ? 180 : 0,
    };
    return {
      ...defaults,
      ...(state.lastGeometry[objectType] || {}),
      ...(state.geometryDrafts[key] || {}),
    };
  }

  function captureObjectDefaults(obj, toolId = normalizeActiveTool()) {
    if (!obj || !obj.type) return;
    if (isFunctionalZoneObject(obj.type)) {
      state.zoneDraftStyle = normalizeZoneStyle(obj.style_hints);
      return;
    }
    state.lastStyles[obj.type] = Model.cloneStyle(Model.normalizeStyleHints(obj.style_hints, obj.type));
    const geo = obj.geometry || {};
    const draft = {};
    if (geo.kind === "circle") draft.radius = Number(geo.radius) || 0.035;
    if (geo.kind === "triangle") {
      draft.size = Number(geo.size) || 0.055;
      draft.rotation_deg = Number(geo.rotation_deg) || 0;
    }
    if (Object.keys(draft).length) {
      state.lastGeometry[obj.type] = { ...(state.lastGeometry[obj.type] || {}), ...draft };
      state.geometryDrafts[draftKey(toolId, obj.type)] = { ...(state.geometryDrafts[draftKey(toolId, obj.type)] || {}), ...draft };
    }
  }

  function basePath() {
    const input = $("#baseImagePath");
    return (input && input.value.trim()) || "05_output/drawings/base/master_plan.jpg";
  }

  let statusToastTimer = null;
  function setStatus(message, ok = true) {
    const el = $("#workbenchStatus");
    if (!el) return;
    el.textContent = message;
    el.classList.toggle("error", !ok);
    el.classList.add("show");
    if (statusToastTimer) clearTimeout(statusToastTimer);
    statusToastTimer = setTimeout(() => el.classList.remove("show"), 2600);
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
      labelDrafts: JSON.parse(JSON.stringify(state.labelDrafts)),
    };
  }

  function restoreSnapshot(snapshot) {
    state.objects = JSON.parse(JSON.stringify(snapshot.objects || []));
    state.currentPoints = JSON.parse(JSON.stringify(snapshot.currentPoints || []));
    state.selectedId = snapshot.selectedId || "";
    state.zoneDraftStyle = normalizeZoneStyle(snapshot.zoneDraftStyle || state.zoneDraftStyle);
    state.zoneDraftLabel = snapshot.zoneDraftLabel || "";
    state.labelDrafts = JSON.parse(JSON.stringify(snapshot.labelDrafts || {}));
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
        const glyph = (config.label || key).trim().charAt(0) || "图";
        return `
          <button
            class="drawing-tab ${active ? "active" : ""} ${planned ? "planned" : "enabled"}"
            type="button"
            role="tab"
            aria-selected="${active ? "true" : "false"}"
            data-drawing-type="${escapeHtml(key)}"
          >
            ${escapeHtml(glyph)}
            <span class="wb3-tip">${escapeHtml(config.label)}${escapeHtml(suffix)}</span>
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
    renderPptControls();
    renderPptPreview();
  }

  function renderWorkspaceMeta() {
    const config = drawingConfig();
    const crumb = $("#wbCrumb");
    if (crumb) crumb.textContent = projectCode() || "未选择项目";
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
      let label = config.status === "enabled" ? (state.dirty ? "有未保存修改" : "可编辑") : "待设计";
      if (config.status === "enabled") {
        const approved = state.styleSpec && state.styleSpec.approved_at;
        label += approved ? " · 已批准风格" : " · 未建立风格";
      }
      stateEl.textContent = label;
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
    if (drawingType() === "functional_zoning") {
      const selected = selectedObject();
      const activeStyle = selected ? normalizeZoneStyle(selected.style_hints) : normalizeZoneStyle(state.zoneDraftStyle);
      const label = selected ? selected.label || "" : state.zoneDraftLabel || "";
      tools.innerHTML = `
        <label class="zone-name-field">
          <span>分区名称 <small>名称只进图例，不显示在图中</small></span>
          <input id="objectLabel" placeholder="如：中心广场 / 活动草坪" value="${escapeHtml(label)}">
        </label>
        ${renderStyleControls("functional_zone", activeStyle, {
          toolId: "closed_path",
          objectType: "functional_zone",
        })}
      `;
      const legendContainer = $("#zoneLegendPreview");
      if (legendContainer) {
        legendContainer.innerHTML = renderFunctionalZoneLegendPreview();
      }
      bindStyleControls("functional_zone", "functional_zone", { toolId: "closed_path", functional: true });
      return;
    }
    renderRegistryTools(tools, config);
  }

  function renderRegistryTools(tools, config) {
    const rawTools = config.tools || [];
    const activeTool = normalizeActiveTool();
    const objectTypes = toolObjectTypes(activeTool);
    const selectedObjectType = selectedToolObjectType(activeTool);
    const selected = selectedObject();
    const labelKey = draftKey(activeTool, selectedObjectType);
    const labelValue =
      selected && selected.type === selectedObjectType
        ? selected.label || ""
        : state.labelDrafts[labelKey] || "";
    const draftStyle = activeTool === "supporting_images" ? null : draftStyleFor(selectedObjectType, activeTool);
    const draftGeometry = activeTool === "supporting_images" ? null : draftGeometryFor(selectedObjectType, activeTool);
    tools.innerHTML = `
      <div class="zone-tool-group drawing-tool-picker" data-workbench-tool-picker="true">
        <span>绘图工具</span>
        <div class="segmented-control tool-grid">
          ${rawTools
            .map(
              (toolId) => `
                <button
                  type="button"
                  class="tool-button ${toolId === "text_label" ? "text-tool" : ""} ${activeTool === toolId ? "active" : ""}"
                  data-tool-id="${escapeHtml(toolId)}"
                >${toolButtonContent(toolId)}</button>
              `,
            )
            .join("")}
        </div>
      </div>
      ${
        activeTool === "supporting_images"
          ? '<div class="control-empty">配图工具仅管理参考图片，不在画布生成语义对象。</div>'
          : `
            <label>
              <span>对象类型</span>
              <select id="objectType">${optionHtml(objectTypes, selectedObjectType)}</select>
            </label>
            <label>
              <span>标签文本</span>
              <input id="objectLabel" placeholder="例如：主入口 / 景观节点 / R=9M" value="${escapeHtml(labelValue)}">
            </label>
            ${renderStyleControls(activeTool, draftStyle, {
              toolId: activeTool,
              objectType: selectedObjectType,
              geometry: draftGeometry,
            })}
          `
      }
      ${activeTool === "supporting_images" ? renderSupportingPanel() : ""}
    `;
    tools.querySelectorAll("[data-tool-id]").forEach((button) => {
      button.addEventListener("click", () => setActiveTool(button.dataset.toolId));
    });
    const objectType = $("#objectType");
    if (objectType) {
      objectType.addEventListener("change", () => {
        state.activeObjectTypes[drawingType()] = objectType.value;
        renderSpecificTools();
      });
    }
    if (activeTool !== "supporting_images") {
      bindStyleControls(activeTool, selectedObjectType, { toolId: activeTool });
    }
    bindSupportingPanel();
  }

  function toolButtonContent(toolId) {
    const label = escapeHtml(TOOL_LABELS[toolId] || toolId);
    if (toolId === "text_label") {
      return `<span class="tool-icon" aria-hidden="true">T</span><span>${label}</span>`;
    }
    return label;
  }

  function shouldShowArrowControls(toolId, objectType) {
    return canUseArrowStyle(toolId, objectType);
  }

  function shouldRenderArrowHeads(obj) {
    return obj && (obj.type === "turning_radius" || obj.type === "slope_arrow" || FLOW_ARROW_OBJECT_TYPES.has(obj.type));
  }

  function canUseArrowStyle(toolId, objectType) {
    return toolId === "turning_radius" || toolId === "slope_arrow" || FLOW_ARROW_OBJECT_TYPES.has(objectType);
  }

  function sanitizeArrowStyle(style, toolId, objectType) {
    const next = Model.cloneStyle(style || {});
    if (!canUseArrowStyle(toolId, objectType)) {
      next.start_arrow = false;
      next.end_arrow = false;
      next.arrow_size = null;
    }
    return next;
  }

  function currentToolSpec() {
    return TOOL_GEOMETRY[normalizeActiveTool()] || null;
  }

  function canFinishDraft() {
    const spec = currentToolSpec();
    return !!spec && state.currentPoints.length >= (spec.minPoints || 1);
  }

  function styleSpecFor(specKey) {
    return PRIMITIVE_STYLE_SPEC[specKey] || PRIMITIVE_STYLE_SPEC.closed_path;
  }

  function colorInputId(field) {
    return field === "fill_color" ? "styleFillColor" : "styleStrokeColor";
  }

  function renderColorControl(field, label, value) {
    const palette = zonePaletteItems();
    const recentColors = state.zoneRecentColors.filter(isHexColor);
    const active = normalizeHexColor(value) || "#333333";
    return `
      <div class="zone-tool-group">
        <span>${escapeHtml(label)}</span>
        <div class="zone-palette">
          ${palette
            .map(
              (item, index) => `
                <button
                  type="button"
                  class="zone-swatch ${item.color.toUpperCase() === active ? "active" : ""} ${
                    item.fallback ? "fallback" : ""
                  }"
                  style="--swatch:${escapeHtml(item.color)}"
                  title="${item.fallback ? "补足色，后续风格协商会替换" : "风格色"}"
                  aria-label="选择颜色 ${index + 1}"
                  data-style-color="${escapeHtml(field)}"
                  data-style-value="${escapeHtml(item.color)}"
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
                        class="zone-swatch zone-swatch-recent ${color === active ? "active" : ""}"
                        style="--swatch:${escapeHtml(color)}"
                        title="最近使用颜色"
                        aria-label="选择最近使用颜色 ${escapeHtml(color)}"
                        data-style-color="${escapeHtml(field)}"
                        data-style-value="${escapeHtml(color)}"
                      ></button>
                    `,
                  )
                  .join("")}
              </div>
            `
            : ""
        }
        <input
          id="${colorInputId(field)}"
          type="color"
          value="${escapeHtml(active)}"
          aria-label="${escapeHtml(label)}"
          data-style-color-input="${escapeHtml(field)}"
        >
      </div>
    `;
  }

  function segmentedStyleControl(label, field, options, selected) {
    return `
      <div class="zone-tool-group">
        <span>${escapeHtml(label)}</span>
        <div class="segmented-control">
          ${options
            .map(
              (item) => `
                <button
                  type="button"
                  class="${String(selected) === String(item.value) ? "active" : ""}"
                  data-style-segment="${escapeHtml(field)}"
                  data-style-value="${escapeHtml(item.value)}"
                >${escapeHtml(item.label)}</button>
              `,
            )
            .join("")}
        </div>
      </div>
    `;
  }

  function rangeControl(id, label, value, min, max, step, dataAttrs = "") {
    return `
      <div class="zone-tool-group">
        <span>${escapeHtml(label)}</span>
        <input id="${escapeHtml(id)}" type="range" min="${min}" max="${max}" step="${step}" value="${escapeHtml(String(value))}" ${dataAttrs}>
      </div>
    `;
  }

  function numberControl(id, label, value, min, max, step, dataAttrs = "") {
    return `
      <div class="zone-tool-group">
        <span>${escapeHtml(label)}</span>
        <input id="${escapeHtml(id)}" type="number" min="${min}" max="${max}" step="${step}" value="${escapeHtml(String(value))}" ${dataAttrs}>
      </div>
    `;
  }

  async function loadStylePresets() {
    try {
      const data = await api("/api/drawing/style-presets");
      state.stylePresets = Array.isArray(data.presets)
        ? data.presets.filter((item) => item && item.id && item.name && item.kind && item.hints)
        : [];
      state.stylePresetPath = data.path || "";
      state.stylePresetLoadError = "";
    } catch (err) {
      console.warn("[workbench] style preset load failed", err);
      state.stylePresets = [];
      state.stylePresetPath = "";
      state.stylePresetLoadError = err.message || "样式预设加载失败";
    }
  }

  async function saveStylePresetToLibrary(preset) {
    const data = await api("/api/drawing/style-presets/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ preset }),
    });
    state.stylePresets = Array.isArray(data.presets) ? data.presets : [];
    state.stylePresetPath = data.path || state.stylePresetPath;
    state.stylePresetLoadError = "";
  }

  async function deleteStylePresetFromLibrary(id) {
    const data = await api("/api/drawing/style-presets/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id }),
    });
    state.stylePresets = Array.isArray(data.presets) ? data.presets : [];
    state.stylePresetPath = data.path || state.stylePresetPath;
    state.stylePresetLoadError = "";
  }

  async function loadDeckLayout() {
    const project = projectCode();
    if (!project) {
      state.deckLayout = null;
      state.deckLayoutPath = "";
      renderPptControls();
      renderPptPreview();
      return null;
    }
    const params = new URLSearchParams({ project });
    const data = await api(`/api/drawing/deck-layout?${params}`);
    state.deckLayout = data.layout || null;
    state.deckLayoutPath = data.path || "";
    renderPptControls();
    renderPptPreview();
    return state.deckLayout;
  }

  async function saveDeckLayout(payload = {}) {
    const project = projectCode();
    if (!project) throw new Error("请先打开或创建项目。");
    const data = await api("/api/drawing/deck-layout/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project, ...payload }),
    });
    state.deckLayout = data.layout || null;
    state.deckLayoutPath = data.path || "";
    renderPptControls();
    renderPptPreview();
    return state.deckLayout;
  }

  async function reflowDeckLayout(scope = "current") {
    const project = projectCode();
    if (!project) throw new Error("请先打开或创建项目。");
    if (hasManualReflowTarget(scope) && !confirmManualReflow(scope)) {
      setPptStatus("已取消重新排版，保留本页手动调整。", true);
      return state.deckLayout;
    }
    const data = await api("/api/drawing/deck-layout/reflow", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        project,
        scope,
        drawing_type: drawingType(),
      }),
    });
    state.deckLayout = data.layout || null;
    state.deckLayoutPath = data.path || "";
    renderPptControls();
    renderPptPreview();
    return state.deckLayout;
  }

  function hasManualReflowTarget(scope = "current") {
    if (!state.deckLayout || !state.deckLayout.slides) return false;
    if (scope === "all") {
      return Object.values(state.deckLayout.slides).some((slide) => slide && slide.manual_overrides === true);
    }
    const slide = currentPptSlide();
    return !!(slide && slide.manual_overrides === true);
  }

  function confirmManualReflow(scope = "current") {
    const target = scope === "all" ? "全部图纸页中已有手动调整的页面" : "本页";
    return window.confirm(`重新排版会覆盖${target}手动调整。是否继续？`);
  }

  function currentPptSlide() {
    const slides = (state.deckLayout && state.deckLayout.slides) || {};
    return slides[drawingType()] || null;
  }

  function boxStyle(box) {
    const data = box || { x: 0, y: 0, w: 0, h: 0 };
    return `left:${Number(data.x || 0) * 100}%;top:${Number(data.y || 0) * 100}%;width:${Number(data.w || 0) * 100}%;height:${Number(data.h || 0) * 100}%;`;
  }

  function supportingImageById(id) {
    const images = state.supportingImages[drawingType()] || [];
    return images.find((image) => image.id === id) || null;
  }

  function setPptStatus(message, ok = true) {
    const el = $("#pptLayoutStatus");
    if (!el) return;
    el.textContent = message;
    el.style.color = ok ? "var(--muted3)" : "var(--accent-2)";
  }

  function renderPptControls() {
    const textarea = $("#pptSlideText");
    const slide = currentPptSlide();
    if (textarea && document.activeElement !== textarea) {
      textarea.value = slide ? slide.text || "" : "";
    }
    document.querySelectorAll("[data-ppt-template]").forEach((button) => {
      button.classList.toggle("active", !!state.deckLayout && button.dataset.pptTemplate === state.deckLayout.template_side);
    });
    const toggle = $("#togglePptPreview");
    if (toggle) {
      toggle.classList.toggle("primary", state.pptPreviewMode);
      toggle.setAttribute("aria-pressed", state.pptPreviewMode ? "true" : "false");
      toggle.textContent = state.pptPreviewMode ? "返回制图" : "PPT预览";
    }
    if (!state.deckLayout) {
      setPptStatus("尚未加载PPT预览。", false);
      return;
    }
    const frame = state.deckLayout.drawing_frame || {};
    const needs = slide && slide.needs_reflow;
    const side = state.deckLayout.template_side === "drawing_right" ? "信息左 / 图纸右" : "图纸左 / 信息右";
    setPptStatus(
      `${side}；图纸框 x=${Number(frame.x || 0).toFixed(2)} y=${Number(frame.y || 0).toFixed(2)} w=${Number(frame.w || 0).toFixed(2)} h=${Number(frame.h || 0).toFixed(2)}${needs ? "；本页需重新排版" : ""}`,
      !needs,
    );
  }

  function renderPptPreview() {
    const panel = $("#pptPreviewPanel");
    const canvas = $("#workbenchCanvas");
    const zoom = $(".wb3-zoom");
    const dock = $(".wb3-dock");
    const slideEl = $("#pptSlidePreview");
    if (!panel || !canvas || !slideEl) return;
    panel.hidden = !state.pptPreviewMode;
    canvas.hidden = state.pptPreviewMode;
    if (zoom) zoom.hidden = state.pptPreviewMode;
    if (dock) dock.hidden = state.pptPreviewMode;
    if (!state.pptPreviewMode) return;
    if (!state.deckLayout) {
      slideEl.innerHTML = '<div class="ppt-empty-note">请先打开项目并加载PPT预览。</div>';
      return;
    }
    const slide = currentPptSlide();
    const frame = state.deckLayout.drawing_frame || { x: 0.02, y: 0.17, w: 0.64, h: 0.72 };
    const elements = (slide && slide.elements) || {};
    const drawingSrc = state.svgExists && state.svgUrl ? `${state.svgUrl}&_=${Date.now()}` : state.loadedBaseUrl || "";
    const drawingMedia = drawingSrc
      ? `<img data-ppt-drawing-media="true" src="${escapeHtml(drawingSrc)}" alt="${escapeHtml(drawingConfig().label || "图纸")}">`
      : '<div class="ppt-empty-note">暂无图纸输出；将先使用底图或等待agent生成SVG。</div>';
    const legendHtml = isFunctionalZoning() ? renderFunctionalZoneLegendPreview() : renderGenericLegendPreview();
    const supportBoxes = Array.isArray(elements.supporting_images) ? elements.supporting_images : [];
    const warnings = Array.isArray(slide && slide.layout_warnings)
      ? slide.layout_warnings.filter(Boolean)
      : [];
    const warningHtml = warnings.length
      ? `<div class="ppt-warning-banner" data-ppt-layout-warning="true">排版提醒：${escapeHtml(warnings.join("；"))}</div>`
      : "";
    const supportHtml = supportBoxes
      .map((box) => {
        const image = supportingImageById(box.id);
        const src = image ? supportingImageUrl(image) : "";
        return `
          <div class="ppt-el ppt-supporting-img" style="${boxStyle(box)}">
            ${src ? `<img src="${escapeHtml(src)}" alt="${escapeHtml(image.caption || image.original_name || "配图")}">` : '<div class="ppt-empty-note">配图</div>'}
          </div>
        `;
      })
      .join("");
    slideEl.innerHTML = `
      ${slide && slide.needs_reflow ? '<div class="ppt-reflow-banner">本页排版需根据最新图纸框重新生成</div>' : ""}
      ${warningHtml}
      <div class="ppt-el ppt-drawing-frame" data-ppt-drawing-frame="true" style="${boxStyle(frame)}">
        ${drawingMedia}
        <span class="ppt-frame-label">全局图纸框</span>
      </div>
      <div class="ppt-el ppt-info-box ppt-legend-box" data-ppt-element="legend" style="${boxStyle(elements.legend)}">
        <h4>图例</h4>
        ${legendHtml}
      </div>
      <div class="ppt-el ppt-info-box" data-ppt-element="text" style="${boxStyle(elements.text)}">
        <h4>${escapeHtml((slide && slide.title) || drawingConfig().label || "图纸说明")}</h4>
        <p>${escapeHtml((slide && slide.text) || "暂无图纸说明。")}</p>
      </div>
      ${supportHtml}
    `;
  }

  function confirmPptGlobalChange() {
    return window.confirm("图纸位置和大小会应用到全部图纸页，并可能影响现有图例、文本、配图排版。是否继续？");
  }

  async function saveCurrentPptText() {
    const input = $("#pptSlideText");
    await saveDeckLayout({
      drawing_type: drawingType(),
      slide: { text: input ? input.value : "" },
    });
    setStatus("已保存PPT图纸说明。");
  }

  async function applyPptTemplate(templateSide) {
    if (!templateSide || !state.deckLayout || templateSide === state.deckLayout.template_side) return;
    if (!confirmPptGlobalChange()) {
      renderPptControls();
      return;
    }
    await saveDeckLayout({ template_side: templateSide });
    setStatus("已更新全局PPT版式，所有页面已标记为需重新排版。");
  }

  function presetMatchesContext(preset, specKey, context = {}) {
    if (!preset) return false;
    const kind = preset.kind || "";
    const toolId = context.toolId || specKey;
    const objectType = context.objectType || "";
    if (specKey === "functional_zone") return kind === "functional_zone" || kind === "all";
    if (!kind || kind === "all" || kind === specKey || kind === toolId || kind === objectType) return true;
    return false;
  }

  function presetGeometryFor(specKey, context = {}) {
    const toolId = context.toolId || specKey;
    const spec = TOOL_GEOMETRY[toolId] || TOOL_GEOMETRY[specKey] || {};
    return {
      kind: spec.kind || "path",
      closed: spec.closed === true,
    };
  }

  function renderStylePresetSwatch(preset, specKey, context) {
    const geometry = presetGeometryFor(specKey, context);
    const objectType = context.objectType || preset.objectType || preset.kind || specKey;
    const style = sanitizeArrowStyle(
      Model.normalizeStyleHints({ ...(preset.hints || {}) }, objectType),
      context.toolId || specKey,
      objectType,
    );
    return `
      <svg data-style-preset-swatch viewBox="0 0 24 16" aria-hidden="true">
        ${renderGenericLegendSwatch({
          type: objectType,
          style,
          geometry_kind: geometry.kind,
          geometry_closed: geometry.closed,
        })}
      </svg>
    `;
  }

  function allStylePresetsFor(specKey, context = {}) {
    return (state.stylePresets || [])
      .filter((preset) => presetMatchesContext(preset, specKey, context))
      .map((preset) => ({ ...preset, source: "repo" }));
  }

  function renderStylePresetControls(specKey, style, context = {}) {
    const presets = allStylePresetsFor(specKey, context);
    const loadError = state.stylePresetLoadError || "";
    return `
      <div class="style-section-title">预设</div>
      <div class="zone-tool-group style-presets" data-style-presets="true">
        <div class="style-preset-list">
          ${
            loadError
              ? `<span class="control-empty">预设加载失败：${escapeHtml(loadError)}</span>`
              : presets.length
              ? presets
                  .map(
                    (preset) => `
                      <div class="style-preset-row">
                        <button
                          type="button"
                          class="style-preset-apply"
                          data-style-preset-apply="${escapeHtml(preset.id)}"
                          data-preset-source="${escapeHtml(preset.source)}"
                          data-preset-name="${escapeHtml(preset.name)}"
                        >
                          ${renderStylePresetSwatch(preset, specKey, context)}
                          <span>${escapeHtml(preset.name)}</span>
                        </button>
                        <button type="button" class="style-preset-delete" data-style-preset-delete="${escapeHtml(preset.id)}" aria-label="删除 ${escapeHtml(preset.name)}">删除</button>
                      </div>
                    `,
                  )
                  .join("")
              : '<span class="control-empty">暂无可用预设</span>'
          }
        </div>
        <div class="style-preset-save">
          <input id="stylePresetName" placeholder="另存当前样式">
          <button type="button" id="saveStylePreset">保存</button>
        </div>
      </div>
    `;
  }

  function renderStyleControls(specKey, rawStyle = {}, context = {}) {
    const spec = styleSpecFor(specKey);
    const style =
      specKey === "functional_zone"
        ? normalizeZoneStyle(rawStyle)
        : Model.normalizeStyleHints(rawStyle || {}, context.objectType || specKey);
    const geo = context.geometry || {};
    const showArrows = spec.arrows === "flow-only" && shouldShowArrowControls(context.toolId || specKey, context.objectType);
    const showStrokeSection = spec.strokeWidth || spec.strokeStyle || spec.border || showArrows;
    const showDashScale =
      (spec.strokeStyle && style.stroke_style === "dashed") || (spec.border && style.border_style === "dashed");
    const strokeLabel = spec.fill ? "边框宽" : "线宽";
    const strokeMax = spec.maxStrokeWidth || 0.018;
    return `
      <div class="style-controls" data-style-controls="true">
        ${renderStylePresetControls(specKey, style, context)}
        ${
          spec.textContent
            ? `
              <div class="style-section-title">文字</div>
              <label><span>文字内容</span><input id="textLabelContent" value="${escapeHtml(style.text_content || "文字")}" data-style-input="text_content" data-style-kind="string"></label>
              ${rangeControl(
                "textLabelFontSize",
                "字号",
                style.font_size || 0.024,
                "0.012",
                "0.06",
                "0.002",
                'data-style-input="font_size" data-style-kind="number"',
              )}
              ${renderColorControl("stroke_color", "文字颜色", style.stroke_color || "#333333")}
            `
            : ""
        }
        ${
          spec.fill
            ? `
              <div class="style-section-title">填充</div>
              ${segmentedStyleControl(
                "填充模式",
                "fill_mode",
                spec.fill.map((value) => ({ value, label: FILL_LABELS[value] || value })),
                style.fill_mode || "none",
              )}
              ${renderColorControl("fill_color", "填充色", style.fill_color || "#DCE8C8")}
              ${
                style.fill_mode === "translucent"
                  ? `
                    <details class="style-advanced">
                      <summary>透明度</summary>
                      ${rangeControl(
                        "styleFillOpacity",
                        "不透明度",
                        style.fill_opacity ?? 0.42,
                        "0.12",
                        "1",
                        "0.02",
                        'data-style-input="fill_opacity" data-style-kind="number"',
                      )}
                    </details>
                  `
                  : ""
              }
              ${
                style.fill_mode === "hatch"
                  ? `
                    <details class="style-advanced" open>
                      <summary>斜线参数</summary>
                      ${numberControl(
                        "styleHatchAngle",
                        "角度",
                        style.hatch_angle_deg || 45,
                        "0",
                        "180",
                        "5",
                        'data-style-input="hatch_angle_deg" data-style-kind="number"',
                      )}
                      ${numberControl(
                        "styleHatchSpacing",
                        "间距",
                        style.hatch_spacing || 0.018,
                        "0.006",
                        "0.06",
                        "0.002",
                        'data-style-input="hatch_spacing" data-style-kind="number"',
                      )}
                    </details>
                  `
                  : ""
              }
            `
            : ""
        }
        ${
          showStrokeSection
            ? `
              <div class="style-section-title">描边</div>
              ${renderColorControl("stroke_color", spec.fill ? "边框色" : "线色", style.stroke_color || style.fill_color || "#333333")}
              ${
                spec.strokeWidth
                  ? rangeControl(
                      "styleStrokeWidth",
                      strokeLabel,
                      style.stroke_width || 0.003,
                      "0.001",
                      String(strokeMax),
                      "0.0005",
                      'data-style-input="stroke_width" data-style-kind="number"',
                    )
                  : ""
              }
              ${
                spec.strokeStyle
                  ? segmentedStyleControl(
                      "线型",
                      "stroke_style",
                      spec.strokeStyle.map((value) => ({ value, label: STROKE_STYLE_LABELS[value] || value })),
                      style.stroke_style || "solid",
                    )
                  : ""
              }
              ${
                showDashScale
                  ? rangeControl(
                      "styleDashScale",
                      "虚线密度",
                      dashScale(style),
                      "0.4",
                      "2.5",
                      "0.1",
                      'data-style-input="dash_scale" data-style-kind="number"',
                    )
                  : ""
              }
              ${
                spec.border
                  ? segmentedStyleControl(
                      "边框",
                      "border_style",
                      spec.border.map((value) => ({ value, label: BORDER_LABELS[value] || value })),
                      style.border_style || "solid",
                    )
                  : ""
              }
              ${
                spec.border && style.border_style === "double"
                  ? `
                    <details class="style-advanced" open>
                      <summary>双线参数</summary>
                      ${numberControl(
                        "styleDoubleGap",
                        "间距",
                        style.double_border_gap || 0.006,
                        "0.002",
                        "0.03",
                        "0.001",
                        'data-style-input="double_border_gap" data-style-kind="number"',
                      )}
                    </details>
                  `
                  : ""
              }
              ${
                showArrows
                  ? `
                    <div class="zone-tool-group arrow-controls">
                      <span>箭头</span>
                      <label class="checkbox-line"><input id="styleStartArrow" type="checkbox" data-style-input="start_arrow" data-style-kind="boolean" ${style.start_arrow ? "checked" : ""}> 起点</label>
                      <label class="checkbox-line"><input id="styleEndArrow" type="checkbox" data-style-input="end_arrow" data-style-kind="boolean" ${style.end_arrow ? "checked" : ""}> 终点</label>
                      <details class="style-advanced">
                        <summary>箭头尺寸</summary>
                        ${rangeControl(
                          "styleArrowSize",
                          "尺寸（随线宽，可覆盖）",
                          computedArrowSize(style),
                          "0.012",
                          "0.07",
                          "0.002",
                          'data-style-input="arrow_size" data-style-kind="number"',
                        )}
                      </details>
                    </div>
                  `
                  : ""
              }
            `
            : ""
        }
        ${
          spec.radius
            ? `
              <div class="style-section-title">标记</div>
              ${rangeControl(
                "geometryRadius",
                "圆半径",
                geo.radius || 0.035,
                "0.012",
                "0.12",
                "0.002",
                'data-geometry-input="radius" data-style-kind="number"',
              )}
            `
            : ""
        }
        ${
          spec.size || spec.rotation
            ? `
              <div class="style-section-title">标记</div>
              ${
                spec.size
                  ? rangeControl(
                      "geometrySize",
                      "三角尺寸",
                      geo.size || 0.055,
                      "0.025",
                      "0.13",
                      "0.002",
                      'data-geometry-input="size" data-style-kind="number"',
                    )
                  : ""
              }
              ${
                spec.rotation
                  ? rangeControl(
                      "geometryRotation",
                      "旋转角度",
                      geo.rotation_deg || 0,
                      "0",
                      "360",
                      "5",
                      'data-geometry-input="rotation_deg" data-style-kind="number"',
                    )
                  : ""
              }
            `
            : ""
        }
        ${
          spec.labelBox
            ? `
              <div class="style-section-title">标注</div>
              <label><span>标注文本</span><input id="labelBoxText" value="${escapeHtml((style.label_box && style.label_box.text) || (specKey === "turning_radius" ? "R=9M" : ""))}" data-style-nested="label_box.text" data-style-kind="string"></label>
              <details class="style-advanced">
                <summary>标注框参数</summary>
                ${rangeControl("labelBoxWidth", "宽", (style.label_box && style.label_box.width) || 0.09, "0.05", "0.22", "0.005", 'data-style-nested="label_box.width" data-style-kind="number"')}
                ${rangeControl("labelBoxHeight", "高", (style.label_box && style.label_box.height) || 0.035, "0.025", "0.09", "0.005", 'data-style-nested="label_box.height" data-style-kind="number"')}
                ${rangeControl("labelBoxFontSize", "字号", (style.label_box && style.label_box.font_size) || 0.018, "0.012", "0.04", "0.002", 'data-style-nested="label_box.font_size" data-style-kind="number"')}
                ${rangeControl("labelBoxOpacity", "透明度", (style.label_box && style.label_box.opacity) ?? 0.55, "0.2", "0.9", "0.02", 'data-style-nested="label_box.opacity" data-style-kind="number"')}
              </details>
            `
            : ""
        }
        ${
          spec.inlineText
            ? `
              <div class="style-section-title">标注</div>
              <label><span>坡度文本</span><input id="inlineText" value="${escapeHtml((style.inline_text && style.inline_text.text) || "0.3%")}" data-style-nested="inline_text.text" data-style-kind="string"></label>
              <details class="style-advanced">
                <summary>文字参数</summary>
                ${rangeControl("inlineTextFontSize", "字号", (style.inline_text && style.inline_text.font_size) || 0.018, "0.012", "0.04", "0.002", 'data-style-nested="inline_text.font_size" data-style-kind="number"')}
                ${rangeControl("inlineTextPosition", "位置", (style.inline_text && style.inline_text.position) || 0.5, "0.15", "0.85", "0.05", 'data-style-nested="inline_text.position" data-style-kind="number"')}
              </details>
            `
            : ""
        }
      </div>
    `;
  }

  function bindStyleControls(specKey, objectType, context = {}) {
    const toolId = context.toolId || specKey;
    const isFunctional = specKey === "functional_zone" || context.functional;
    const labelInput = $("#objectLabel");
    if (labelInput) {
      labelInput.addEventListener("input", () => {
        const selected = selectedObject();
        if (isFunctional) {
          if (!selected) state.zoneDraftLabel = labelInput.value;
          return;
        }
        if (selected && selected.type === objectType) {
          selected.label = labelInput.value;
          markDirty();
          renderObjectList();
          refreshLegendPreview();
        } else {
          state.labelDrafts[draftKey(toolId, objectType)] = labelInput.value;
        }
      });
      labelInput.addEventListener("change", () => {
        const selected = selectedObject();
        if (!selected || (!isFunctional && selected.type !== objectType)) {
          if (isFunctional) state.zoneDraftLabel = labelInput.value.trim();
          else state.labelDrafts[draftKey(toolId, objectType)] = labelInput.value.trim();
          return;
        }
        const next = labelInput.value.trim();
        if ((selected.label || "") === next) return;
        pushUndoSnapshot();
        selected.label = next;
        markDirty();
        renderObjectList();
        refreshLegendPreview();
        setStatus(isFunctional ? "已更新分区名称。" : "已更新对象标签。");
      });
    }
    document.querySelectorAll("[data-style-preset-apply]").forEach((button) => {
      button.addEventListener("click", () => {
        const preset = allStylePresetsFor(specKey, { ...context, objectType, toolId }).find(
          (item) => item.id === button.dataset.stylePresetApply,
        );
        if (!preset) return;
        updateStyle(specKey, { ...(preset.hints || {}) }, { toolId, objectType, functional: isFunctional });
        renderSpecificTools();
        setStatus(`已套用预设：${preset.name}`);
      });
    });
    document.querySelectorAll("[data-style-preset-delete]").forEach((button) => {
      button.addEventListener("click", async () => {
        const id = button.dataset.stylePresetDelete;
        if (!id) return;
        try {
          await deleteStylePresetFromLibrary(id);
          renderSpecificTools();
          setStatus("已删除样式预设。");
        } catch (err) {
          setStatus(err.message || "删除样式预设失败。", false);
        }
      });
    });
    const savePresetButton = $("#saveStylePreset");
    if (savePresetButton) {
      savePresetButton.addEventListener("click", async () => {
        const input = $("#stylePresetName");
        const name = ((input && input.value) || "").trim();
        if (!name) {
          setStatus("请先输入预设名称。", false);
          return;
        }
        const current = currentStyleFor(specKey, { toolId, objectType, functional: isFunctional });
        const preset = {
          id: `repo-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 7)}`,
          name,
          kind: objectType || toolId || specKey,
          toolId,
          objectType,
          hints: Model.cloneStyle(current),
          created_at: new Date().toISOString(),
        };
        try {
          await saveStylePresetToLibrary(preset);
          renderSpecificTools();
          setStatus(`已保存预设到 ${state.stylePresetPath || "JSON"}：${name}`);
        } catch (err) {
          setStatus(err.message || "保存样式预设失败。", false);
        }
      });
    }
    document.querySelectorAll("[data-style-segment]").forEach((button) => {
      button.addEventListener("click", () => {
        const key = button.dataset.styleSegment;
        const value = button.dataset.styleValue;
        if (!key) return;
        updateStyle(specKey, { [key]: value }, { toolId, objectType, functional: isFunctional });
        renderSpecificTools();
      });
    });
    document.querySelectorAll("[data-style-color]").forEach((button) => {
      button.addEventListener("click", () => {
        const key = button.dataset.styleColor;
        const value = button.dataset.styleValue;
        if (!key || !value) return;
        updateStyle(specKey, { [key]: value }, { toolId, objectType, functional: isFunctional });
        renderSpecificTools();
      });
    });
    document.querySelectorAll("[data-style-color-input]").forEach((input) => {
      input.addEventListener("change", () => {
        const key = input.dataset.styleColorInput;
        if (!key) return;
        updateStyle(specKey, { [key]: input.value }, { toolId, objectType, functional: isFunctional });
        renderSpecificTools();
      });
    });
    document.querySelectorAll("[data-style-input]").forEach((input) => {
      input.addEventListener("input", () => {
        const key = input.dataset.styleInput;
        if (!key) return;
        const kind = input.dataset.styleKind || "string";
        const value = kind === "boolean" ? input.checked : kind === "number" ? Number(input.value) : input.value;
        updateStyle(specKey, { [key]: value }, { toolId, objectType, functional: isFunctional }, { renderTools: false });
      });
    });
    document.querySelectorAll("[data-style-nested]").forEach((input) => {
      input.addEventListener("input", () => {
        const path = input.dataset.styleNested || "";
        const [group, key] = path.split(".");
        if (!group || !key) return;
        const kind = input.dataset.styleKind || "string";
        const value = kind === "number" ? Number(input.value) : input.value;
        const current = currentStyleFor(specKey, { toolId, objectType, functional: isFunctional });
        updateStyle(
          specKey,
          { [group]: { ...(current[group] || {}), enabled: true, [key]: value } },
          { toolId, objectType, functional: isFunctional },
          { renderTools: false },
        );
      });
    });
    document.querySelectorAll("[data-geometry-input]").forEach((input) => {
      input.addEventListener("input", () => {
        const key = input.dataset.geometryInput;
        if (!key) return;
        updateActiveGeometry(toolId, objectType, { [key]: Number(input.value) });
      });
    });
  }

  function currentStyleFor(specKey, context = {}) {
    if (specKey === "functional_zone" || context.functional) {
      const selected = selectedObject();
      return selected ? normalizeZoneStyle(selected.style_hints) : normalizeZoneStyle(state.zoneDraftStyle);
    }
    return draftStyleFor(context.objectType, context.toolId || specKey);
  }

  function updateStyle(specKey, patch, context = {}, options = {}) {
    if (specKey === "functional_zone" || context.functional) {
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
      if (Object.prototype.hasOwnProperty.call(patch, "stroke_color")) addRecentColor(next.stroke_color);
      markDirty();
      renderCanvasLayers("style-control");
      renderObjectList();
      if (options.renderTools !== false) renderSpecificTools();
      refreshLegendPreview();
      return;
    }
    updateActiveStyle(context.toolId || specKey, context.objectType || selectedToolObjectType(context.toolId || specKey), patch);
    if (Object.prototype.hasOwnProperty.call(patch, "fill_color")) addRecentColor(patch.fill_color);
    if (Object.prototype.hasOwnProperty.call(patch, "stroke_color")) addRecentColor(patch.stroke_color);
    if (options.renderTools !== false) renderSpecificTools();
  }

  function updateActiveStyle(toolId, objectType, patch) {
    const key = draftKey(toolId, objectType);
    const current = draftStyleFor(objectType, toolId);
    const next = sanitizeArrowStyle(Model.normalizeStyleHints({ ...current, ...patch }, objectType), toolId, objectType);
    state.styleDrafts[key] = Model.cloneStyle(next);
    state.lastStyles[objectType] = Model.cloneStyle(next);
    const selected = selectedObject();
    if (selected && selected.type === objectType && !isFunctionalZoneObject(objectType)) {
      selected.style_hints = Model.cloneStyle(next);
      markDirty();
      renderCanvasLayers("style-control");
      renderObjectList();
      refreshLegendPreview();
    }
  }

  function updateActiveGeometry(toolId, objectType, patch) {
    const key = draftKey(toolId, objectType);
    state.geometryDrafts[key] = { ...draftGeometryFor(objectType, toolId), ...patch };
    state.lastGeometry[objectType] = { ...(state.lastGeometry[objectType] || {}), ...patch };
    const selected = selectedObject();
    if (!selected || selected.type !== objectType || isFunctionalZoneObject(objectType)) return;
    const geo = selected.geometry || {};
    if (geo.kind === "circle" && patch.radius !== undefined) geo.radius = Number(patch.radius);
    if (geo.kind === "triangle") {
      if (patch.size !== undefined) geo.size = Number(patch.size);
      if (patch.rotation_deg !== undefined) geo.rotation_deg = Number(patch.rotation_deg);
    }
    selected.geometry = geo;
    markDirty();
    renderCanvasLayers("geometry-control");
    renderObjectList();
  }

  function renderSupportingPanel() {
    const images = state.supportingImages[drawingType()] || [];
    return `
      <div class="supporting-panel" data-supporting-panel="true">
        <div class="supporting-title">配图</div>
        <label><span>上传配图</span><input id="supportingImageFile" type="file" accept=".jpg,.jpeg,.png,.webp"></label>
        <label><span>标题</span><input id="supportingCaption" placeholder="可选"></label>
        <label><span>备注</span><input id="supportingNotes" placeholder="可选"></label>
        <label><span>排序</span><input id="supportingOrder" type="number" min="1" step="1" value="${images.length + 1}"></label>
        <button class="wb3-btn" id="supportingUpload" type="button">上传配图</button>
        <div class="supporting-list">
          ${
            images.length
              ? images
                  .slice()
                  .sort((a, b) => (Number(a.sort_order) || 0) - (Number(b.sort_order) || 0))
                  .map(renderSupportingImageRow)
                  .join("")
              : '<div class="control-empty">暂无配图。</div>'
          }
        </div>
      </div>
    `;
  }

  function supportingImageUrl(image) {
    const project = projectCode();
    if (!project || !image || !image.file) return "";
    const params = new URLSearchParams({ project, path: image.file });
    return `/api/project-file?${params}`;
  }

  function renderSupportingImageRow(image) {
    return `
      <div class="supporting-row" data-supporting-id="${escapeHtml(image.id || "")}">
        <img src="${escapeHtml(supportingImageUrl(image))}" alt="">
        <div>
          <b>${escapeHtml(image.caption || image.original_name || image.id || "配图")}</b>
          <small>${escapeHtml(image.notes || image.file || "")}</small>
        </div>
        <button type="button" data-delete-supporting="${escapeHtml(image.id || "")}">删除</button>
      </div>
    `;
  }

  function bindSupportingPanel() {
    const upload = $("#supportingUpload");
    if (upload) upload.addEventListener("click", () => uploadSupportingImage().catch((err) => setStatus(err.message, false)));
    document.querySelectorAll("[data-delete-supporting]").forEach((button) => {
      button.addEventListener("click", () =>
        deleteSupportingImage(button.dataset.deleteSupporting).catch((err) => setStatus(err.message, false)),
      );
    });
  }

  function buildFunctionalZoneLegendGroups(objects) {
    const groups = new Map();
    let invisibleCount = 0;
    objects.forEach((obj) => {
      if (obj.type !== "functional_zone") return;
      const style = normalizeZoneStyle(obj.style_hints);
      const fillVisible = style.fill_mode !== "none";
      const isInvisible = !fillVisible && style.border_style === "none";
      if (isInvisible) {
        invisibleCount++;
        return;
      }
      // 按可见性归一 key
      const key = JSON.stringify({
        fill: fillVisible ? style.fill_color : null,
        fill_mode: style.fill_mode,
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
      const fillVisible = style.fill_mode !== "none";
      const hasBorder = style.border_style !== "none";
      const borderColor = hasBorder ? style.stroke_color || style.fill_color : "transparent";
      // swatch viewBox 24x16，映射 stroke_width 到 1-3px 范围以区分线宽差异
      const borderWidth = hasBorder ? Math.max(1, Math.min(3, Math.round(style.stroke_width * 300))) : 0;
      const dashArrayValue = style.border_style === "dashed" ? legendDashArray(style) : "";
      return `
        <div class="zone-legend-item">
          <svg class="zone-legend-swatch" viewBox="0 0 24 16" aria-hidden="true">
            <rect x="1" y="1" width="22" height="14" rx="2"
              fill="${fillVisible ? style.fill_color : 'none'}"
              fill-opacity="${fillVisible ? String(style.fill_opacity ?? 0.42) : '0'}"
              stroke="${borderColor}"
              stroke-width="${borderWidth}"
              ${dashArrayValue ? `stroke-dasharray="${dashArrayValue}"` : ''}
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

  function normalizedGenericLegendObjects() {
    return state.objects
      .filter((obj) => obj.type !== "functional_zone")
      .map((obj) => ({
        ...obj,
        style_hints: sanitizeArrowStyle(
          Model.normalizeStyleHints(obj.style_hints || {}, obj.type),
          obj.type,
          obj.type,
        ),
      }))
      .filter((obj) => {
        const style = obj.style_hints || {};
        if (style.legend_enabled === false) return false;
        const geo = obj.geometry || {};
        if (geo.kind === "text") return !!(style.text_content || obj.label || "").trim();
        if (geo.kind === "circle" || geo.kind === "triangle") {
          const hasFill = style.fill_mode === "solid" || style.fill_mode === "translucent";
          const hasBorder = style.border_style !== "none";
          return hasFill || hasBorder;
        }
        if (geo.kind === "path" && geo.closed) {
          return style.fill_mode !== "none" || style.border_style !== "none";
        }
        return Number(style.stroke_width) > 0;
      });
  }

  function renderGenericLegendSwatch(group) {
    const style = group.style || {};
    const meta = REGISTRY_OBJECTS[group.type] || {};
    const kind = group.geometry_kind || meta.geometry || "path";
    const closed =
      Object.prototype.hasOwnProperty.call(group, "geometry_closed")
        ? group.geometry_closed === true
        : meta.closed === true;
    const stroke = style.stroke_color || style.fill_color || "#333333";
    const strokeWidth = Math.max(1, Math.min(4, Math.round((Number(style.stroke_width) || 0.003) * 320)));
    const dashArrayValue = style.stroke_style === "dashed" || style.border_style === "dashed" ? legendDashArray(style) : "";
    if (group.type === "elevation_marker") {
      const fillVisible = style.fill_mode === "solid" || style.fill_mode === "translucent";
      return `
        <polygon points="4,2 20,2 12,13"
          fill="${fillVisible ? style.fill_color || "none" : "none"}"
          fill-opacity="${style.fill_mode === "translucent" ? String(style.fill_opacity ?? 0.42) : fillVisible ? "1" : "0"}"
          stroke="${style.border_style === "none" ? "transparent" : stroke}"
          stroke-width="${style.border_style === "none" ? 0 : strokeWidth}"
          ${dashArrayValue ? `stroke-dasharray="${dashArrayValue}"` : ""}
        />
        <rect x="14" y="1" width="9" height="5" rx="0" fill="#FFFFFF" fill-opacity="${(style.label_box && style.label_box.opacity) ?? 0.55}" />`;
    }
    if (kind === "circle") {
      const fillVisible = style.fill_mode === "solid" || style.fill_mode === "translucent";
      return `
        <circle cx="12" cy="8" r="5.5"
          fill="${fillVisible ? style.fill_color || "none" : "none"}"
          fill-opacity="${style.fill_mode === "translucent" ? String(style.fill_opacity ?? 0.42) : fillVisible ? "1" : "0"}"
          stroke="${style.border_style === "none" ? "transparent" : stroke}"
          stroke-width="${style.border_style === "none" ? 0 : strokeWidth}"
          ${dashArrayValue ? `stroke-dasharray="${dashArrayValue}"` : ""}
        />`;
    }
    if (kind === "triangle") {
      const fillVisible = style.fill_mode === "solid" || style.fill_mode === "translucent";
      return `
        <polygon points="12,2 20,14 4,14"
          fill="${fillVisible ? style.fill_color || "none" : "none"}"
          fill-opacity="${style.fill_mode === "translucent" ? String(style.fill_opacity ?? 0.42) : fillVisible ? "1" : "0"}"
          stroke="${style.border_style === "none" ? "transparent" : stroke}"
          stroke-width="${style.border_style === "none" ? 0 : strokeWidth}"
          ${dashArrayValue ? `stroke-dasharray="${dashArrayValue}"` : ""}
        />`;
    }
    if (kind === "text") {
      return `<text x="12" y="11" text-anchor="middle" fill="${stroke}" font-size="11" font-weight="700">T</text>`;
    }
    if (closed) {
      const fillVisible = style.fill_mode === "solid" || style.fill_mode === "translucent" || style.fill_mode === "hatch";
      return `
        <rect x="1" y="1" width="22" height="14" rx="2"
          fill="${fillVisible ? style.fill_color || "none" : "none"}"
          fill-opacity="${style.fill_mode === "translucent" ? String(style.fill_opacity ?? 0.42) : fillVisible ? "1" : "0"}"
          stroke="${style.border_style === "none" ? "transparent" : stroke}"
          stroke-width="${style.border_style === "none" ? 0 : strokeWidth}"
          ${dashArrayValue ? `stroke-dasharray="${dashArrayValue}"` : ""}
        />`;
    }
    const showEndArrow = style.end_arrow && canUseArrowStyle(group.type, group.type);
    const arrow = showEndArrow
      ? `<polygon points="21,8 17,5.5 17,10.5" fill="${stroke}"></polygon>`
      : "";
    return `
      <line x1="3" y1="8" x2="${showEndArrow ? 18 : 21}" y2="8"
        stroke="${stroke}"
        stroke-width="${strokeWidth}"
        stroke-linecap="${style.stroke_style === "dashed" ? "butt" : "round"}"
        ${dashArrayValue ? `stroke-dasharray="${dashArrayValue}"` : ""}
      />${arrow}`;
  }

  function renderGenericLegendPreview() {
    const groups = Model.buildLegendGroups(normalizedGenericLegendObjects());
    if (!groups.length) return '<p class="zone-legend-empty">暂无图例对象</p>';
    return groups
      .map((group) => {
        const label =
          group.label ||
          (group.geometry_kind === "path" && group.geometry_closed ? geometryName("closed_path") : geometryName(group.geometry_kind || "path"));
        return `
          <div class="zone-legend-item">
            <svg class="zone-legend-swatch" viewBox="0 0 24 16" aria-hidden="true">
              ${renderGenericLegendSwatch(group)}
            </svg>
            <span class="zone-legend-label">${escapeHtml(label)}</span>
            ${group.count > 1 ? `<span class="zone-legend-count">x ${group.count}</span>` : ""}
          </div>
        `;
      })
      .join("");
  }

  function refreshLegendPreview() {
    const container = $("#zoneLegendPreview");
    if (!container) return;
    container.innerHTML = isFunctionalZoning() ? renderFunctionalZoneLegendPreview() : renderGenericLegendPreview();
    if (state.pptPreviewMode) renderPptPreview();
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
    if (drawingType() !== "functional_zoning") return;
    state.objects.forEach((obj) => addRecentColor(obj.style_hints && obj.style_hints.fill_color));
    pruneRecentColors();
  }

  function normalizeZoneStyle(style = {}) {
    const raw = style || {};
    const next = Model.normalizeStyleHints(raw, "functional_zone");
    const palette = zonePaletteItems();
    const fallbackColor = (palette[0] && palette[0].color) || DEFAULT_ZONE_STYLE.fill_color;
    next.fill_color = isHexColor(raw.fill_color) ? String(raw.fill_color).toUpperCase() : fallbackColor;
    if (!["none", "translucent", "solid", "hatch"].includes(next.fill_mode)) {
      next.fill_mode = DEFAULT_ZONE_STYLE.fill_mode;
    }
    if (!["solid", "dashed", "none", "double"].includes(next.border_style)) {
      next.border_style = DEFAULT_ZONE_STYLE.border_style;
    }
    if (!isHexColor(raw.stroke_color)) next.stroke_color = next.fill_color;
    next.stroke_width = normalizeStrokeWidth(next.stroke_width ?? ZONE_STROKE_WIDTHS[raw.stroke_width_key]);
    next.fill_opacity = Number.isFinite(Number(next.fill_opacity)) ? Number(next.fill_opacity) : DEFAULT_ZONE_STYLE.fill_opacity;
    return next;
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
      "#togglePptPreview",
      "#savePptSlideText",
      "#pptReflowCurrent",
      "#pptReflowAll",
      "#canvasZoomOut",
      "#canvasZoomReset",
      "#canvasZoomIn",
    ].forEach((selector) => {
      const el = $(selector);
      if (el) {
        const supportToolActive = drawingType() !== "functional_zoning" && normalizeActiveTool() === "supporting_images";
        el.disabled =
          !enabled ||
          (selector === "#exportDrawing" && !state.svgExists) ||
          (supportToolActive && ["#finishObject", "#undoPoint"].includes(selector));
      }
    });
    const notes = $("#taskUserNotes");
    if (notes) notes.placeholder = drawingConfig().agentNotesPlaceholder || "";
    const send = $("#sendToAgent");
    if (send) send.textContent = drawingConfig().taskButtonLabel || "发给 agent 出图";
    const activeTool = normalizeActiveTool();
    const activeObjectType = selectedToolObjectType(activeTool);
    const finish = $("#finishObject");
    if (finish) finish.textContent = isFunctionalZoneObject(activeObjectType) ? "完成分区" : "完成" + (TOOL_LABELS[activeTool] || "对象");
    const undo = $("#undoPoint");
    if (undo) undo.textContent = state.currentPoints.length ? "撤销最后一点" : "撤销";
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
    renderWorkspaceMeta();
    if (drawingType() === "functional_zoning") {
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

  function objectStyle(type, rawStyle = {}) {
    const style = type === "functional_zone" ? normalizeZoneStyle(rawStyle) : Model.normalizeStyleHints(rawStyle, type);
    const fill =
      style.fill_mode === "solid" || style.fill_mode === "translucent" || style.fill_mode === "hatch"
        ? style.fill_color
        : "none";
    return {
      stroke: style.stroke_color || "#111827",
      fill,
      hints: style,
    };
  }

  function objectName(type) {
    // Try registry first
    if (REGISTRY_OBJECTS[type]) return REGISTRY_OBJECTS[type].label || type;
    for (const config of Object.values(DRAWING_WORKBENCHES)) {
      const item = (config.objectTypes || []).find((entry) => entry.value === type);
      if (item) return item.label;
    }
    return type;
  }

  function geometryName(kind) {
    if (GEOMETRY_LABELS[kind]) return GEOMETRY_LABELS[kind];
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
    state.objects = Array.isArray(data.drawing.objects)
      ? data.drawing.objects.map((obj) => {
          const migrated = Model.migrateLegacyObject(obj);
          return {
            ...migrated,
            style_hints: Model.normalizeStyleHints(migrated.style_hints, migrated.type),
          };
        })
      : [];
    if (drawingType() === "functional_zoning") {
      state.objects = state.objects
        .filter((obj) => obj.type === "functional_zone" && obj.geometry && (obj.geometry.kind === "polygon" || (obj.geometry.kind === "path" && obj.geometry.closed === true)))
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
    loadDeckLayout().catch((err) => setPptStatus(err.message, false));
    loadSupportingImages(drawingType())
      .then(() => renderPptPreview())
      .catch((err) => setStatus(err.message, false));
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
      .filter((obj) => drawingType() !== "functional_zoning" || (obj.type === "functional_zone" && obj.geometry && (obj.geometry.kind === "polygon" || (obj.geometry.kind === "path" && obj.geometry.closed === true))))
      .map((obj) => {
        if (drawingType() === "functional_zoning") {
          const geometry = { kind: "path", closed: true, coords: obj.geometry.coords };
          // Preserve segments if they contain quadratic arcs
          if (obj.geometry.segments && obj.geometry.segments.some((s) => s.kind === "quadratic")) {
            geometry.segments = obj.geometry.segments;
            geometry.coords = Model.sampleSegments(obj.geometry.segments, true);
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
          style_hints: Model.normalizeStyleHints(obj.style_hints, obj.type),
        };
      });
    return {
      schema_version: "1.2",
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

  function sampleSegments(segments, closed) {
    return Model.sampleSegments(segments, closed !== false);
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

  async function loadSupportingImages(type = drawingType()) {
    if (!(drawingConfig(type).tools || []).includes("supporting_images")) return;
    const project = projectCode();
    if (!project) return;
    const params = new URLSearchParams({ project, drawing_type: type });
    const data = await api(`/api/drawing/supporting/list?${params}`);
    state.supportingImages[type] = Array.isArray(data.images) ? data.images : [];
    state.supportingLoaded[type] = true;
    if (type === drawingType()) renderSpecificTools();
    if (type === drawingType()) renderPptPreview();
  }

  async function uploadSupportingImage() {
    const project = projectCode();
    if (!project) {
      setStatus("请先选择项目，再上传配图。", false);
      return;
    }
    const input = $("#supportingImageFile");
    if (!input || !input.files || !input.files.length) {
      setStatus("请选择一张配图。", false);
      return;
    }
    const form = new FormData();
    form.append("file", input.files[0]);
    const type = drawingType();
    const params = new URLSearchParams({ project, drawing_type: type });
    const data = await api(`/api/drawing/supporting/upload?${params}`, { method: "POST", body: form });
    const saved = (data.saved || [])[0];
    if (saved) {
      const caption = ($("#supportingCaption") && $("#supportingCaption").value.trim()) || "";
      const notes = ($("#supportingNotes") && $("#supportingNotes").value.trim()) || "";
      const sortOrder = Number(($("#supportingOrder") && $("#supportingOrder").value) || saved.sort_order || 1);
      if (caption || notes || sortOrder !== saved.sort_order) {
        await api("/api/drawing/supporting/update", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            project,
            drawing_type: type,
            image_id: saved.id,
            caption,
            notes,
            sort_order: sortOrder,
          }),
        });
      }
    }
    input.value = "";
    await loadSupportingImages(type);
    setStatus("配图已上传。");
  }

  async function deleteSupportingImage(imageId) {
    const project = projectCode();
    if (!project || !imageId) return;
    const type = drawingType();
    await api("/api/drawing/supporting/delete", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project, drawing_type: type, image_id: imageId }),
    });
    await loadSupportingImages(type);
    setStatus("配图已删除。");
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

  function defaultGeometryForTool(toolId, points, objectType) {
    const cleanPoints = (points || []).map((point) => [Number(point[0]), Number(point[1])]);
    const draft = draftGeometryFor(objectType, toolId);
    if (toolId === "closed_path") {
      return { kind: "path", closed: true, coords: cleanPoints };
    }
    if (toolId === "open_path" || toolId === "turning_radius" || toolId === "slope_arrow") {
      return { kind: "path", closed: false, coords: cleanPoints };
    }
    if (toolId === "circle") {
      return { kind: "circle", center: cleanPoints[0], radius: draft.radius };
    }
    if (toolId === "triangle" || toolId === "elevation_marker") {
      return { kind: "triangle", center: cleanPoints[0], size: draft.size, rotation_deg: draft.rotation_deg };
    }
    if (toolId === "text_label") {
      return { kind: "text", coords: cleanPoints.slice(0, 1) };
    }
    return null;
  }

  function createObjectFromTool(toolId, points, options = {}) {
    const spec = TOOL_GEOMETRY[toolId];
    if (!spec) {
      setStatus(`工具 ${toolId} 不能在画布上生成对象。`, false);
      return null;
    }
    const minPoints = spec.minPoints || 1;
    if (!Array.isArray(points) || points.length < minPoints) {
      setStatus(`${TOOL_LABELS[toolId] || toolId} 至少需要 ${minPoints} 个点。`, false);
      return null;
    }
    const objectType = options.objectType || selectedToolObjectType(toolId);
    const objectLabel = $("#objectLabel");
    const labelKey = draftKey(toolId, objectType);
    const index = state.objects.length + 1;
    const id = options.id || nextObjectId();
    const isFunctionalZone = isFunctionalZoneObject(objectType);
    const label =
      options.label ||
      (objectLabel && objectLabel.value.trim()) ||
      (state.labelDrafts[labelKey] || "").trim() ||
      (isFunctionalZone ? state.zoneDraftLabel.trim() || `功能区 ${index}` : `${objectName(objectType)} ${index}`);
    const geometryPoints = spec.kind === "path" ? points.slice() : points.slice(0, minPoints);
    const geometry = defaultGeometryForTool(toolId, geometryPoints, objectType);
    if (!geometry) return null;
    const style = isFunctionalZone ? normalizeZoneStyle(state.zoneDraftStyle) : draftStyleFor(objectType, toolId);
    if (toolId === "turning_radius") {
      style.label_box = {
        ...(style.label_box || {}),
        enabled: true,
        text: (objectLabel && objectLabel.value.trim()) || (style.label_box && style.label_box.text) || "R=9M",
      };
    }
    if (toolId === "elevation_marker") {
      style.label_box = {
        ...(style.label_box || {}),
        enabled: true,
        text: (objectLabel && objectLabel.value.trim()) || (style.label_box && style.label_box.text) || "",
      };
    }
    if (toolId === "slope_arrow") {
      style.inline_text = {
        ...(style.inline_text || {}),
        enabled: true,
        text: (objectLabel && objectLabel.value.trim()) || (style.inline_text && style.inline_text.text) || "0.3%",
      };
    }
    if (toolId === "text_label") {
      const text = (style.text_content || "").trim() || (objectLabel && objectLabel.value.trim()) || "文字";
      style.text_content = text;
    }
    const object = {
      id,
      type: objectType,
      geometry,
      label,
      confidence: "medium",
      source: "user_sketch",
      style_hints: style,
    };
    state.objects.push(object);
    captureObjectDefaults(object, toolId);
    state.selectedId = id;
    if (isFunctionalZone) {
      state.zoneDraftStyle = style;
      state.zoneDraftLabel = "";
    } else {
      state.labelDrafts[labelKey] = "";
    }
    state.currentPoints = [];
    markDirty();
    renderCanvasLayers("create-object-from-tool");
    renderObjectList();
    renderSpecificTools();
    refreshLegendPreview();
    if (isFunctionalZone && style.fill_mode === "none" && style.border_style === "none") {
      setStatus("该分区在图中不可见（无边框 + 无填充）。", false);
    } else {
      setStatus(isFunctionalZone ? `已添加分区：${label}` : `已添加：${label}`);
    }
    return object;
  }

  function addPoint(event) {
    if (event.target.closest && event.target.closest(".zone-arc-handle")) return;
    const point = normalizedPoint(event);
    if (!point) return;
    const activeTool = normalizeActiveTool();
    const spec = TOOL_GEOMETRY[activeTool];
    if (!spec) return;
    pushUndoSnapshot();
    if (!state.currentPoints.length && state.selectedId) {
      captureObjectDefaults(selectedObject());
      state.selectedId = "";
    }
    state.currentPoints.push(point);
    markDirty();
    if (spec.kind !== "path" && state.currentPoints.length >= (spec.minPoints || 1)) {
      createObjectFromTool(activeTool, state.currentPoints);
    } else {
      renderCanvasLayers("add-draft-point");
      renderObjectList();
      renderAvailability();
    }
  }

  function finishObject() {
    if (!isEnabled()) return;
    const activeTool = normalizeActiveTool();
    const spec = TOOL_GEOMETRY[activeTool];
    if (!spec) return;
    if (state.currentPoints.length < (spec.minPoints || 1)) {
      setStatus(`${TOOL_LABELS[activeTool] || activeTool} needs ${spec.minPoints || 1} points.`, false);
      return;
    }
    pushUndoSnapshot();
    createObjectFromTool(activeTool, state.currentPoints);
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

  function safePoint(point) {
    if (!Array.isArray(point) || point.length < 2) return null;
    const x = Number(point[0]);
    const y = Number(point[1]);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return null;
    return [x, y];
  }

  function pathFillValue(obj, style) {
    const mode = style.hints.fill_mode;
    if (mode === "solid") return { color: style.hints.fill_color || style.fill, opacity: 1 };
    if (mode === "hatch") {
      const patternId = `hatch-${String(obj.id || "object").replace(/[^a-zA-Z0-9_-]/g, "-")}`;
      const spacing = Number(style.hints.hatch_spacing) || 0.018;
      const angle = Number(style.hints.hatch_angle_deg) || 45;
      const width = Number(style.hints.hatch_width) || 0.002;
      const color = style.hints.fill_color || style.fill;
      return {
        color: `url(#${patternId})`,
        opacity: 1,
        defs: `
          <defs>
            <pattern id="${patternId}" width="${spacing}" height="${spacing}" patternUnits="userSpaceOnUse" patternTransform="rotate(${angle})">
              <line x1="0" y1="0" x2="0" y2="${spacing}" stroke="${color}" stroke-width="${width}"></line>
            </pattern>
          </defs>
        `,
      };
    }
    if (mode === "translucent") {
      return { color: style.hints.fill_color || style.fill, opacity: style.hints.fill_opacity || 0.42 };
    }
    return { color: "none", opacity: 1 };
  }

  function renderArrowHeads(coords, style, objectId) {
    if (!Array.isArray(coords) || coords.length < 2) return "";
    const parts = [];
    if (style.start_arrow) parts.push(renderArrowHead(coords[1], coords[0], style, objectId));
    if (style.end_arrow) parts.push(renderArrowHead(coords[coords.length - 2], coords[coords.length - 1], style, objectId));
    return parts.join("");
  }

  function stageSize() {
    const stage = $("#workbenchStage");
    const rect = stage && stage.getBoundingClientRect();
    return {
      width: rect && rect.width ? rect.width : 1,
      height: rect && rect.height ? rect.height : 1,
    };
  }

  function arrowGeometry(from, tip, style) {
    from = safePoint(from);
    tip = safePoint(tip);
    if (!from || !tip) return null;
    const stage = stageSize();
    const fromPx = [from[0] * stage.width, from[1] * stage.height];
    const tipPx = [tip[0] * stage.width, tip[1] * stage.height];
    const dx = tipPx[0] - fromPx[0];
    const dy = tipPx[1] - fromPx[1];
    const length = Math.hypot(dx, dy);
    if (!length) return null;
    const size = computedArrowSize(style);
    const sizePx = Math.min(size * stage.width, length * 0.45);
    const sidePx = sizePx * 0.42;
    const ux = dx / length;
    const uy = dy / length;
    const basePx = [tipPx[0] - ux * sizePx, tipPx[1] - uy * sizePx];
    const side = [-uy * sidePx, ux * sidePx];
    const toNorm = (point) => [point[0] / stage.width, point[1] / stage.height];
    return {
      tip,
      base: toNorm(basePx),
      p2: toNorm([basePx[0] + side[0], basePx[1] + side[1]]),
      p3: toNorm([basePx[0] - side[0], basePx[1] - side[1]]),
    };
  }

  function arrowBasePoint(from, tip, style) {
    const geometry = arrowGeometry(from, tip, style);
    return geometry ? geometry.base : safePoint(tip);
  }

  function renderArrowHead(from, tip, style, objectId) {
    const geometry = arrowGeometry(from, tip, style);
    if (!geometry) return "";
    const p1 = geometry.tip;
    const p2 = geometry.p2;
    const p3 = geometry.p3;
    return `<polygon data-object-id="${escapeHtml(objectId)}" points="${[p1, p2, p3].map((p) => p.join(",")).join(" ")}" fill="${style.stroke_color || "#333333"}"></polygon>`;
  }

  function trimOpenPathCoordsForArrows(coords, style) {
    const next = (coords || []).map((point) => safePoint(point)).filter(Boolean);
    if (next.length < 2) return next;
    if (style.start_arrow) next[0] = arrowBasePoint(next[1], next[0], style);
    if (style.end_arrow) next[next.length - 1] = arrowBasePoint(next[next.length - 2], next[next.length - 1], style);
    return next;
  }

  function trimOpenSegmentsForArrows(segments, style) {
    const next = (segments || []).map((segment) => ({ ...segment }));
    if (!next.length) return next;
    if (style.start_arrow) {
      const first = next[0];
      const from = safePoint(first.from);
      const toward = safePoint(first.kind === "quadratic" ? first.control : first.to);
      if (from && toward) first.from = arrowBasePoint(toward, from, style);
    }
    if (style.end_arrow) {
      const last = next[next.length - 1];
      const to = safePoint(last.to);
      const from = safePoint(last.kind === "quadratic" ? last.control : last.from);
      if (from && to) last.to = arrowBasePoint(from, to, style);
    }
    return next;
  }

  function renderSemanticTextOverlays(obj, fallbackPoint, style) {
    const parts = [];
    const anchor = objectAnchorPoint(obj) || fallbackPoint || [0.5, 0.5];
    if (style.label_box && style.label_box.enabled) {
      const box = style.label_box;
      const offset = Array.isArray(box.offset) ? box.offset : [0.02, -0.02];
      const width = Number(box.width) || 0.09;
      const height = Number(box.height) || 0.035;
      const x = Math.min(Math.max(anchor[0] + Number(offset[0] || 0), 0.01), 0.98 - width);
      const y = Math.min(Math.max(anchor[1] + Number(offset[1] || 0), 0.01), 0.98 - height);
      const color = style.stroke_color || style.fill_color || "#333333";
      const text = box.text || obj.label || "";
      parts.push(`<rect data-object-id="${escapeHtml(obj.id)}" x="${x}" y="${y}" width="${width}" height="${height}" rx="0" fill="#FFFFFF" fill-opacity="${box.opacity ?? 0.55}"></rect>`);
      if (text) {
        parts.push(`<text x="${x + width * 0.08}" y="${y + height * 0.65}" fill="${color}" font-size="${box.font_size || 0.018}" font-weight="700">${escapeHtml(text)}</text>`);
      }
      if (obj.id === state.selectedId) {
        parts.push(
          renderHandleSvg(
            x + width,
            y,
            "#fff",
            color,
            `data-vertex-object-id="${escapeHtml(obj.id)}" data-vertex-index="labelbox" data-vertex-role="labelbox"`,
          ),
        );
      }
    }
    if (style.inline_text && style.inline_text.enabled) {
      const inline = style.inline_text;
      const coords = objectPathCoords(obj);
      if (coords.length >= 2) {
        const position = Math.min(Math.max(Number(inline.position) || 0.5, 0), 1);
        const start = coords[0];
        const end = coords[coords.length - 1];
        const offset = Array.isArray(inline.offset) ? inline.offset : [0, -0.018];
        const stage = stageSize();
        const dxPx = (end[0] - start[0]) * stage.width;
        const dyPx = (end[1] - start[1]) * stage.height;
        const length = Math.hypot(dxPx, dyPx) || 1;
        const dxN = dxPx / length;
        const dyN = dyPx / length;
        const alongOffset = Number(offset[0] || 0);
        const normalOffset = Math.abs(Number(offset[1] || 0));
        const basePx = [
          (start[0] + (end[0] - start[0]) * position) * stage.width,
          (start[1] + (end[1] - start[1]) * position) * stage.height,
        ];
        let nx = -dyN;
        let ny = dxN;
        if (ny > 0) {
          nx = -nx;
          ny = -ny;
        }
        const x = (basePx[0] + dxN * alongOffset * stage.width + nx * normalOffset * stage.width) / stage.width;
        const y = (basePx[1] + dyN * alongOffset * stage.width + ny * normalOffset * stage.width) / stage.height;
        let angle = Model.lineAngleDeg(coords);
        if (angle > 90 || angle < -90) angle += 180;
        angle = ((angle % 360) + 360) % 360;
        parts.push(`<text x="${x}" y="${y}" text-anchor="middle" transform="rotate(${angle} ${x} ${y})" fill="${style.stroke_color || "#333333"}" font-size="${inline.font_size || 0.018}" font-weight="700">${escapeHtml(inline.text || obj.label || "")}</text>`);
      }
    }
    return parts.join("");
  }

  function objectAnchorPoint(obj) {
    const geo = (obj && obj.geometry) || {};
    if (geo.kind === "circle" || geo.kind === "triangle") return safePoint(geo.center);
    if (geo.kind === "text") return safePoint((geo.coords || [])[0]);
    const coords = objectPathCoords(obj);
    return coords[Math.floor(coords.length / 2)] || null;
  }

  function aspectK() {
    const stage = $("#workbenchStage");
    const rect = stage && stage.getBoundingClientRect();
    return rect && rect.height ? rect.width / rect.height : 1;
  }

  function aspectCompensatePoint(point, center, k = aspectK()) {
    return [point[0], center[1] + (point[1] - center[1]) * k];
  }

  function aspectUncompensatePoint(point, center, k = aspectK()) {
    return [point[0], center[1] + (point[1] - center[1]) / k];
  }

  function aspectCompensatePoints(points, center, k = aspectK()) {
    return (points || []).map((point) => aspectCompensatePoint(point, center, k));
  }

  function extendScreenPoint(center, point, distance = 0.038) {
    const stage = stageSize();
    const cx = center[0] * stage.width;
    const cy = center[1] * stage.height;
    const px = point[0] * stage.width;
    const py = point[1] * stage.height;
    const dx = px - cx;
    const dy = py - cy;
    const length = Math.hypot(dx, dy) || 1;
    const extra = distance * stage.width;
    return [(px + (dx / length) * extra) / stage.width, (py + (dy / length) * extra) / stage.height];
  }

  function objectPathCoords(obj) {
    const geo = (obj && obj.geometry) || {};
    if (Array.isArray(geo.segments) && geo.segments.length) return Model.sampleSegments(geo.segments, !!geo.closed);
    return Array.isArray(geo.coords) ? geo.coords.map(safePoint).filter(Boolean) : [];
  }

  function objectVertexPoints(obj) {
    const geo = (obj && obj.geometry) || {};
    if (Array.isArray(geo.segments) && geo.segments.length) {
      const points = geo.segments.map((seg) => safePoint(seg.from)).filter(Boolean);
      if (!geo.closed) {
        const last = geo.segments[geo.segments.length - 1];
        const end = last && safePoint(last.to);
        if (end) points.push(end);
      }
      return points;
    }
    return Array.isArray(geo.coords) ? geo.coords.map(safePoint).filter(Boolean) : [];
  }

  function selectedStrokeColor(color, selected) {
    return selected && isHexColor(color) ? darkenHex(color, 0.2) : color;
  }

  function renderSharedVertexHandles(points, fill, stroke, options = {}) {
    const roles = options.roles || [];
    return (points || [])
      .map(([x, y], index) => {
        const attrs = options.objectId
          ? `data-vertex-object-id="${escapeHtml(options.objectId)}" data-vertex-index="${index}" data-vertex-role="${escapeHtml(roles[index] || "vertex")}"`
          : "";
        return renderHandleSvg(x, y, fill, stroke, attrs);
      })
      .join("");
  }

  function renderSharedPathHitLayer({ objectId, pathD, points, closed, style, fillVisible, borderVisible }) {
    if (state.currentPoints.length > 0) return "";
    const classes = "zone-hit geometry-hit";
    const safeStyle = style || {};
    if (closed) {
      if (borderVisible) {
        if (pathD) {
          return `
            <path
              class="${classes}"
              data-object-id="${escapeHtml(objectId)}"
              d="${pathD}"
              fill="none"
              stroke="transparent"
              stroke-width="${getZoneHitStrokeWidth(safeStyle)}"
              pointer-events="stroke"
            ></path>
          `;
        }
        return `
          <polygon
            class="${classes}"
            data-object-id="${escapeHtml(objectId)}"
            points="${(points || []).map((point) => point.join(",")).join(" ")}"
            fill="none"
            stroke="transparent"
            stroke-width="${getZoneHitStrokeWidth(safeStyle)}"
            pointer-events="stroke"
          ></polygon>
        `;
      }
      if (fillVisible) {
        if (pathD) {
          return `
            <path
              class="${classes}"
              data-object-id="${escapeHtml(objectId)}"
              d="${pathD}"
              fill="transparent"
              stroke="none"
              pointer-events="fill"
            ></path>
          `;
        }
        return `
          <polygon
            class="${classes}"
            data-object-id="${escapeHtml(objectId)}"
            points="${(points || []).map((point) => point.join(",")).join(" ")}"
            fill="transparent"
            stroke="none"
            pointer-events="fill"
          ></polygon>
        `;
      }
      return "";
    }
    if (pathD) {
      return `
        <path
          class="${classes}"
          data-object-id="${escapeHtml(objectId)}"
          d="${pathD}"
          fill="none"
          stroke="transparent"
          stroke-width="${getZoneHitStrokeWidth(safeStyle)}"
          pointer-events="stroke"
        ></path>
      `;
    }
    return `
      <polyline
        class="${classes}"
        data-object-id="${escapeHtml(objectId)}"
        points="${(points || []).map((point) => point.join(",")).join(" ")}"
        fill="none"
        stroke="transparent"
        stroke-width="${getZoneHitStrokeWidth(safeStyle)}"
        pointer-events="stroke"
      ></polyline>
    `;
  }

  function renderSharedCircleHitLayer({ objectId, cx, cy, radius, ry, style }) {
    if (state.currentPoints.length > 0) return "";
    return `
      <ellipse
        class="zone-hit geometry-hit"
        data-object-id="${escapeHtml(objectId)}"
        cx="${cx}"
        cy="${cy}"
        rx="${radius}"
        ry="${ry || radius}"
        fill="transparent"
        stroke="transparent"
        stroke-width="${getZoneHitStrokeWidth(style || {})}"
        pointer-events="all"
      ></ellipse>
    `;
  }

  function renderSharedPolygonHitLayer({ objectId, points, style }) {
    if (state.currentPoints.length > 0) return "";
    return `
      <polygon
        class="zone-hit geometry-hit"
        data-object-id="${escapeHtml(objectId)}"
        points="${(points || []).map((point) => point.join(",")).join(" ")}"
        fill="transparent"
        stroke="transparent"
        stroke-width="${getZoneHitStrokeWidth(style || {})}"
        pointer-events="all"
      ></polygon>
    `;
  }

  function renderObjectSvg(obj) {
    const style = objectStyle(obj.type, obj.style_hints);
    const selected = obj.id === state.selectedId;
    const sw = Number(style.hints.stroke_width) > 0 ? Number(style.hints.stroke_width) : 0.003;
    const geo = obj.geometry || {};
    let shape = "";
    let labelPoint = [0.5, 0.5];

    if (geo.kind === "text") {
      const [x, y] = safePoint((geo.coords || [])[0]) || [0.5, 0.5];
      const color = style.hints.stroke_color || style.stroke || "#333333";
      const fontSize = Number(style.hints.font_size) > 0 ? Number(style.hints.font_size) : 0.024;
      const text = style.hints.text_content || obj.label || "文字";
      shape = `<text data-object-id="${escapeHtml(obj.id)}" x="${x}" y="${y}" text-anchor="middle" dominant-baseline="middle" fill="${color}" font-size="${fontSize}" font-weight="700">${escapeHtml(text)}</text>`;
      shape += renderSharedCircleHitLayer({
        objectId: obj.id,
        cx: x,
        cy: y,
        radius: Math.max(0.028, fontSize * 2.2),
        ry: Math.max(0.02, fontSize * 1.5 * aspectK()),
        style: style.hints,
      });
      if (selected) {
        shape += renderSharedVertexHandles([[x, y]], "#fff", color, {
          objectId: obj.id,
          roles: ["text-anchor"],
        });
      }
      labelPoint = [x, y];
    } else if (geo.kind === "circle") {
      const center = safePoint(geo.center) || safePoint((geo.coords || [])[0]) || [0.5, 0.5];
      const cx = center[0], cy = center[1], r = Number(geo.radius) > 0 ? Number(geo.radius) : 0.035;
      const ry = r * aspectK();
      const fillVisible = style.hints.fill_mode === "solid" || style.hints.fill_mode === "translucent";
      const fill = fillVisible ? style.hints.fill_color || style.fill : "none";
      const fillOpacity = style.hints.fill_mode === "translucent" ? String(style.hints.fill_opacity || 0.42) : "1";
      const borderVisible = style.hints.border_style !== "none";
      const stroke = borderVisible ? selectedStrokeColor(style.stroke, selected) : "none";
      const borderW = borderVisible ? sw : 0;
      const dash = (style.hints.stroke_style === "dashed" || style.hints.border_style === "dashed") ? ` stroke-dasharray="${dashArray(style.hints)}"` : "";
      shape = `<ellipse cx="${cx}" cy="${cy}" rx="${r}" ry="${ry}" fill="${fill}" fill-opacity="${fillOpacity}" stroke="${stroke}" stroke-width="${borderW}"${dash} pointer-events="none"></ellipse>`;
      if (borderVisible && style.hints.border_style === "double") {
        const innerR = Math.max(0.004, r - (style.hints.double_border_gap || 0.006));
        shape += `<ellipse cx="${cx}" cy="${cy}" rx="${innerR}" ry="${innerR * aspectK()}" fill="none" stroke="${stroke}" stroke-width="${borderW}" pointer-events="none"></ellipse>`;
      }
      shape += renderSharedCircleHitLayer({ objectId: obj.id, cx, cy, radius: r, ry, style: style.hints });
      if (selected) {
        shape += renderSharedVertexHandles([[cx, cy], [Math.min(1, cx + r), cy]], "#fff", stroke, {
          objectId: obj.id,
          roles: ["circle-center", "circle-radius"],
        });
      }
      labelPoint = [cx, cy - r];
    } else if (geo.kind === "triangle") {
      const center = safePoint(geo.center) || safePoint((geo.coords || [])[0]) || [0.5, 0.5];
      const cx = center[0], cy = center[1];
      const size = geo.size || 0.055;
      const rot = geo.rotation_deg || 0;
      const rawPts = Model.trianglePoints([cx, cy], size, rot);
      const pts = aspectCompensatePoints(rawPts, [cx, cy]);
      const points = pts.map(p => p.join(",")).join(" ");
      const fillVisible = style.hints.fill_mode === "solid" || style.hints.fill_mode === "translucent";
      const fill = fillVisible ? style.hints.fill_color || style.fill : "none";
      const fillOpacity = style.hints.fill_mode === "translucent" ? String(style.hints.fill_opacity || 0.42) : "1";
      const borderVisible = style.hints.border_style !== "none";
      const stroke = borderVisible ? selectedStrokeColor(style.stroke, selected) : "none";
      const borderW = borderVisible ? sw : 0;
      const dash = (style.hints.stroke_style === "dashed" || style.hints.border_style === "dashed") ? ` stroke-dasharray="${dashArray(style.hints)}"` : "";
      shape = `<polygon points="${points}" fill="${fill}" fill-opacity="${fillOpacity}" stroke="${stroke}" stroke-width="${borderW}"${dash} pointer-events="none"></polygon>`;
      if (borderVisible && style.hints.border_style === "double") {
        const innerPts = aspectCompensatePoints(Model.trianglePoints([cx, cy], Math.max(0.01, size - (style.hints.double_border_gap || 0.006)), rot), [cx, cy]);
        shape += `<polygon points="${innerPts.map(p => p.join(",")).join(" ")}" fill="none" stroke="${stroke}" stroke-width="${borderW}" pointer-events="none"></polygon>`;
      }
      shape += renderSharedPolygonHitLayer({ objectId: obj.id, points: pts, style: style.hints });
      if (selected) {
        shape += renderSharedVertexHandles(pts, "#fff", stroke, {
          objectId: obj.id,
          roles: ["triangle-size", "triangle-size", "triangle-size"],
        });
        const rotatePoint = extendScreenPoint([cx, cy], pts[0]);
        shape += `<line class="geometry-rotate-stem" x1="${pts[0][0]}" y1="${pts[0][1]}" x2="${rotatePoint[0]}" y2="${rotatePoint[1]}" stroke="${stroke}" stroke-width="${getHandleStrokeWidth()}" pointer-events="none"></line>`;
        shape += renderRotateHandle(
          rotatePoint[0],
          rotatePoint[1],
          stroke,
          `data-vertex-object-id="${escapeHtml(obj.id)}" data-vertex-index="rotate" data-vertex-role="triangle-rotate"`,
        );
      }
      labelPoint = [cx, cy - size];
    } else if ((geo.kind === "path" && geo.closed) || geo.kind === "polygon") {
      // Closed path (polygon)
      const closedCoords = objectPathCoords(obj);
      if (closedCoords.length < 3) return "";
      const segments = geo.segments;
      const stroke = style.hints.border_style === "none" ? "none" : selectedStrokeColor(style.stroke, selected);
      const borderWidth = style.hints.border_style === "none" ? 0 : sw;
      const dash = (style.hints.stroke_style === "dashed" || style.hints.border_style === "dashed") ? ` stroke-dasharray="${dashArray(style.hints)}"` : "";
      if (segments && segments.length > 0) {
        const pathD = segmentsToPathD(segments, true);
        const fill = pathFillValue(obj, style);
        shape = `${fill.defs || ""}<path d="${pathD}" fill="${fill.color}" fill-opacity="${fill.opacity}" stroke="${stroke}" stroke-width="${borderWidth}" stroke-linejoin="round"${dash} pointer-events="none"></path>`;
        if (style.hints.border_style === "double") {
          shape += `<path d="${pathD}" fill="none" stroke="${stroke}" stroke-width="${Math.max(0.001, borderWidth - (style.hints.double_border_gap || 0.006) / 2)}" stroke-linejoin="round" pointer-events="none"></path>`;
        }
        shape += renderSharedPathHitLayer({
          objectId: obj.id,
          pathD,
          closed: true,
          style: style.hints,
          fillVisible: fill.color !== "none",
          borderVisible: style.hints.border_style !== "none",
        });
      } else {
        const points = closedCoords.map(p => p.join(",")).join(" ");
        const fill = pathFillValue(obj, style);
        shape = `${fill.defs || ""}<polygon points="${points}" fill="${fill.color}" fill-opacity="${fill.opacity}" stroke="${stroke}" stroke-width="${borderWidth}"${dash} pointer-events="none"></polygon>`;
        if (style.hints.border_style === "double") {
          shape += `<polygon points="${points}" fill="none" stroke="${stroke}" stroke-width="${Math.max(0.001, borderWidth - (style.hints.double_border_gap || 0.006) / 2)}" pointer-events="none"></polygon>`;
        }
        shape += renderSharedPathHitLayer({
          objectId: obj.id,
          points: closedCoords,
          closed: true,
          style: style.hints,
          fillVisible: fill.color !== "none",
          borderVisible: style.hints.border_style !== "none",
        });
      }
      if (selected) {
        const stroke = selectedStrokeColor(style.stroke, true);
        shape += renderSharedVertexHandles(objectVertexPoints(obj), "#fff", stroke);
        shape += renderSegmentHandles(obj.id, ensureSegments(obj), { fill_color: stroke });
      }
      labelPoint = closedCoords[Math.floor(closedCoords.length / 2)] || closedCoords[0];
    } else if (geo.kind === "point") {
      const [x, y] = safePoint((geo.coords || [])[0]) || [0.5, 0.5];
      shape = `<circle data-object-id="${escapeHtml(obj.id)}" cx="${x}" cy="${y}" r="0.012" fill="${style.stroke}" stroke="#fff" stroke-width="0.004"></circle>`;
      labelPoint = [x, y];
    } else {
      // Open path (polyline/arrow/line)
      const coords = objectPathCoords(obj);
      const segments = geo.segments;
      const stroke = selectedStrokeColor(style.stroke, selected);
      if (segments && segments.length > 0) {
        const visibleSegments = shouldRenderArrowHeads(obj) ? trimOpenSegmentsForArrows(segments, style.hints) : segments;
        const pathD = segmentsToPathD(visibleSegments, false);
        const hitPathD = segmentsToPathD(segments, false);
        const dash = style.hints.stroke_style === "dashed" ? ` stroke-dasharray="${dashArray(style.hints)}"` : "";
        const lineCap = style.hints.stroke_style === "dashed" ? "butt" : "round";
        shape = `<path d="${pathD}" fill="none" stroke="${stroke}" stroke-width="${sw}" stroke-linecap="${lineCap}" stroke-linejoin="round"${dash} pointer-events="none"></path>`;
        shape += renderSharedPathHitLayer({ objectId: obj.id, pathD: hitPathD, closed: false, style: style.hints });
      } else if (coords.length >= 2) {
        const visibleCoords = shouldRenderArrowHeads(obj) ? trimOpenPathCoordsForArrows(coords, style.hints) : coords;
        const points = visibleCoords.map(p => p.join(",")).join(" ");
        const dash = style.hints.stroke_style === "dashed" ? ` stroke-dasharray="${dashArray(style.hints)}"` : "";
        const lineCap = style.hints.stroke_style === "dashed" ? "butt" : "round";
        shape = `<polyline points="${points}" fill="none" stroke="${stroke}" stroke-width="${sw}" stroke-linecap="${lineCap}" stroke-linejoin="round"${dash} pointer-events="none"></polyline>`;
        shape += renderSharedPathHitLayer({ objectId: obj.id, points: coords, closed: false, style: style.hints });
      }
      if (shouldRenderArrowHeads(obj)) shape += renderArrowHeads(coords, style.hints, obj.id);
      if (selected && coords.length >= 2) {
        const stroke = selectedStrokeColor(style.stroke, true);
        shape += renderSharedVertexHandles(objectVertexPoints(obj), "#fff", stroke);
        shape += renderSegmentHandles(obj.id, ensureSegments(obj), { fill_color: stroke });
      }
      if (coords.length) labelPoint = coords[Math.floor(coords.length / 2)] || coords[0];
    }
    const overlays = renderSemanticTextOverlays(obj, labelPoint, style.hints);
    return `${shape}${overlays}`;
  }

  function segmentsToPathD(segments, closed) {
    return Model.segmentsToPathD(segments, closed !== false);
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
    const activeTool = normalizeActiveTool();
    const spec = TOOL_GEOMETRY[activeTool] || {};
    const minPoints = spec.minPoints || 1;
    const objectType = selectedToolObjectType(activeTool);
    const draftStyle = draftStyleFor(objectType, activeTool);
    const handleColor = draftStyle.fill_color || draftStyle.stroke_color || "#111827";
    const circles = state.currentPoints
      .map(([x, y], index) =>
        spec.kind === "path" && spec.closed && index === 0 && state.currentPoints.length >= minPoints
          ? renderCloseHandleSvg(x, y, handleColor)
          : renderHandleSvg(x, y, "#111827", "none"),
      )
      .join("");
    return `<polyline points="${points}" fill="none" stroke="#111827" stroke-width="${ZONE_EDIT_WIDTH}" stroke-dasharray="0.014 0.012"></polyline>${circles}`;
  }

  function renderHandleSvg(x, y, fill, stroke, attrs = "") {
    const strokeAttr = stroke === "none" ? 'stroke="none"' : `stroke="${stroke}" stroke-width="${getHandleStrokeWidth()}"`;
    return `<ellipse class="geometry-vertex-handle" ${attrs} cx="${x}" cy="${y}" rx="${getHandleRadiusX()}" ry="${getHandleRadiusY()}" fill="${fill}" ${strokeAttr}></ellipse>`;
  }

  function renderRotateHandle(x, y, stroke, attrs = "") {
    const outerRx = getHandleRadiusX(9);
    const outerRy = getHandleRadiusY(9);
    const arcRx = getHandleRadiusX(4.5);
    const arcRy = getHandleRadiusY(4.5);
    const strokeWidth = getHandleStrokeWidth();
    const startRad = (-145 * Math.PI) / 180;
    const endRad = (65 * Math.PI) / 180;
    const start = [x + Math.cos(startRad) * arcRx, y + Math.sin(startRad) * arcRy];
    const end = [x + Math.cos(endRad) * arcRx, y + Math.sin(endRad) * arcRy];
    const ux = -Math.sin(endRad);
    const uy = Math.cos(endRad);
    const nx = -uy;
    const ny = ux;
    const arrowX = getHandleRadiusX(3.2);
    const arrowY = getHandleRadiusY(3.2);
    const base = [end[0] - ux * arrowX, end[1] - uy * arrowY];
    const p2 = [base[0] + nx * arrowX * 0.65, base[1] + ny * arrowY * 0.65];
    const p3 = [base[0] - nx * arrowX * 0.65, base[1] - ny * arrowY * 0.65];
    return `
      <g class="geometry-vertex-handle geometry-rotate-icon" ${attrs}>
        <ellipse cx="${x}" cy="${y}" rx="${outerRx}" ry="${outerRy}" fill="#fff" stroke="${stroke}" stroke-width="${strokeWidth}" pointer-events="all"></ellipse>
        <path class="geometry-rotate-arrow" d="M ${start[0]} ${start[1]} A ${arcRx} ${arcRy} 0 1 1 ${end[0]} ${end[1]}" fill="none" stroke="${stroke}" stroke-width="${strokeWidth}" stroke-linecap="round" pointer-events="none"></path>
        <polygon points="${[end, p2, p3].map((p) => p.join(",")).join(" ")}" fill="${stroke}" pointer-events="none"></polygon>
      </g>
    `;
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
        finishObject();
      });
    });
    overlay.querySelectorAll(".geometry-hit[data-object-id]").forEach((shape) => {
      shape.addEventListener("pointerdown", (event) => {
        if (event.button !== undefined && event.button !== 0) return;
        event.stopPropagation();
        const obj = state.objects.find((item) => item.id === shape.dataset.objectId);
        if (!obj) return;
        state.moveDrag = {
          objectId: obj.id,
          startX: event.clientX,
          startY: event.clientY,
          moved: false,
          original: clonePlain(obj),
        };
      });
    });
    overlay.querySelectorAll("[data-object-id]:not(.zone-arc-handle)").forEach((shape) => {
      shape.addEventListener("click", (event) => {
        event.stopPropagation();
        selectObject(shape.dataset.objectId);
      });
    });
    overlay.querySelectorAll(".geometry-vertex-handle[data-vertex-object-id]").forEach((handle) => {
      handle.addEventListener("pointerdown", (event) => {
        event.stopPropagation();
        event.preventDefault();
        state.vertexDrag = {
          objectId: handle.dataset.vertexObjectId,
          role: handle.dataset.vertexRole || "vertex",
          startX: event.clientX,
          startY: event.clientY,
          moved: false,
        };
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

  function clonePlain(value) {
    return JSON.parse(JSON.stringify(value));
  }

  function translatePoint(point, dx, dy) {
    const p = safePoint(point);
    return p ? clampUnit([p[0] + dx, p[1] + dy]) : point;
  }

  function translateSegment(segment, dx, dy) {
    if (!segment || typeof segment !== "object") return segment;
    const next = { ...segment };
    if (segment.from) next.from = translatePoint(segment.from, dx, dy);
    if (segment.to) next.to = translatePoint(segment.to, dx, dy);
    if (segment.control) next.control = translatePoint(segment.control, dx, dy);
    return next;
  }

  function translateGeometry(geometry, dx, dy) {
    if (!geometry || typeof geometry !== "object") return geometry;
    const next = { ...geometry };
    if (Array.isArray(geometry.coords)) next.coords = geometry.coords.map((point) => translatePoint(point, dx, dy));
    if (Array.isArray(geometry.segments)) next.segments = geometry.segments.map((segment) => translateSegment(segment, dx, dy));
    if (geometry.center) next.center = translatePoint(geometry.center, dx, dy);
    return next;
  }

  function applyTranslatedGeometry(target, original, dx, dy) {
    if (!target || !original) return;
    target.geometry = translateGeometry(original.geometry, dx, dy);
  }

  function updateMoveDrag(event) {
    const drag = state.moveDrag;
    if (!drag) return;
    const stage = $("#workbenchStage");
    if (!stage) return;
    const rect = stage.getBoundingClientRect();
    const dxPx = event.clientX - drag.startX;
    const dyPx = event.clientY - drag.startY;
    const dist = Math.hypot(dxPx, dyPx);
    if (!drag.moved && dist < 3) return;
    const obj = state.objects.find((item) => item.id === drag.objectId);
    if (!obj) return;
    if (!drag.moved) {
      drag.moved = true;
      pushUndoSnapshot();
      state.selectedId = drag.objectId;
    }
    const dx = dxPx / (rect.width || 1);
    const dy = dyPx / (rect.height || 1);
    applyTranslatedGeometry(obj, drag.original, dx, dy);
    markDirty();
    renderCanvasLayers("move-drag");
    renderObjectList();
    renderSpecificTools();
  }

  function finishMoveDrag() {
    if (!state.moveDrag) return;
    const moved = state.moveDrag.moved;
    state.moveDrag = null;
    if (moved) {
      markDirty();
      refreshLegendPreview();
    }
  }

  function copySelectedObject() {
    const selected = selectedObject();
    if (!selected) return false;
    state.clipboard = clonePlain(selected);
    setStatus("已复制选中对象。");
    return true;
  }

  function pasteClipboardObject() {
    if (!state.clipboard) return false;
    pushUndoSnapshot();
    const pasted = clonePlain(state.clipboard);
    pasted.id = nextObjectId();
    pasted.geometry = translateGeometry(pasted.geometry, 0.02, 0.02);
    state.objects.push(pasted);
    state.selectedId = pasted.id;
    captureObjectDefaults(pasted);
    markDirty();
    renderCanvasLayers("paste-object");
    renderObjectList();
    renderSpecificTools();
    refreshLegendPreview();
    setStatus(`已粘贴：${pasted.label || pasted.id}`);
    return true;
  }


  function getSelectedObject() {
    return state.objects.find((obj) => obj.id === state.selectedId) || null;
  }

  function ensureSegments(obj) {
    if (obj.geometry.segments && obj.geometry.segments.length > 0) {
      return obj.geometry.segments;
    }
    const coords = obj.geometry.coords || [];
    return Model.coordsToSegments(coords, obj.geometry.closed !== false);
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

  function updateVertexDrag(event) {
    if (!state.vertexDrag) return;
    const stage = $("#workbenchStage");
    if (!stage) return;
    const rect = stage.getBoundingClientRect();
    const p = clampUnit(normalizedPoint(event));
    if (!p) return;
    const dx = (event.clientX - state.vertexDrag.startX) / rect.width;
    const dy = (event.clientY - state.vertexDrag.startY) / rect.height;
    const dist = Math.sqrt(dx * dx + dy * dy);
    const shortSide = Math.min(rect.width, rect.height) || 1;
    if (!state.vertexDrag.moved && dist < 3 / shortSide) return;
    if (!state.vertexDrag.moved) {
      state.vertexDrag.moved = true;
      pushUndoSnapshot();
    }
    const obj = state.objects.find((o) => o.id === state.vertexDrag.objectId);
    if (!obj || !obj.geometry) return;
    if (state.vertexDrag.role === "labelbox") {
      const anchor = objectAnchorPoint(obj) || [0.5, 0.5];
      const current = obj.style_hints || {};
      const box = current.label_box || {};
      const width = Number(box.width) || 0.09;
      obj.style_hints = {
        ...current,
        label_box: {
          ...box,
          enabled: true,
          offset: [Number((p[0] - anchor[0] - width).toFixed(6)), Number((p[1] - anchor[1]).toFixed(6))],
        },
      };
    } else if (obj.geometry.kind === "circle") {
      if (state.vertexDrag.role === "circle-center") {
        obj.geometry.center = p;
      } else {
        const center = safePoint(obj.geometry.center) || [0.5, 0.5];
        const radius = Math.hypot(p[0] - center[0], p[1] - center[1]);
        obj.geometry.radius = Number(Math.max(0.004, Math.min(0.25, radius)).toFixed(6));
      }
    } else if (obj.geometry.kind === "text") {
      obj.geometry.coords = [p];
    } else if (obj.geometry.kind === "triangle") {
      const center = safePoint(obj.geometry.center) || [0.5, 0.5];
      const modelPoint = aspectUncompensatePoint(p, center);
      const vx = modelPoint[0] - center[0];
      const vy = modelPoint[1] - center[1];
      const radius = Math.hypot(vx, vy);
      if (radius <= 0.004) return;
      if (state.vertexDrag.role === "triangle-rotate") {
        obj.geometry.rotation_deg = Number((((Math.atan2(vy, vx) * 180) / Math.PI + 90 + 360) % 360).toFixed(3));
      } else if (state.vertexDrag.role === "triangle-size") {
        obj.geometry.size = Number(Math.max(0.012, Math.min(0.28, radius * 1.5)).toFixed(6));
      }
    }
    captureObjectDefaults(obj);
    markDirty();
    renderCanvasLayers("vertex-drag");
    renderObjectList();
    renderSpecificTools();
  }


  function selectObject(id) {
    state.selectedId = id || "";
    state.currentPoints = [];
    captureObjectDefaults(selectedObject());
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

  function renderObjectList() {
    const list = $("#objectList");
    if (!list) return;
    if (!state.objects.length) {
      list.innerHTML = '<div class="control-empty">还没有语义对象。</div>';
      return;
    }
    if (drawingType() === "functional_zoning") {
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
    const fill = style.fill_mode !== "none" ? style.fill_color : "transparent";
    const borderColor = style.border_style === "none" ? "transparent" : style.stroke_color || style.fill_color;
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
    if (modifier && event.key.toLowerCase() === "c" && !editable) {
      if (copySelectedObject()) event.preventDefault();
      return;
    }
    if (modifier && event.key.toLowerCase() === "v" && !editable) {
      if (pasteClipboardObject()) event.preventDefault();
      return;
    }
    if (modifier && event.key.toLowerCase() === "z" && !isEditableElement(document.activeElement)) {
      event.preventDefault();
      if (event.shiftKey) redoHistory();
      else undoHistory();
      return;
    }
    if (!modifier && event.key === "Enter" && !editable && canFinishDraft()) {
      event.preventDefault();
      finishObject();
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

  async function bind() {
    if (!$("#drawingWorkbench")) return;
    // Load registry and shared style presets first, then render.
    await loadRegistry();
    await loadStylePresets();
    state.currentDrawingType = initialDrawingType();
    renderDrawingTabs();
    renderDrawingWorkspace();

    $("#workbenchLoad").addEventListener("click", () => loadDrawing().catch((err) => setStatus(err.message, false)));
    $("#workbenchSave").addEventListener("click", () => saveDrawing().catch((err) => setStatus(err.message, false)));
    $("#togglePptPreview")?.addEventListener("click", () => {
      state.pptPreviewMode = !state.pptPreviewMode;
      renderPptControls();
      renderPptPreview();
      if (state.pptPreviewMode && !state.deckLayout) {
        loadDeckLayout().catch((err) => setPptStatus(err.message, false));
      }
    });
    $("#savePptSlideText")?.addEventListener("click", () => saveCurrentPptText().catch((err) => setStatus(err.message, false)));
    $("#pptReflowCurrent")?.addEventListener("click", () =>
      reflowDeckLayout("current")
        .then(() => setStatus("已重新排版当前PPT页。"))
        .catch((err) => setStatus(err.message, false)),
    );
    $("#pptReflowAll")?.addEventListener("click", () =>
      reflowDeckLayout("all")
        .then(() => setStatus("已重新排版全部PPT页。"))
        .catch((err) => setStatus(err.message, false)),
    );
    document.querySelectorAll("[data-ppt-template]").forEach((button) => {
      button.addEventListener("click", () => applyPptTemplate(button.dataset.pptTemplate).catch((err) => setStatus(err.message, false)));
    });
    $("#uploadBaseImage").addEventListener("click", () => uploadBaseImage().catch((err) => setStatus(err.message, false)));
    $("#sendToAgent").addEventListener("click", () => sendToAgent().catch((err) => setTaskStatus(err.message, false)));
    $("#exportDrawing").addEventListener("click", () => exportDrawing().catch((err) => setStatus(err.message, false)));
    $("#finishObject").addEventListener("click", finishObject);
    $("#undoPoint").addEventListener("click", undoPoint);
    $("#redoAction").addEventListener("click", redoHistory);
    $("#deleteObject").addEventListener("click", deleteSelected);
    $("#clearDraft").addEventListener("click", clearDraft);
    $("#canvasZoomOut").addEventListener("click", () => setCanvasZoom(state.canvasZoom / CANVAS_BUTTON_ZOOM_FACTOR));
    $("#canvasZoomReset").addEventListener("click", () => setCanvasZoom(1));
    $("#canvasZoomIn").addEventListener("click", () => setCanvasZoom(state.canvasZoom * CANVAS_BUTTON_ZOOM_FACTOR));
    $("#sketchOverlay").addEventListener("click", addPoint);
    $("#sketchOverlay").addEventListener("dblclick", (event) => {
      event.preventDefault();
      if (canFinishDraft()) finishObject();
    });
    $("#workbenchCanvas").addEventListener("wheel", handleCanvasWheel, { passive: false });
    document.addEventListener("keydown", handleShortcuts);
    // arc drag: one-time document-level pointer handlers (survive re-render)
    document.addEventListener("pointermove", (event) => {
      if (state.vertexDrag) {
        updateVertexDrag(event);
        return;
      }
      if (state.moveDrag && !state.arcDrag) {
        updateMoveDrag(event);
        return;
      }
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
      if (state.vertexDrag) {
        state.vertexDrag = null;
        markDirty();
        refreshLegendPreview();
        return;
      }
      if (state.moveDrag) {
        finishMoveDrag();
        return;
      }
      if (!state.arcDrag) return;
      state.arcDrag = null;
      markDirty();
      refreshLegendPreview();
    });
    document.addEventListener("pointercancel", () => {
      state.vertexDrag = null;
      state.arcDrag = null;
      state.moveDrag = null;
    });
    if (window.ResizeObserver) {
      const stage = $("#workbenchStage");
      if (stage) {
        const observer = new ResizeObserver(() => renderCanvasLayers("stage-resize"));
        observer.observe(stage);
      }
    }
    // Footer toggle (collapsible workflow bar)
    const footerEl = $("#workbenchFooter");
    const footerToggleEl = $("#footerToggle");
    if (footerEl && footerToggleEl) {
      footerToggleEl.addEventListener("click", () => {
        footerEl.classList.toggle("open");
      });
    }

    // Rail collapse toggles
    function setRailCollapsed(side, collapsed) {
      const layout = $("#workbenchLayout");
      if (!layout) return;
      layout.classList.toggle(`${side}-collapsed`, collapsed);
      const btn = side === "left" ? $("#toggleLeftRail") : $("#toggleRightRail");
      if (btn) btn.setAttribute("aria-pressed", String(!collapsed));
    }
    $("#toggleLeftRail")?.addEventListener("click", () => {
      setRailCollapsed("left", !$("#workbenchLayout").classList.contains("left-collapsed"));
    });
    $("#toggleRightRail")?.addEventListener("click", () => {
      setRailCollapsed("right", !$("#workbenchLayout").classList.contains("right-collapsed"));
    });
    // Default: left open, right collapsed (give canvas more room on load)
    setRailCollapsed("left", false);
    setRailCollapsed("right", true);

    // v3 inspector accordion
    document.querySelectorAll(".wb3-sect-h").forEach((h) => {
      h.addEventListener("click", () => h.parentElement.classList.toggle("open"));
    });
    // v3 inspector collapse
    const inspBtn = $("#toggleInspector");
    if (inspBtn) {
      inspBtn.addEventListener("click", () => {
        const work = $("#workbenchLayout");
        if (!work) return;
        const collapsed = work.classList.toggle("insp-collapsed");
        inspBtn.classList.toggle("on", !collapsed);
      });
    }

    // Base image popover
    const basePanelBtn = $("#toggleBasePanel");
    const basePanel = $("#basePanel");
    if (basePanelBtn && basePanel) {
      basePanelBtn.addEventListener("click", (event) => {
        event.stopPropagation();
        const open = basePanel.hidden;
        basePanel.hidden = !open;
        basePanelBtn.setAttribute("aria-expanded", String(open));
      });
      document.addEventListener("click", (event) => {
        if (basePanel.hidden) return;
        if (!basePanel.contains(event.target) && event.target !== basePanelBtn) {
          basePanel.hidden = true;
          basePanelBtn.setAttribute("aria-expanded", "false");
        }
      });
    }

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

  window.DrawingWorkbenchTest = {
    createObject(toolId, points) {
      if (!supportsTool(toolId) || toolId === "supporting_images") {
        throw new Error(`Unsupported drawing tool: ${toolId}`);
      }
      state.activeTool = toolId;
      const object = createObjectFromTool(toolId, points || []);
      if (!object) throw new Error(`Failed to create object for tool: ${toolId}`);
      return JSON.parse(JSON.stringify(object));
    },
    getObjects() {
      return JSON.parse(JSON.stringify(state.objects));
    },
    getActiveDrawingType() {
      return drawingType();
    },
    async reloadStylePresets() {
      await loadStylePresets();
      renderDrawingWorkspace();
      return JSON.parse(JSON.stringify(state.stylePresets || []));
    },
  };

  bind();
})();
