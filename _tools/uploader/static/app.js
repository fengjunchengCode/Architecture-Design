const state = {
  project: "",
};

const $ = (selector) => document.querySelector(selector);
const output = $("#output");

function writeOutput(data) {
  output.textContent = typeof data === "string" ? data : JSON.stringify(data, null, 2);
}

function currentProject() {
  const code = $("#projectCode").value.trim();
  if (!code) throw new Error("请先输入或选择项目代号");
  return code;
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.error || data.stderr || "请求失败");
  }
  return data;
}

async function loadProjects() {
  const data = await api("/api/projects");
  const list = $("#projectList");
  list.innerHTML = "";
  data.projects.forEach((project) => {
    const chip = document.createElement("button");
    chip.className = `project-chip ${project.code === state.project ? "active" : ""}`;
    chip.textContent = project.code;
    chip.addEventListener("click", () => {
      state.project = project.code;
      $("#projectCode").value = project.code;
      loadProjects();
      runInventory();
    });
    list.appendChild(chip);
  });
}

async function createProject() {
  const code = currentProject();
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
  writeOutput(data);
  await loadProjects();
  await runInventory();
}

async function upload(bucket, input) {
  const code = currentProject();
  if (!input.files.length) throw new Error("请选择文件");
  const form = new FormData();
  Array.from(input.files).forEach((file) => form.append("files", file));
  const data = await api(`/api/upload?project=${encodeURIComponent(code)}&bucket=${bucket}`, {
    method: "POST",
    body: form,
  });
  writeOutput(data);
  input.value = "";
  await runInventory();
}

async function runInventory() {
  const code = currentProject();
  const data = await api(`/api/inventory?project=${encodeURIComponent(code)}`);
  $("#gateStatus").textContent = data.s0_ready ? "S0 gate 已通过" : "缺少区位图";
  $("#gateStatus").style.color = data.s0_ready ? "#1f6f5b" : "#b94b2f";
  writeOutput(data);
}

async function runValidate() {
  const code = currentProject();
  const data = await api(`/api/validate?project=${encodeURIComponent(code)}`);
  writeOutput(data);
}

function bind() {
  $("#createProject").addEventListener("click", () => createProject().catch((err) => writeOutput(err.message)));
  $("#refreshProjects").addEventListener("click", () => loadProjects().catch((err) => writeOutput(err.message)));
  $("#runInventory").addEventListener("click", () => runInventory().catch((err) => writeOutput(err.message)));
  $("#runValidate").addEventListener("click", () => runValidate().catch((err) => writeOutput(err.message)));

  document.querySelectorAll(".bucket").forEach((bucketEl) => {
    const bucket = bucketEl.dataset.bucket;
    const input = bucketEl.querySelector("input");
    const button = bucketEl.querySelector("button");
    button.addEventListener("click", () => upload(bucket, input).catch((err) => writeOutput(err.message)));
  });
}

bind();
loadProjects().catch((err) => writeOutput(err.message));
