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
  const DRAWING_WORKBENCHES = {
    functional_zoning: {
      status: "enabled",
      category: "analysis_a",
      label: "功能分区",
      title: "功能分区工作台",
      description: "标注功能区边界、功能名称和必要标签，保存为后续精绘分区图的语义证据。",
      objectTypes: [
        { value: "functional_zone", label: "功能区", defaultGeometry: "polygon" },
        { value: "label", label: "标签", defaultGeometry: "point" },
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

  function renderAvailability() {
    const enabled = isEnabled();
    const layout = $("#workbenchLayout");
    if (layout) layout.hidden = !enabled;
    [
      "#workbenchSave",
      "#finishObject",
      "#undoPoint",
      "#deleteObject",
      "#clearDraft",
      "#sendToAgent",
      "#exportDrawing",
    ].forEach((selector) => {
      const el = $(selector);
      if (el) el.disabled = !enabled || (selector === "#exportDrawing" && !state.svgExists);
    });
    const notes = $("#taskUserNotes");
    if (notes) notes.placeholder = drawingConfig().agentNotesPlaceholder || "";
    const send = $("#sendToAgent");
    if (send) send.textContent = drawingConfig().taskButtonLabel || "发给 agent 出图";
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
    resetInteraction();
    state.svgExists = !!data.svg_exists;
    state.svgUrl = data.svg_url || "";
    clearDirty();
    const pathInput = $("#baseImagePath");
    if (pathInput) pathInput.value = data.drawing.base_image.path || basePath();
    const hasBaseImage = loadBaseImage(data.base_image_url, data.base_image_exists);
    renderSvgDraft();
    loadStyle().catch((err) => renderStyleStrip(null, err.message));
    renderObjects();
    renderObjectList();
    renderAvailability();
    if (hasBaseImage) {
      setStatus(data.exists ? "已加载已保存的草图。" : "已初始化空白草图。");
    }
  }

  function loadBaseImage(url, exists) {
    const image = $("#baseImage");
    const empty = $("#workbenchEmpty");
    if (!image || !empty) return false;
    console.log("[workbench] loadBaseImage", { url, exists });
    if (!exists || !url) {
      image.removeAttribute("src");
      state.loadedBaseUrl = "";
      empty.hidden = false;
      empty.textContent = "未找到底图。请上传 JPG/PNG，或填写 05_output/drawings/base/ 下的底图路径。";
      setStatus("底图不存在，请先上传底图或填写已存在的底图路径。", false);
      return false;
    }
    state.loadedBaseUrl = `${url}&_=${Date.now()}`;
    image.onload = () => {
      setStatus(`底图已加载 ${image.naturalWidth}×${image.naturalHeight}。`);
      console.log("[workbench] base image loaded", image.naturalWidth, image.naturalHeight);
    };
    image.onerror = () => {
      setStatus(`底图加载失败：${state.loadedBaseUrl}`, false);
      console.error("[workbench] base image error", state.loadedBaseUrl);
    };
    image.src = state.loadedBaseUrl;
    empty.hidden = true;
    return true;
  }

  function buildDrawing() {
    const image = $("#baseImage");
    const naturalWidth = (image && image.naturalWidth) || (state.drawing && state.drawing.base_image.natural_width) || 1;
    const naturalHeight =
      (image && image.naturalHeight) || (state.drawing && state.drawing.base_image.natural_height) || 1;
    return {
      schema_version: "1.0",
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
      objects: state.objects.map((obj) => ({
        id: obj.id,
        type: obj.type,
        geometry: obj.geometry,
        label: obj.label || "",
        confidence: obj.confidence || "medium",
        source: obj.source || "user_sketch",
        style_hints: {},
      })),
    };
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
    if (!image || !image.src || !image.naturalWidth || !isEnabled()) return null;
    const rect = image.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    if (x < 0 || x > 1 || y < 0 || y > 1) return null;
    return [Number(x.toFixed(6)), Number(y.toFixed(6))];
  }

  function addPoint(event) {
    const point = normalizedPoint(event);
    if (!point) return;
    const geometryKind = $("#geometryKind");
    if (!geometryKind) return;
    state.currentPoints.push(point);
    markDirty();
    if (geometryKind.value === "point") finishObject();
    else renderObjects();
  }

  function finishObject() {
    if (!isEnabled()) return;
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
    const index = state.objects.length + 1;
    const id = `obj-${String(index).padStart(3, "0")}`;
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
    renderObjects();
    renderObjectList();
    setStatus(`已添加：${label}`);
  }

  function undoPoint() {
    if (!state.currentPoints.length) return;
    state.currentPoints.pop();
    markDirty();
    renderObjects();
  }

  function deleteSelected() {
    if (!state.selectedId) return;
    state.objects = state.objects.filter((obj) => obj.id !== state.selectedId);
    state.selectedId = "";
    markDirty();
    renderObjects();
    renderObjectList();
    setStatus("已删除选中对象。");
  }

  function clearDraft() {
    if (!state.objects.length && !state.currentPoints.length) return;
    state.objects = [];
    state.currentPoints = [];
    state.selectedId = "";
    markDirty();
    renderObjects();
    renderObjectList();
    setStatus("已清空当前草图。");
  }

  function renderObjects() {
    const overlay = $("#sketchOverlay");
    if (!overlay) return;
    overlay.innerHTML = [...state.objects.map(renderObjectSvg), renderDraftSvg()].join("");
  }

  function renderObjectSvg(obj) {
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

  function renderDraftSvg() {
    if (!state.currentPoints.length) return "";
    const points = state.currentPoints.map((point) => point.join(",")).join(" ");
    const circles = state.currentPoints
      .map(([x, y]) => `<circle cx="${x}" cy="${y}" r="0.009" fill="#111827"></circle>`)
      .join("");
    return `<polyline points="${points}" fill="none" stroke="#111827" stroke-width="0.006" stroke-dasharray="0.014 0.012"></polyline>${circles}`;
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
        state.selectedId = button.dataset.objectId;
        renderObjects();
        renderObjectList();
      });
    });
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
    $("#deleteObject").addEventListener("click", deleteSelected);
    $("#clearDraft").addEventListener("click", clearDraft);
    $("#workbenchCanvas").addEventListener("click", addPoint);
    $("#workbenchCanvas").addEventListener("dblclick", (event) => {
      event.preventDefault();
      finishObject();
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
