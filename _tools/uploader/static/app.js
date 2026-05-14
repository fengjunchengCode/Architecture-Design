const state = {
  project: "",
  pendingUrlProject: new URLSearchParams(window.location.search).get("project") || "",
  projects: [],
  inventory: null,
};

const $ = (selector) => document.querySelector(selector);
const output = $("#output");

const BUCKET_LABELS = {
  briefing: "需求类",
  location_map: "区位图",
  topography: "地形图",
  site_photo: "现场照片",
  reference: "参考案例",
  chat: "聊天记录",
};

function writeOutput(data) {
  output.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function typedProjectCode() {
  const code = $("#projectCode").value.trim();
  return code;
}

function activeProject() {
  const typed = typedProjectCode();
  if (!state.project) throw new Error("请先完成第 1 步：创建或选择项目");
  if (typed && typed !== state.project) {
    throw new Error(`当前输入为 ${typed}，但尚未打开该项目。请先点击“创建/打开项目”。`);
  }
  return state.project;
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || data.stderr || "请求失败");
  }
  return data;
}

function setStep(id, mode) {
  const el = $(id);
  el.classList.remove("active", "done", "locked");
  el.classList.add(mode);
}

function clearFileInputs() {
  document.querySelectorAll(".bucket input").forEach((input) => {
    input.value = "";
  });
}

function syncUrlProject(code) {
  const url = new URL(window.location.href);
  if (code) {
    url.searchParams.set("project", code);
  } else {
    url.searchParams.delete("project");
  }
  window.history.replaceState({}, "", url);
}

function renderProjectList() {
  const list = $("#projectList");
  list.innerHTML = "";
  if (!state.projects.length) {
    const empty = document.createElement("div");
    empty.className = "empty-projects";
    empty.textContent = "还没有项目。请填写上方信息并点击“创建/打开项目”。";
    list.appendChild(empty);
    return;
  }
  state.projects.forEach((project) => {
    const chip = document.createElement("button");
    chip.className = `project-chip ${project.code === state.project ? "active" : ""}`;
    chip.textContent = project.code;
    chip.addEventListener("click", () => {
      setActiveProject(project.code);
      runInventory().catch((err) => writeOutput(err.message));
    });
    list.appendChild(chip);
  });
}

function setActiveProject(code, options = {}) {
  const { syncUrl = true, clearFiles = true, resetInventory = true } = options;
  state.project = code;
  if (resetInventory) state.inventory = null;
  if (code) $("#projectCode").value = code;
  if (clearFiles) clearFileInputs();
  if (syncUrl) syncUrlProject(code);
  renderProjectList();
  setControls();
}

function setControls() {
  const typed = typedProjectCode();
  const mismatch = Boolean(state.project && typed && typed !== state.project);
  const hasProject = Boolean(state.project && !mismatch);
  $("#activeProject").textContent = state.project ? `当前项目：${state.project}` : "未选择项目";
  if (mismatch) {
    $("#projectHint").textContent = `当前输入为 ${typed}，但打开的项目仍是 ${state.project}。请先点击“创建/打开项目”。`;
  } else {
    $("#projectHint").textContent = hasProject
      ? `已打开 ${state.project}。上传、Inventory 和 Validate 都会指向这个项目。`
      : "请先创建新项目，或从下方已有项目中选择一个。";
  }
  $("#uploadHint").textContent = hasProject
    ? `选择文件后必须点击对应卡片里的“上传到当前项目”，文件会进入 ${state.project}。`
    : "等待项目创建或选择。上传区已锁定。";

  document.querySelectorAll(".bucket").forEach((bucketEl) => {
    bucketEl.classList.toggle("locked", !hasProject);
    bucketEl.querySelector("input").disabled = !hasProject;
    bucketEl.querySelector("button").disabled = !hasProject;
  });
  $("#runInventory").disabled = !hasProject;
  $("#runValidate").disabled = !hasProject;

  setStep("#stepProject", hasProject ? "done" : "active");
  setStep("#stepUpload", hasProject ? "active" : "locked");
  setStep("#stepCheck", state.inventory ? "active" : hasProject ? "active" : "locked");
  setStep("#stepAgent", state.inventory?.s0_ready ? "active" : "locked");
  updateBucketStates();
}

