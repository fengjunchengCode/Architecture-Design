(function () {
  const state = {
    project: "",
    drawing: null,
    objects: [],
    currentPoints: [],
    selectedId: "",
    loadedBaseUrl: "",
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

  function projectCode() {
    const appProject =
      window.architectureUploader && window.architectureUploader.getProject
        ? window.architectureUploader.getProject()
        : "";
    return appProject || new URLSearchParams(window.location.search).get("project") || "";
  }

  function setStatus(message, ok = true) {
    const el = $("#workbenchStatus");
    if (!el) return;
    el.textContent = message;
    el.style.color = ok ? "var(--muted)" : "var(--accent-2)";
  }

  function drawingType() {
    return $("#drawingType").value;
  }

  function basePath() {
    return $("#baseImagePath").value.trim() || "05_output/drawings/base/master_plan.jpg";
  }

  function escapeHtml(value) {
    return String(value)
      .replaceAll("&", "&amp;")
      .replaceAll("<", "&lt;")
      .replaceAll(">", "&gt;")
      .replaceAll('"', "&quot;");
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
    return {
      functional_zone: "功能区",
      vehicle_flow: "车行流线",
      pedestrian_flow: "人行流线",
      main_entrance: "主入口",
      label: "标签",
    }[type] || type;
  }

  function geometryName(kind) {
    return { polygon: "多边形", arrow: "箭头", polyline: "折线", point: "点" }[kind] || kind;
  }

  function setDefaultGeometry() {
    const type = $("#objectType").value;
    const next = {
      functional_zone: "polygon",
      vehicle_flow: "arrow",
      pedestrian_flow: "arrow",
      main_entrance: "point",
      label: "point",
    }[type];
    if (next) $("#geometryKind").value = next;
  }

  async function loadDrawing() {
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
    state.currentPoints = [];
    state.selectedId = "";
    $("#baseImagePath").value = data.drawing.base_image.path || basePath();
    const hasBaseImage = loadBaseImage(data.base_image_url, data.base_image_exists);
    renderObjects();
    renderObjectList();
    if (hasBaseImage) {
      setStatus(data.exists ? "已加载已保存的语义图纸。" : "已初始化空白语义图纸。");
    }
  }

  function loadBaseImage(url, exists) {
    const image = $("#baseImage");
    const empty = $("#workbenchEmpty");
    console.log("[workbench] loadBaseImage", { url, exists });
    if (!exists || !url) {
      image.removeAttribute("src");
      state.loadedBaseUrl = "";
      empty.hidden = false;
      empty.textContent = "未找到底图。请把底图放到 05_output/drawings/base/master_plan.jpg。";
      setStatus("底图不存在，请先把 master_plan.jpg 放到 05_output/drawings/base/。", false);
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
    const naturalWidth = image.naturalWidth || (state.drawing && state.drawing.base_image.natural_width) || 1;
    const naturalHeight = image.naturalHeight || (state.drawing && state.drawing.base_image.natural_height) || 1;
    return {
      schema_version: "1.0",
      drawing_type: drawingType(),
      project_code: state.project || projectCode(),
      base_image: {
        path: basePath(),
        natural_width: naturalWidth,
        natural_height: naturalHeight,
        source: "render",
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
    const project = projectCode();
    if (!project) {
      setStatus("请先打开或创建项目，再保存。", false);
      return;
    }
    state.project = project;
    const drawing = buildDrawing();
    const data = await api("/api/drawing/save", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project, drawing }),
    });
    state.drawing = data.drawing;
    setStatus(`已保存：${data.path}`);
  }

  async function renderDrawing() {
    const project = projectCode();
    if (!project) {
      setStatus("请先打开或创建项目，再渲染。", false);
      return;
    }
    state.project = project;
    const drawing = buildDrawing();
    const data = await api("/api/drawing/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project, drawing }),
    });
    state.drawing = drawing;
    const preview = $("#renderPreview");
    preview.innerHTML = `
      <a href="${escapeHtml(data.png_url)}" target="_blank" rel="noreferrer">${escapeHtml(data.paths.png)}</a>
      <img src="${escapeHtml(data.png_url)}&_=${Date.now()}" alt="渲染图">
    `;
    setStatus(`已渲染：${data.paths.png}`);
  }

  function normalizedPoint(event) {
    const image = $("#baseImage");
    if (!image.src || !image.naturalWidth) return null;
    const rect = image.getBoundingClientRect();
    const x = (event.clientX - rect.left) / rect.width;
    const y = (event.clientY - rect.top) / rect.height;
    if (x < 0 || x > 1 || y < 0 || y > 1) return null;
    return [Number(x.toFixed(6)), Number(y.toFixed(6))];
  }

  function addPoint(event) {
    const point = normalizedPoint(event);
    if (!point) return;
    const kind = $("#geometryKind").value;
    state.currentPoints.push(point);
    if (kind === "point") finishObject();
    else renderObjects();
  }

  function finishObject() {
    const kind = $("#geometryKind").value;
    const minimum = { point: 1, polyline: 2, arrow: 2, polygon: 3 }[kind] || 1;
    if (state.currentPoints.length < minimum) {
      setStatus(`${geometryName(kind)} 至少需要 ${minimum} 个点。`, false);
      return;
    }
    const index = state.objects.length + 1;
    const id = `obj-${String(index).padStart(3, "0")}`;
    const label = $("#objectLabel").value.trim() || `${objectName($("#objectType").value)} ${index}`;
    const object = {
      id,
      type: $("#objectType").value,
      geometry: { kind, coords: state.currentPoints.slice() },
      label,
      confidence: "medium",
      source: $("#objectSource").value,
      style_hints: {},
    };
    state.objects.push(object);
    state.selectedId = id;
    state.currentPoints = [];
    renderObjects();
    renderObjectList();
    setStatus(`已添加：${label}`);
  }

  function undoPoint() {
    state.currentPoints.pop();
    renderObjects();
  }

  function deleteSelected() {
    if (!state.selectedId) return;
    state.objects = state.objects.filter((obj) => obj.id !== state.selectedId);
    state.selectedId = "";
    renderObjects();
    renderObjectList();
    setStatus("已删除选中对象。");
  }

  function clearDraft() {
    state.objects = [];
    state.currentPoints = [];
    state.selectedId = "";
    renderObjects();
    renderObjectList();
    setStatus("已清空当前草图。");
  }

  function renderObjects() {
    const overlay = $("#sketchOverlay");
    if (!overlay) return;
    overlay.innerHTML = [
      ...state.objects.map(renderObjectSvg),
      renderDraftSvg(),
    ].join("");
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

  function bind() {
    if (!$("#drawingWorkbench")) return;
    $("#workbenchLoad").addEventListener("click", () => loadDrawing().catch((err) => setStatus(err.message, false)));
    $("#workbenchSave").addEventListener("click", () => saveDrawing().catch((err) => setStatus(err.message, false)));
    $("#workbenchRender").addEventListener("click", () => renderDrawing().catch((err) => setStatus(err.message, false)));
    $("#finishObject").addEventListener("click", finishObject);
    $("#undoPoint").addEventListener("click", undoPoint);
    $("#deleteObject").addEventListener("click", deleteSelected);
    $("#clearDraft").addEventListener("click", clearDraft);
    $("#objectType").addEventListener("change", setDefaultGeometry);
    $("#drawingType").addEventListener("change", () => loadDrawing().catch((err) => setStatus(err.message, false)));
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
        loadDrawing().catch((err) => setStatus(err.message, false));
      }
    });
    setDefaultGeometry();
    renderObjectList();
    state.project = projectCode();
    if (
      state.project &&
      window.architectureUploader &&
      window.architectureUploader.getPage &&
      window.architectureUploader.getPage() === "workbench"
    ) {
      loadDrawing().catch((err) => setStatus(err.message, false));
    }
  }

  bind();
})();
