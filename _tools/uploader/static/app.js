const state = {
  project: "",
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
  if (!state.project) throw new Error("请先完成第 1 步：创建或选择项目");
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

function setControls() {
  const hasProject = Boolean(state.project);
  $("#activeProject").textContent = hasProject ? `当前项目：${state.project}` : "未选择项目";
  $("#projectHint").textContent = hasProject
    ? `已打开 ${state.project}。现在可以上传资料。`
    : "请先创建新项目，或从下方已有项目中选择一个。";
  $("#uploadHint").textContent = hasProject
    ? "选择文件后还没有上传，必须点击对应卡片里的“上传到当前项目”。"
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
  const list = $("#projectList");
  list.innerHTML = "";
  if (!data.projects.length) {
    const empty = document.createElement("div");
    empty.className = "empty-projects";
    empty.textContent = "还没有项目。请填写上方信息并点击“创建/打开项目”。";
    list.appendChild(empty);
    setControls();
    return;
  }
  data.projects.forEach((project) => {
    const chip = document.createElement("button");
    chip.className = `project-chip ${project.code === state.project ? "active" : ""}`;
    chip.textContent = project.code;
    chip.addEventListener("click", () => {
      state.project = project.code;
      state.inventory = null;
      $("#projectCode").value = project.code;
      clearFileInputs();
      setControls();
      loadProjects();
      runInventory();
    });
    list.appendChild(chip);
  });
  setControls();
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
  state.project = code;
  state.inventory = null;
  clearFileInputs();
  writeOutput(data);
  await loadProjects();
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
      state.project = "";
      state.inventory = null;
      clearFileInputs();
      setControls();
      loadProjects().catch((err) => writeOutput(err.message));
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