function updateBucketStates() {
  const counts = state.inventory?.counts || {};
  document.querySelectorAll(".bucket").forEach((bucketEl) => {
    const bucket = bucketEl.dataset.bucket;
    const input = bucketEl.querySelector("input");
    const stateEl = bucketEl.querySelector(".bucket-state");
    const uploaded = counts[bucket] || 0;
    const selected = input.files?.length || 0;
    bucketEl.classList.toggle("has-files", uploaded > 0);
    if (!state.project) {
      stateEl.textContent = "先创建/选择项目";
    } else if (selected > 0) {
      stateEl.textContent = `已选择 ${selected} 个文件，尚未上传`;
    } else if (uploaded > 0) {
      stateEl.textContent = `已入库 ${uploaded} 个文件`;
    } else {
      stateEl.textContent = bucket === "location_map" ? "未上传，S0 会被阻塞" : "未上传";
    }
  });
}

async function loadProjects() {
  const data = await api("/api/projects");
  state.projects = data.projects;
  let shouldRunInventory = false;
  if (state.pendingUrlProject) {
    const requested = state.pendingUrlProject;
    state.pendingUrlProject = "";
    if (state.projects.some((project) => project.code === requested)) {
      state.project = requested;
      $("#projectCode").value = requested;
      state.inventory = null;
      clearFileInputs();
      shouldRunInventory = true;
    } else {
      writeOutput(`URL 中的项目 ${requested} 不存在。请先创建/打开项目。`);
      syncUrlProject("");
    }
  }
  renderProjectList();
  setControls();
  if (shouldRunInventory) await runInventory();
}

async function createProject() {
  const code = typedProjectCode();
  if (!code) throw new Error("请先填写项目代号，例如 26-SZ-NSXX");
  const payload = {
    code,
    name: $("#projectName").value.trim() || code,
    type: $("#projectType").value,
  };
  const data = await api("/api/projects", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  writeOutput(data);
  await loadProjects();
  setActiveProject(code, { clearFiles: true, resetInventory: true });
  await runInventory();
}

async function upload(bucket, input) {
  const code = activeProject();
  if (!input.files.length) throw new Error(`请先在“${BUCKET_LABELS[bucket]}”选择文件，再点击上传`);
  const form = new FormData();
  Array.from(input.files).forEach((file) => form.append("files", file));
  const data = await api(`/api/upload?project=${encodeURIComponent(code)}&bucket=${bucket}`, {
    method: "POST",
    body: form,
  });
  writeOutput(data);
  input.value = "";
  updateBucketStates();
  await runInventory();
}

async function runInventory() {
  const code = activeProject();
  const data = await api(`/api/inventory?project=${encodeURIComponent(code)}`);
  state.inventory = data;
  $("#gateStatus").textContent = data.s0_ready ? "S0 gate 已通过" : "缺少区位图";
  $("#gateStatus").style.color = data.s0_ready ? "#1f6f5b" : "#b94b2f";
  writeOutput(data);
  setControls();
}

async function runValidate() {
  const code = activeProject();
  const data = await api(`/api/validate?project=${encodeURIComponent(code)}`);
  writeOutput(data);
}

function bind() {
  $("#createProject").addEventListener("click", () => createProject().catch((err) => writeOutput(err.message)));
  $("#refreshProjects").addEventListener("click", () => loadProjects().catch((err) => writeOutput(err.message)));
  $("#runInventory").addEventListener("click", () => runInventory().catch((err) => writeOutput(err.message)));
  $("#runValidate").addEventListener("click", () => runValidate().catch((err) => writeOutput(err.message)));
  $("#projectCode").addEventListener("input", () => {
    if ($("#projectCode").value.trim() !== state.project) {
      setActiveProject("", { syncUrl: true, clearFiles: true, resetInventory: true });
      setControls();
    }
  });

  document.querySelectorAll(".bucket").forEach((bucketEl) => {
    const bucket = bucketEl.dataset.bucket;
    const input = bucketEl.querySelector("input");
    const button = bucketEl.querySelector("button");
    input.addEventListener("change", updateBucketStates);
    button.addEventListener("click", () => upload(bucket, input).catch((err) => writeOutput(err.message)));
  });
}

bind();
setControls();
loadProjects().catch((err) => writeOutput(err.message));
