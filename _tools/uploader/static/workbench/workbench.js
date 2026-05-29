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
  ];
  const SOURCE_OPTIONS = [
    { value: "user_sketch", label: "用户手绘" },
    { value: "vision_inferred", label: "视觉识别" },
    { value: "cad_extracted", label: "CAD 提取" },
  ];
  const GEOMETRY_LABELS = {
    path: "路径",
    circle: "圆形",
    triangle: "三角形",
    point: "点位",
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
  };
  const SPECIAL_TOOL_TYPES = new Set(["turning_radius", "elevation_marker", "slope_arrow"]);
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
    supporting_images: "配图",
  };

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
    const tools = drawingTools(type);
    if (tools.includes(state.activeTool)) return state.activeTool;
    state.activeTool = tools[0] || "";
    return state.activeTool;
  }

  function toolObjectTypes(toolId = normalizeActiveTool()) {
    const objectTypes = drawingConfig().objectTypes || [];
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
    if (!supportsTool(toolId) || toolId === "supporting_images") return;
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

  function draftKey(toolId, objectType) {
    return `${drawingType()}|${toolId || ""}|${objectType || ""}`;
  }

  function draftStyleFor(objectType, toolId = normalizeActiveTool()) {
    const key = draftKey(toolId, objectType);
    const selected = selectedObject();
    if (!isFunctionalZoning() && selected && selected.type === objectType) {
      return Model.cloneStyle(Model.normalizeStyleHints(selected.style_hints, objectType));
    }
    if (state.styleDrafts[key]) return Model.cloneStyle(state.styleDrafts[key]);
    if (state.lastStyles[objectType]) return Model.cloneStyle(state.lastStyles[objectType]);
    return Model.defaultStyleForObjectType(objectType);
  }

  function draftGeometryFor(objectType, toolId = normalizeActiveTool()) {
    const key = draftKey(toolId, objectType);
    const defaults = { radius: 0.035, size: 0.055, rotation_deg: 0 };
    return {
      ...defaults,
      ...(state.lastGeometry[objectType] || {}),
      ...(state.geometryDrafts[key] || {}),
    };
  }

  function captureObjectDefaults(obj, toolId = normalizeActiveTool()) {
    if (!obj || !obj.type) return;
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
    if (isFunctionalZoning()) {
      renderFunctionalZoningTools(tools);
      return;
    }
    renderRegistryTools(tools, config);
    return;
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

  function renderRegistryTools(tools, config) {
    const rawTools = config.tools || [];
    const activeTool = normalizeActiveTool();
    const objectTypes = toolObjectTypes(activeTool);
    const selectedObject = selectedToolObjectType(activeTool);
    tools.innerHTML = `
      <div class="zone-tool-group drawing-tool-picker" data-workbench-tool-picker="true">
        <span>绘图工具</span>
        <div class="segmented-control tool-grid">
          ${rawTools
            .map(
              (toolId) => `
                <button
                  type="button"
                  class="tool-button ${activeTool === toolId ? "active" : ""}"
                  data-tool-id="${escapeHtml(toolId)}"
                >${escapeHtml(TOOL_LABELS[toolId] || toolId)}</button>
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
              <select id="objectType">${optionHtml(objectTypes, selectedObject)}</select>
            </label>
            <label>
              <span>标签文本</span>
              <input id="objectLabel" placeholder="例如：主入口 / 景观节点 / R=9M">
            </label>
            <label>
              <span>来源</span>
              <select id="objectSource">${optionHtml(SOURCE_OPTIONS, "user_sketch")}</select>
            </label>
            ${renderRegistryStyleControls(activeTool, selectedObject)}
          `
      }
      ${rawTools.includes("supporting_images") ? renderSupportingPanel() : ""}
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
    bindRegistryStyleControls(activeTool, selectedObject);
    bindSupportingPanel();
  }

  function renderRegistryStyleControls(toolId, objectType) {
    const style = draftStyleFor(objectType, toolId);
    const geo = draftGeometryFor(objectType, toolId);
    const isPath = ["closed_path", "open_path", "turning_radius", "slope_arrow"].includes(toolId);
    const isClosed = toolId === "closed_path";
    const isCircle = toolId === "circle";
    const isTriangle = toolId === "triangle" || toolId === "elevation_marker";
    const hasFill = isClosed || isCircle || isTriangle;
    const hasLabelBox = toolId === "turning_radius" || toolId === "elevation_marker";
    const hasInline = toolId === "slope_arrow";
    return `
      <div class="style-controls" data-style-controls="true">
        ${
          hasFill
            ? `
              <label><span>填充模式</span><select id="styleFillMode">
                ${optionHtml(
                  [
                    { value: "none", label: "无填充" },
                    { value: "translucent", label: "半透明" },
                    { value: "solid", label: "实心" },
                    { value: "hatch", label: "斜线" },
                  ],
                  style.fill_mode || "none",
                )}
              </select></label>
              <label><span>填充色</span><input id="styleFillColor" type="color" value="${escapeHtml(style.fill_color || "#DCE8C8")}"></label>
              <label><span>不透明度</span><input id="styleFillOpacity" type="range" min="0.1" max="1" step="0.05" value="${escapeHtml(String(style.fill_opacity || 0.42))}"></label>
              <label><span>斜线角度</span><input id="styleHatchAngle" type="number" min="0" max="180" step="5" value="${escapeHtml(String(style.hatch_angle_deg || 45))}"></label>
              <label><span>斜线间距</span><input id="styleHatchSpacing" type="number" min="0.006" max="0.06" step="0.002" value="${escapeHtml(String(style.hatch_spacing || 0.018))}"></label>
            `
            : ""
        }
        ${
          isPath || hasFill
            ? `
              <label><span>线/边框颜色</span><input id="styleStrokeColor" type="color" value="${escapeHtml(style.stroke_color || "#333333")}"></label>
              <label><span>线/边框宽度</span><input id="styleStrokeWidth" type="range" min="0.001" max="0.018" step="0.001" value="${escapeHtml(String(style.stroke_width || 0.003))}"></label>
              <label><span>线型</span><select id="styleStrokeStyle">
                ${optionHtml(
                  [
                    { value: "solid", label: "实线" },
                    { value: "dashed", label: "虚线" },
                  ],
                  style.stroke_style || "solid",
                )}
              </select></label>
            `
            : ""
        }
        ${
          hasFill
            ? `
              <label><span>边框</span><select id="styleBorderStyle">
                ${optionHtml(
                  [
                    { value: "none", label: "无边框" },
                    { value: "solid", label: "单实线" },
                    { value: "dashed", label: "虚线" },
                    { value: "double", label: "双实线" },
                  ],
                  style.border_style || "solid",
                )}
              </select></label>
              <label><span>双线间距</span><input id="styleDoubleGap" type="number" min="0.002" max="0.03" step="0.001" value="${escapeHtml(String(style.double_border_gap || 0.006))}"></label>
            `
            : ""
        }
        ${
          isPath
            ? `
              <label class="checkbox-line"><input id="styleStartArrow" type="checkbox" ${style.start_arrow ? "checked" : ""}> 起点箭头</label>
              <label class="checkbox-line"><input id="styleEndArrow" type="checkbox" ${style.end_arrow ? "checked" : ""}> 终点箭头</label>
              <label><span>箭头尺寸</span><input id="styleArrowSize" type="range" min="0.012" max="0.07" step="0.002" value="${escapeHtml(String(style.arrow_size || 0.028))}"></label>
            `
            : ""
        }
        ${isCircle ? `<label><span>圆半径</span><input id="geometryRadius" type="range" min="0.012" max="0.12" step="0.002" value="${escapeHtml(String(geo.radius))}"></label>` : ""}
        ${
          isTriangle
            ? `
              <label><span>三角尺寸</span><input id="geometrySize" type="range" min="0.025" max="0.13" step="0.002" value="${escapeHtml(String(geo.size))}"></label>
              <label><span>旋转角度</span><input id="geometryRotation" type="range" min="0" max="360" step="5" value="${escapeHtml(String(geo.rotation_deg))}"></label>
            `
            : ""
        }
        ${
          hasLabelBox
            ? `
              <label><span>标注文本</span><input id="labelBoxText" value="${escapeHtml((style.label_box && style.label_box.text) || (toolId === "turning_radius" ? "R=9M" : ""))}"></label>
              <label><span>标注框宽</span><input id="labelBoxWidth" type="range" min="0.05" max="0.22" step="0.005" value="${escapeHtml(String((style.label_box && style.label_box.width) || 0.09))}"></label>
              <label><span>标注框高</span><input id="labelBoxHeight" type="range" min="0.025" max="0.09" step="0.005" value="${escapeHtml(String((style.label_box && style.label_box.height) || 0.035))}"></label>
              <label><span>标注字号</span><input id="labelBoxFontSize" type="range" min="0.012" max="0.04" step="0.002" value="${escapeHtml(String((style.label_box && style.label_box.font_size) || 0.018))}"></label>
              <label><span>标注透明度</span><input id="labelBoxOpacity" type="range" min="0.08" max="0.45" step="0.02" value="${escapeHtml(String((style.label_box && style.label_box.opacity) || 0.18))}"></label>
            `
            : ""
        }
        ${
          hasInline
            ? `
              <label><span>坡度文本</span><input id="inlineText" value="${escapeHtml((style.inline_text && style.inline_text.text) || "0.3%")}"></label>
              <label><span>坡度字号</span><input id="inlineTextFontSize" type="range" min="0.012" max="0.04" step="0.002" value="${escapeHtml(String((style.inline_text && style.inline_text.font_size) || 0.018))}"></label>
              <label><span>文本位置</span><input id="inlineTextPosition" type="range" min="0.15" max="0.85" step="0.05" value="${escapeHtml(String((style.inline_text && style.inline_text.position) || 0.5))}"></label>
            `
            : ""
        }
      </div>
    `;
  }

  function bindRegistryStyleControls(toolId, objectType) {
    const styleMap = {
      styleFillMode: ["fill_mode", "string"],
      styleFillColor: ["fill_color", "string"],
      styleFillOpacity: ["fill_opacity", "number"],
      styleHatchAngle: ["hatch_angle_deg", "number"],
      styleHatchSpacing: ["hatch_spacing", "number"],
      styleStrokeColor: ["stroke_color", "string"],
      styleStrokeWidth: ["stroke_width", "number"],
      styleStrokeStyle: ["stroke_style", "string"],
      styleBorderStyle: ["border_style", "string"],
      styleDoubleGap: ["double_border_gap", "number"],
      styleStartArrow: ["start_arrow", "boolean"],
      styleEndArrow: ["end_arrow", "boolean"],
      styleArrowSize: ["arrow_size", "number"],
    };
    Object.entries(styleMap).forEach(([id, [key, kind]]) => {
      const el = $(`#${id}`);
      if (!el) return;
      el.addEventListener("input", () => {
        const value = kind === "boolean" ? el.checked : kind === "number" ? Number(el.value) : el.value;
        updateActiveStyle(toolId, objectType, { [key]: value });
      });
    });
    const nestedMap = {
      labelBoxText: ["label_box", "text", "string"],
      labelBoxWidth: ["label_box", "width", "number"],
      labelBoxHeight: ["label_box", "height", "number"],
      labelBoxFontSize: ["label_box", "font_size", "number"],
      labelBoxOpacity: ["label_box", "opacity", "number"],
      inlineText: ["inline_text", "text", "string"],
      inlineTextFontSize: ["inline_text", "font_size", "number"],
      inlineTextPosition: ["inline_text", "position", "number"],
    };
    Object.entries(nestedMap).forEach(([id, [group, key, kind]]) => {
      const el = $(`#${id}`);
      if (!el) return;
      el.addEventListener("input", () => {
        const value = kind === "number" ? Number(el.value) : el.value;
        const current = draftStyleFor(objectType, toolId);
        updateActiveStyle(toolId, objectType, { [group]: { ...(current[group] || {}), enabled: true, [key]: value } });
      });
    });
    const geometryMap = {
      geometryRadius: ["radius", "number"],
      geometrySize: ["size", "number"],
      geometryRotation: ["rotation_deg", "number"],
    };
    Object.entries(geometryMap).forEach(([id, [key]]) => {
      const el = $(`#${id}`);
      if (!el) return;
      el.addEventListener("input", () => updateActiveGeometry(toolId, objectType, { [key]: Number(el.value) }));
    });
  }

  function updateActiveStyle(toolId, objectType, patch) {
    const key = draftKey(toolId, objectType);
    const current = draftStyleFor(objectType, toolId);
    const next = Model.normalizeStyleHints({ ...current, ...patch }, objectType);
    state.styleDrafts[key] = Model.cloneStyle(next);
    state.lastStyles[objectType] = Model.cloneStyle(next);
    const selected = selectedObject();
    if (selected && selected.type === objectType && !isFunctionalZoning()) {
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
    if (!selected || selected.type !== objectType || isFunctionalZoning()) return;
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
    `;
    // Move legend preview to right rail if container exists
    const legendContainer = $("#zoneLegendPreview");
    if (legendContainer) {
      legendContainer.innerHTML = renderFunctionalZoneLegendPreview();
    }
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
    container.innerHTML = renderFunctionalZoneLegendPreview();
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
    ].forEach((selector) => {
      const el = $(selector);
      if (el) el.disabled = !enabled || (selector === "#exportDrawing" && !state.svgExists);
    });
    const notes = $("#taskUserNotes");
    if (notes) notes.placeholder = drawingConfig().agentNotesPlaceholder || "";
    const send = $("#sendToAgent");
    if (send) send.textContent = drawingConfig().taskButtonLabel || "发给 agent 出图";
    const finish = $("#finishObject");
    if (finish) finish.textContent = isFunctionalZoning() ? "完成分区" : "完成" + (TOOL_LABELS[normalizeActiveTool()] || "对象");
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

  function objectStyle(type, rawStyle = {}) {
    const style = Model.normalizeStyleHints(rawStyle, type);
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
    if (isFunctionalZoning()) {
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
    loadSupportingImages(drawingType()).catch((err) => setStatus(err.message, false));
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
      .filter((obj) => !isFunctionalZoning() || (obj.type === "functional_zone" && obj.geometry && (obj.geometry.kind === "polygon" || (obj.geometry.kind === "path" && obj.geometry.closed === true))))
      .map((obj) => {
        if (isFunctionalZoning()) {
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
    const objectSource = $("#objectSource");
    const index = state.objects.length + 1;
    const id = options.id || nextObjectId();
    const label = options.label || (objectLabel && objectLabel.value.trim()) || `${objectName(objectType)} ${index}`;
    const geometry = defaultGeometryForTool(toolId, points.slice(0, minPoints), objectType);
    if (!geometry) return null;
    const style = draftStyleFor(objectType, toolId);
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
    const object = {
      id,
      type: objectType,
      geometry,
      label,
      confidence: "medium",
      source: options.source || (objectSource && objectSource.value) || "user_sketch",
      style_hints: style,
    };
    state.objects.push(object);
    captureObjectDefaults(object, toolId);
    state.selectedId = id;
    state.currentPoints = [];
    markDirty();
    renderCanvasLayers("create-object-from-tool");
    renderObjectList();
    renderSpecificTools();
    refreshLegendPreview();
    setStatus(`已添加：${label}`);
    return object;
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
    const activeTool = normalizeActiveTool();
    const spec = TOOL_GEOMETRY[activeTool];
    if (!spec) return;
    state.currentPoints.push(point);
    markDirty();
    if (state.currentPoints.length >= (spec.minPoints || 1) && (spec.minPoints || 1) <= 2) {
      createObjectFromTool(activeTool, state.currentPoints);
    } else {
      renderObjects();
    }
  }

  function finishObject() {
    if (!isEnabled()) return;
    if (isFunctionalZoning()) {
      finishFunctionalZone();
      return;
    }
    const activeTool = normalizeActiveTool();
    const spec = TOOL_GEOMETRY[activeTool];
    if (!spec) return;
    if (state.currentPoints.length < (spec.minPoints || 1)) {
      setStatus(`${TOOL_LABELS[activeTool] || activeTool} 至少需要 ${spec.minPoints || 1} 个点。`, false);
      return;
    }
    pushUndoSnapshot();
    createObjectFromTool(activeTool, state.currentPoints);
    return;
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
      geometry: { kind: "path", closed: true, coords: state.currentPoints.slice() },
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
    if (mode === "translucent" || mode === "hatch") {
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

  function renderArrowHead(from, tip, style, objectId) {
    from = safePoint(from);
    tip = safePoint(tip);
    if (!from || !tip) return "";
    const size = Number(style.arrow_size) || 0.028;
    const angle = Math.atan2(tip[1] - from[1], tip[0] - from[0]);
    const back = [Math.cos(angle) * size, Math.sin(angle) * size];
    const side = [-Math.sin(angle) * size * 0.42, Math.cos(angle) * size * 0.42];
    const p1 = tip;
    const p2 = [tip[0] - back[0] + side[0], tip[1] - back[1] + side[1]];
    const p3 = [tip[0] - back[0] - side[0], tip[1] - back[1] - side[1]];
    return `<polygon data-object-id="${escapeHtml(objectId)}" points="${[p1, p2, p3].map((p) => p.join(",")).join(" ")}" fill="${style.stroke_color || "#333333"}"></polygon>`;
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
      parts.push(`<rect data-object-id="${escapeHtml(obj.id)}" x="${x}" y="${y}" width="${width}" height="${height}" rx="0.004" fill="${color}" fill-opacity="${box.opacity || 0.18}" stroke="${color}" stroke-width="0.001"></rect>`);
      if (text) {
        parts.push(`<text x="${x + width * 0.08}" y="${y + height * 0.65}" fill="${color}" font-size="${box.font_size || 0.018}" font-weight="700">${escapeHtml(text)}</text>`);
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
        const x = start[0] + (end[0] - start[0]) * position + Number(offset[0] || 0);
        const y = start[1] + (end[1] - start[1]) * position + Number(offset[1] || 0);
        const angle = Model.lineAngleDeg(coords);
        parts.push(`<text x="${x}" y="${y}" transform="rotate(${angle} ${x} ${y})" fill="${style.stroke_color || "#333333"}" font-size="${inline.font_size || 0.018}" font-weight="700">${escapeHtml(inline.text || obj.label || "")}</text>`);
      }
    }
    return parts.join("");
  }

  function objectAnchorPoint(obj) {
    const geo = (obj && obj.geometry) || {};
    if (geo.kind === "circle" || geo.kind === "triangle") return safePoint(geo.center);
    const coords = objectPathCoords(obj);
    return coords[Math.floor(coords.length / 2)] || null;
  }

  function objectPathCoords(obj) {
    const geo = (obj && obj.geometry) || {};
    if (Array.isArray(geo.segments) && geo.segments.length) return Model.sampleSegments(geo.segments, !!geo.closed);
    return Array.isArray(geo.coords) ? geo.coords.map(safePoint).filter(Boolean) : [];
  }

  function renderObjectSvg(obj) {
    if (isFunctionalZoning() && obj.type === "functional_zone") {
      return renderFunctionalZoneSvg(obj);
    }
    const style = objectStyle(obj.type, obj.style_hints);
    const selected = obj.id === state.selectedId;
    const width = selected ? 0.012 : 0.008;
    const geo = obj.geometry;
    let shape = "";
    let labelPoint = [0.5, 0.5];

    if (geo.kind === "circle") {
      const center = safePoint(geo.center) || safePoint((geo.coords || [])[0]) || [0.5, 0.5];
      const cx = center[0], cy = center[1], r = Number(geo.radius) > 0 ? Number(geo.radius) : 0.035;
      const fill = (obj.style_hints && obj.style_hints.fill_mode === "solid") ? (obj.style_hints.fill_color || style.fill) :
                   (obj.style_hints && (obj.style_hints.fill_mode === "translucent" || obj.style_hints.fill_mode === "hatch")) ? (obj.style_hints.fill_color || style.fill) : "none";
      const fillOpacity = (obj.style_hints && obj.style_hints.fill_mode === "translucent") ? "0.42" : "1";
      const stroke = (obj.style_hints && obj.style_hints.stroke_color) || style.stroke;
      const borderW = (obj.style_hints && obj.style_hints.stroke_width) || 0.003;
      const dash = (style.hints.stroke_style === "dashed" || style.hints.border_style === "dashed") ? ' stroke-dasharray="0.014 0.01"' : "";
      shape = `<circle data-object-id="${escapeHtml(obj.id)}" cx="${cx}" cy="${cy}" r="${r}" fill="${fill}" fill-opacity="${fillOpacity}" stroke="${stroke}" stroke-width="${borderW}"${dash}></circle>`;
      if (style.hints.border_style === "double") {
        const innerR = Math.max(0.004, r - (style.hints.double_border_gap || 0.006));
        shape += `<circle data-object-id="${escapeHtml(obj.id)}" cx="${cx}" cy="${cy}" r="${innerR}" fill="none" stroke="${stroke}" stroke-width="${borderW}"></circle>`;
      }
      labelPoint = [cx, cy - r];
    } else if (geo.kind === "triangle") {
      const center = safePoint(geo.center) || safePoint((geo.coords || [])[0]) || [0.5, 0.5];
      const cx = center[0], cy = center[1];
      const size = geo.size || 0.055;
      const rot = geo.rotation_deg || 0;
      const pts = Model.trianglePoints([cx, cy], size, rot);
      const points = pts.map(p => p.join(",")).join(" ");
      const fill = (obj.style_hints && obj.style_hints.fill_mode === "solid") ? (obj.style_hints.fill_color || style.fill) :
                   (obj.style_hints && obj.style_hints.fill_mode === "translucent") ? (obj.style_hints.fill_color || style.fill) : "none";
      const stroke = (obj.style_hints && obj.style_hints.stroke_color) || style.stroke;
      const dash = (style.hints.stroke_style === "dashed" || style.hints.border_style === "dashed") ? ' stroke-dasharray="0.014 0.01"' : "";
      shape = `<polygon data-object-id="${escapeHtml(obj.id)}" points="${points}" fill="${fill}" stroke="${stroke}" stroke-width="${width}"${dash}></polygon>`;
      if (style.hints.border_style === "double") {
        const innerPts = Model.trianglePoints([cx, cy], Math.max(0.01, size - (style.hints.double_border_gap || 0.006)), rot);
        shape += `<polygon data-object-id="${escapeHtml(obj.id)}" points="${innerPts.map(p => p.join(",")).join(" ")}" fill="none" stroke="${stroke}" stroke-width="${width}"></polygon>`;
      }
      labelPoint = [cx, cy - size];
    } else if (geo.kind === "path" && geo.closed) {
      // Closed path (polygon)
      const closedCoords = objectPathCoords(obj);
      if (closedCoords.length < 3) return "";
      const segments = geo.segments;
      if (segments && segments.length > 0) {
        const pathD = segmentsToPathD(segments, true);
        const fill = pathFillValue(obj, style);
        const dash = (style.hints.stroke_style === "dashed" || style.hints.border_style === "dashed") ? ' stroke-dasharray="0.014 0.01"' : "";
        shape = `<path data-object-id="${escapeHtml(obj.id)}" d="${pathD}" fill="${fill.color}" fill-opacity="${fill.opacity}" stroke="${style.stroke}" stroke-width="${width}" stroke-linejoin="round"${dash}></path>`;
        if (style.hints.border_style === "double") {
          shape += `<path data-object-id="${escapeHtml(obj.id)}" d="${pathD}" fill="none" stroke="${style.stroke}" stroke-width="${Math.max(0.001, width - (style.hints.double_border_gap || 0.006) / 2)}" stroke-linejoin="round"></path>`;
        }
      } else {
        const points = closedCoords.map(p => p.join(",")).join(" ");
        const fill = pathFillValue(obj, style);
        const dash = (style.hints.stroke_style === "dashed" || style.hints.border_style === "dashed") ? ' stroke-dasharray="0.014 0.01"' : "";
        shape = `<polygon data-object-id="${escapeHtml(obj.id)}" points="${points}" fill="${fill.color}" fill-opacity="${fill.opacity}" stroke="${style.stroke}" stroke-width="${width}"${dash}></polygon>`;
        if (style.hints.border_style === "double") {
          shape += `<polygon data-object-id="${escapeHtml(obj.id)}" points="${points}" fill="none" stroke="${style.stroke}" stroke-width="${Math.max(0.001, width - (style.hints.double_border_gap || 0.006) / 2)}"></polygon>`;
        }
      }
      if (selected) shape += renderSegmentHandles(obj.id, ensureSegments(obj), { fill_color: style.stroke });
      labelPoint = closedCoords[Math.floor(closedCoords.length / 2)] || closedCoords[0];
    } else if (geo.kind === "point") {
      const [x, y] = safePoint((geo.coords || [])[0]) || [0.5, 0.5];
      shape = `<circle data-object-id="${escapeHtml(obj.id)}" cx="${x}" cy="${y}" r="0.012" fill="${style.stroke}" stroke="#fff" stroke-width="0.004"></circle>`;
      labelPoint = [x, y];
    } else {
      // Open path (polyline/arrow/line)
      const coords = objectPathCoords(obj);
      const segments = geo.segments;
      if (segments && segments.length > 0) {
        const pathD = segmentsToPathD(segments, false);
        const dash = style.hints.stroke_style === "dashed" ? ' stroke-dasharray="0.014 0.01"' : "";
        shape = `<path data-object-id="${escapeHtml(obj.id)}" d="${pathD}" fill="none" stroke="${style.stroke}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round"${dash}></path>`;
      } else if (coords.length >= 2) {
        const points = coords.map(p => p.join(",")).join(" ");
        const dash = style.hints.stroke_style === "dashed" ? ' stroke-dasharray="0.014 0.01"' : "";
        shape = `<polyline data-object-id="${escapeHtml(obj.id)}" points="${points}" fill="none" stroke="${style.stroke}" stroke-width="${width}" stroke-linecap="round" stroke-linejoin="round"${dash}></polyline>`;
      }
      shape += renderArrowHeads(coords, style.hints, obj.id);
      if (selected && coords.length >= 2) shape += renderSegmentHandles(obj.id, ensureSegments(obj), { fill_color: style.stroke });
      if (coords.length) labelPoint = coords[Math.floor(coords.length / 2)] || coords[0];
    }
    const overlays = renderSemanticTextOverlays(obj, labelPoint, style.hints);
    const plainLabel = style.hints.label_box && style.hints.label_box.enabled ? "" : style.hints.inline_text && style.hints.inline_text.enabled ? "" : renderSvgLabel(obj.label, labelPoint, style.stroke);
    return `${shape}${overlays}${plainLabel}`;
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


  function selectObject(id) {
    state.selectedId = id || "";
    state.currentPoints = [];
    if (!isFunctionalZoning()) captureObjectDefaults(selectedObject());
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

  async function bind() {
    if (!$("#drawingWorkbench")) return;
    // Load registry first, then render
    await loadRegistry();
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
    $("#canvasZoomOut").addEventListener("click", () => setCanvasZoom(state.canvasZoom / CANVAS_BUTTON_ZOOM_FACTOR));
    $("#canvasZoomReset").addEventListener("click", () => setCanvasZoom(1));
    $("#canvasZoomIn").addEventListener("click", () => setCanvasZoom(state.canvasZoom * CANVAS_BUTTON_ZOOM_FACTOR));
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
  };

  bind();
})();
