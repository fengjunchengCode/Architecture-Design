const PAGES = ["project", "s0", "s1", "s2", "workbench", "status"];
const PAGE_ALIASES = { spatial: "s1", upload: "s0", validate: "status", drawings: "workbench" };
const requestedPage = new URLSearchParams(window.location.search).get("page") || "project";
const requestedStagePage = PAGE_ALIASES[requestedPage] || requestedPage;

const state = {
  project: "",
  page: PAGES.includes(requestedStagePage) ? requestedStagePage : "project",
  pendingUrlProject: new URLSearchParams(window.location.search).get("project") || "",
  projects: [],
  inventory: null,
  controlPoints: [],
  cadPreview: null,
  alignment: null,
  alignmentTimer: null,
  candidateSetIdCurrent: null,
  candidateSetIdAtSave: null,
  controlPointsSaved: false,
  controlPointsStale: false,
  migrationReport: null,
  cadPreviewZoom: 1,
  s1Location: "",
  amap: {
    config: null,
    sdk: null,
    loaderPromise: null,
    s1Map: null,
    s1Marker: null,
    s1TdtMap: null,
    s1TdtMarker: null,
    s1MapMode: "standard",
    s1MouseTool: null,
    s1DrawMode: null,
    s1DistrictLayer: null,
    s1TdtDistrictLayer: null,
    s1Is3D: false,
    s1Geocoder: null,
    tiandituKey: null,
    s2Map: null,
    s2Markers: new Map(),
    activeCandidateId: "",
  },
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

const CONTROL_FEATURE_TYPES = {
  redline_corner: "红线角点",
  road_intersection: "道路交叉口",
  road_centerline: "道路中心线",
  road_edge: "道路边线/路缘",
  bridge_endpoint: "桥头/桥端",
  bridge_center: "桥中心/桥面",
  water_edge: "水系岸线",
  building_corner: "建筑/构筑物角点",
  visible_landmark: "可识别固定地物",
  other: "其他地物",
};

const CONTROL_PURPOSES = {
  registration: "几何配准",
  road_binding: "道路落边",
  entrance_check: "出入口判断",
  water_binding: "水系/景观",
  reference_only: "仅参考",
};

const CONTROL_CONFIDENCE = {
  low: "低置信",
  medium: "中置信",
  high: "高置信",
};

function escapeHtml(value) {
  return String(value)
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;");
}

function compactList(items, limit = 5) {
  if (!Array.isArray(items) || !items.length) return "无";
  const shown = items
    .slice(0, limit)
    .map((item) => escapeHtml(item?.name || BUCKET_LABELS[item] || item))
    .join("、");
  return items.length > limit ? `${shown} 等 ${items.length} 项` : shown;
}

function labelFromMap(map, value) {
  return map[value] || value || "未标注";
}

function controlFeatureText(value) {
  return labelFromMap(CONTROL_FEATURE_TYPES, value);
}

function controlPurposeText(value) {
  return labelFromMap(CONTROL_PURPOSES, value);
}

function controlConfidenceText(value) {
  return labelFromMap(CONTROL_CONFIDENCE, value);
}

function resultRow(label, value) {
  return `<div class="result-row"><span>${escapeHtml(label)}</span><b>${escapeHtml(value ?? "无")}</b></div>`;
}

function formatMeters(value) {
  const number = Number(value);
  return Number.isFinite(number) ? `${number.toFixed(1)}m` : "无";
}

function qualityText(value) {
  return {
    aligned_high: "高质量配准",
    aligned_partial: "粗配准可用",
    weak: "配准较弱",
    insufficient: "点数不足",
    failed: "配准失败",
    stale_control_points: "旧控制点已过期",
  }[value] || value || "未检查";
}

function candidateSetShort(value) {
  const text = String(value || "");
  const body = text.includes(":") ? text.split(":").pop() : text;
  return body ? body.slice(0, 16) : "无";
}

function refreshStaleState() {
  state.controlPointsStale = Boolean(
    state.controlPointsSaved
      && state.controlPoints.length
      && state.candidateSetIdCurrent
      && state.candidateSetIdAtSave !== state.candidateSetIdCurrent
  );
}

function hasStaleControlPoints() {
  refreshStaleState();
  return state.controlPointsStale;
}

function formatGcj02(lng, lat) {
  return `${Number(lng).toFixed(6)},${Number(lat).toFixed(6)}`;
}

function parsedLocation(value) {
  if (!value) return null;
  try {
    const normalized = parseLocationInput(String(value).trim());
    const [lng, lat] = normalized.split(",").map(Number);
    return { lng, lat, location: formatGcj02(lng, lat) };
  } catch {
    return null;
  }
}

function s1CenterPoint() {
  return parsedLocation($("#centerLocation")?.value || state.s1Location);
}

function setMapStatus(id, text, ok = null) {
  const el = $(id);
  if (!el) return;
  el.textContent = text;
  el.style.color = ok === null ? "" : ok ? "#1f6f5b" : "#b94b2f";
}

function setMapHint(id, text, warn = false) {
  const el = $(id);
  if (!el) return;
  el.textContent = text;
  el.classList.toggle("warn", warn);
}

function setMapEmpty(id, text) {
  const el = $(id);
  if (!el) return;
  el.innerHTML = `<div class="map-empty">${escapeHtml(text)}</div>`;
}

function amapFailureHint(error) {
  const warnings = state.amap.config?.warnings || [];
  return warnings.length ? warnings[0] : error?.message || "高德 JSAPI 暂不可用";
}

async function loadAmapJsapiConfig() {
  if (state.amap.config) return state.amap.config;
  state.amap.config = await api("/api/amap-jsapi-config");
  state.amap.tiandituKey = state.amap.config.tianditu_key || null;
  return state.amap.config;
}

async function ensureAmapSdk() {
  if (state.amap.sdk) return state.amap.sdk;
  if (state.amap.loaderPromise) return state.amap.loaderPromise;
  const config = await loadAmapJsapiConfig();
  if (!config.configured || !config.key) {
    throw new Error(config.warnings?.[0] || "未配置 AMAP_JSAPI_KEY");
  }
  const security = config.security || { mode: "none" };
  if (security.mode === "service_host" && security.service_host) {
    window._AMapSecurityConfig = { serviceHost: security.service_host };
  } else if (security.mode === "security_jscode" && security.security_jscode) {
    window._AMapSecurityConfig = { securityJsCode: security.security_jscode };
  }
  if (!window.AMapLoader?.load) {
    throw new Error("高德 JSAPI loader 未加载，请检查网络或 referer 白名单。");
  }
  state.amap.loaderPromise = window.AMapLoader.load({
    key: config.key,
    version: "2.0",
    plugins: ["AMap.Scale", "AMap.ToolBar", "AMap.AutoComplete", "AMap.PlaceSearch", "AMap.Geocoder", "AMap.DistrictSearch", "AMap.MouseTool"],
  }).then((sdk) => {
    state.amap.sdk = sdk;
    return sdk;
  });
  return state.amap.loaderPromise;
}

function addAmapControls(AMap, map) {
  try {
    if (AMap.Scale) map.addControl(new AMap.Scale());
    if (AMap.ToolBar) map.addControl(new AMap.ToolBar({ position: "RB" }));
  } catch {
    // Controls are optional; a failed control must not block coordinate picking.
  }
}

function lngLatFromAmapClick(event) {
  if (!event?.lnglat || typeof event.lnglat.getLng !== "function" || typeof event.lnglat.getLat !== "function") {
    throw new Error("高德地图点击事件未返回 lnglat。");
  }
  // AMap JSAPI v2 domestic keys return GCJ-02 lnglat here; do not convert to WGS84.
  const lng = Number(event.lnglat.getLng());
  const lat = Number(event.lnglat.getLat());
  if (!Number.isFinite(lng) || !Number.isFinite(lat)) throw new Error("地图坐标无效。");
  return { lng, lat, location: formatGcj02(lng, lat) };
}

function upsertS1Marker(AMap, point) {
  if (!state.amap.s1Map) return;
  const position = [point.lng, point.lat];
  if (!state.amap.s1Marker) {
    state.amap.s1Marker = new AMap.Marker({ position });
    state.amap.s1Marker.setMap(state.amap.s1Map);
  } else {
    state.amap.s1Marker.setPosition(position);
  }
}

async function ensureS1Map() {
  if (state.page !== "s1" || !state.project || !$("#s1AmapMap")) return;
  const center = s1CenterPoint();
  if (!center) {
    setMapStatus("#s1AmapStatus", "等待中心点", null);
    setMapHint("#s1AmapHint", "先输入或从已有 S1 上下文加载 GCJ-02 中心点。");
    if (!state.amap.s1Map) setMapEmpty("#s1AmapMap", "输入或加载中心点后显示地图；外部拾取器仍可作为备用。");
    return;
  }
  try {
    const AMap = await ensureAmapSdk();
    if (!state.amap.s1Map) {
      $("#s1AmapMap").innerHTML = "";
      state.amap.s1Map = new AMap.Map("s1AmapMap", {
        center: [center.lng, center.lat],
        zoom: 17,
        viewMode: "2D",
        WebGLParams: { preserveDrawingBuffer: true },
      });
      addAmapControls(AMap, state.amap.s1Map);
      state.amap.s1Map.on("click", (event) => {
        try {
          const picked = lngLatFromAmapClick(event);
          $("#centerLocation").value = picked.location;
          state.s1Location = picked.location;
          upsertS1Marker(AMap, picked);
          setMapStatus("#s1AmapStatus", "已写入中心点", true);
          setMapHint("#s1AmapHint", "坐标已写入上方输入框，点击“生成 S1 高德上下文”后生效。");
        } catch (err) {
          writeOutput(err.message);
        }
      });
      initS1AmapSearch(AMap);
      initS1MapTools(AMap);
    }
    if (state.amap.s1Map.setCenter) state.amap.s1Map.setCenter([center.lng, center.lat]);
    upsertS1Marker(AMap, center);
    setMapStatus("#s1AmapStatus", "地图已加载", true);
    setMapHint("#s1AmapHint", "点击地图会把 GCJ-02 坐标写入上方中心点输入框。");
  } catch (err) {
    setMapStatus("#s1AmapStatus", "地图不可用", false);
    setMapHint("#s1AmapHint", amapFailureHint(err), true);
    setMapEmpty("#s1AmapMap", "内嵌地图暂不可用；请使用外部高德拾取器备用。");
  }
}


// --- GCJ-02 <-> WGS84 conversion (standard Krasovsky 1940 algorithm) ---
var _PI = 3.14159265358979324;
var _A = 6378245.0;
var _EE = 0.00669342162296594323;

function _tLat(x, y) {
  var r = -100+2*x+3*y+0.2*y*y+0.1*x*y+0.2*Math.sqrt(Math.abs(x));
  r += (20*Math.sin(6*x*_PI)+20*Math.sin(2*x*_PI))*2/3;
  r += (20*Math.sin(y*_PI)+40*Math.sin(y/3*_PI))*2/3;
  r += (160*Math.sin(y/12*_PI)+320*Math.sin(y*_PI/30))*2/3;
  return r;
}
function _tLng(x, y) {
  var r = 300+x+2*y+0.1*x*x+0.1*x*y+0.1*Math.sqrt(Math.abs(x));
  r += (20*Math.sin(6*x*_PI)+20*Math.sin(2*x*_PI))*2/3;
  r += (20*Math.sin(x*_PI)+40*Math.sin(x/3*_PI))*2/3;
  r += (150*Math.sin(x/12*_PI)+300*Math.sin(x/30*_PI))*2/3;
  return r;
}
function gcj02ToWgs84(lng, lat) {
  var dx = _tLng(lng-105, lat-35), dy = _tLat(lng-105, lat-35);
  var rl = lat/180*_PI, m = Math.sin(rl);
  m = 1-_EE*m*m; var sm = Math.sqrt(m);
  dy = (dy*180)/((_A*(1-_EE))/(m*sm)*_PI);
  dx = (dx*180)/(_A/sm*Math.cos(rl)*_PI);
  return [lng-dx, lat-dy];
}
function wgs84ToGcj02(lng, lat) {
  var dx = _tLng(lng-105, lat-35), dy = _tLat(lng-105, lat-35);
  var rl = lat/180*_PI, m = Math.sin(rl);
  m = 1-_EE*m*m; var sm = Math.sqrt(m);
  dy = (dy*180)/((_A*(1-_EE))/(m*sm)*_PI);
  dx = (dx*180)/(_A/sm*Math.cos(rl)*_PI);
  return [lng+dx, lat+dy];
}

// --- Dual map mode ---
// Tianditu uses WGS84, standard AMap uses GCJ-02.
// Click events on Tianditu return WGS84; need conversion to GCJ-02 for input.
function ensureTdtMap(AMap, centerWgs, zoom) {
  if (state.amap.s1TdtMap) return;
  var tk = state.amap.tiandituKey;
  if (!tk) return;
  // Tianditu map center uses WGS84
  state.amap.s1TdtMap = new AMap.Map("s1TdtMap", {
    center: centerWgs, zoom: zoom || 17, viewMode: "2D",
    layers: [
      new AMap.TileLayer({ tileUrl: "https://t0.tianditu.gov.cn/img_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=img&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX=[z]&TILEROW=[y]&TILECOL=[x]&tk=" + tk, tileSize: 256 }),
      new AMap.TileLayer({ tileUrl: "https://t0.tianditu.gov.cn/cia_w/wmts?SERVICE=WMTS&REQUEST=GetTile&VERSION=1.0.0&LAYER=cia&STYLE=default&TILEMATRIXSET=w&FORMAT=tiles&TILEMATRIX=[z]&TILEROW=[y]&TILECOL=[x]&tk=" + tk, tileSize: 256 })
    ],
    WebGLParams: { preserveDrawingBuffer: true },
  });
  addAmapControls(AMap, state.amap.s1TdtMap);
  // Click handler: Tianditu returns WGS84, convert to GCJ-02 for input
  state.amap.s1TdtMap.on("click", function(event) {
    try {
      if (!event.lnglat) return;
      var wgsLng = event.lnglat.getLng(), wgsLat = event.lnglat.getLat();
      var gcj = wgs84ToGcj02(wgsLng, wgsLat);
      document.querySelector("#centerLocation").value = formatGcj02(gcj[0], gcj[1]);
      state.s1Location = formatGcj02(gcj[0], gcj[1]);
      // Standard marker uses GCJ-02
      upsertS1Marker(AMap, { lng: gcj[0], lat: gcj[1] });
      // Tianditu marker uses WGS84
      if (state.amap.s1TdtMarker) {
        state.amap.s1TdtMarker.setPosition([wgsLng, wgsLat]);
      } else {
        state.amap.s1TdtMarker = new AMap.Marker({ position: [wgsLng, wgsLat] });
        state.amap.s1TdtMarker.setMap(state.amap.s1TdtMap);
      }
      setMapStatus("#s1AmapStatus", "已写入中心点（WGS84→GCJ-02）", true);
      if (state.amap.s1Geocoder) {
        state.amap.s1Geocoder.getAddress(gcj, function(s, r) {
          if (s === "complete" && r.regeocode) {
            var g = document.querySelector("#s1AmapGeocoder");
            if (g) g.textContent = r.regeocode.formattedAddress;
          }
        });
      }
      setMapHint("#s1AmapHint", "坐标已写入上方输入框。");
    } catch (err) { writeOutput(err.message); }
  });
}

function switchToTdt(AMap) {
  var aMapEl = document.querySelector("#s1AmapMap");
  var tdtEl = document.querySelector("#s1TdtMap");
  if (!aMapEl || !tdtEl) return;
  var center = state.amap.s1Map.getCenter();
  var zoom = state.amap.s1Map.getZoom();
  // Convert GCJ-02 center to WGS84 for Tianditu
  var centerWgs = gcj02ToWgs84(center.getLng(), center.getLat());
  // Show container FIRST so map gets correct dimensions
  aMapEl.style.display = "none";
  tdtEl.style.display = "block";
  state.amap.s1MapMode = "tianditu";
  // Create or reuse Tianditu map with WGS84 center
  ensureTdtMap(AMap, centerWgs, zoom);
  state.amap.s1TdtMap.setCenter(centerWgs);
  state.amap.s1TdtMap.setZoom(zoom);
  // Sync marker: GCJ-02 → WGS84 for Tianditu
  if (state.amap.s1Marker) {
    var mPos = state.amap.s1Marker.getPosition();
    var mWgs = gcj02ToWgs84(mPos.getLng(), mPos.getLat());
    if (state.amap.s1TdtMarker) {
      state.amap.s1TdtMarker.setPosition(mWgs);
    } else {
      state.amap.s1TdtMarker = new AMap.Marker({ position: mWgs });
      state.amap.s1TdtMarker.setMap(state.amap.s1TdtMap);
    }
  }
  // Force resize after DOM layout update
  setTimeout(function() { state.amap.s1TdtMap.resize(); }, 200);
  setMapStatus("#s1AmapStatus", "天地图高清卫星（WGS84 坐标系，无偏移）", true);
}

function switchToStd(AMap) {
  var aMapEl = document.querySelector("#s1AmapMap");
  var tdtEl = document.querySelector("#s1TdtMap");
  if (!aMapEl || !tdtEl) return;
  if (state.amap.s1TdtMap) {
    // Convert Tianditu WGS84 center to GCJ-02 for standard map
    var tCenter = state.amap.s1TdtMap.getCenter();
    var gcj = wgs84ToGcj02(tCenter.getLng(), tCenter.getLat());
    state.amap.s1Map.setCenter(gcj);
    state.amap.s1Map.setZoom(state.amap.s1TdtMap.getZoom());
    // Sync marker: WGS84 → GCJ-02
    if (state.amap.s1TdtMarker) {
      var mPos = state.amap.s1TdtMarker.getPosition();
      var mGcj = wgs84ToGcj02(mPos.getLng(), mPos.getLat());
      upsertS1Marker(AMap, { lng: mGcj[0], lat: mGcj[1] });
    }
  }
  tdtEl.style.display = "none";
  aMapEl.style.display = "block";
  state.amap.s1MapMode = "standard";
  setMapStatus("#s1AmapStatus", "标准地图（GCJ-02 坐标系）", true);
}

function setS1MapMode(AMap, mode) {
  if (!state.amap.s1Map) return;
  if (mode === "tianditu" && state.amap.tiandituKey) {
    switchToTdt(AMap);
  } else {
    switchToStd(AMap);
  }
  var btns = { standard: "#s1MapStd", tianditu: "#s1MapTdt" };
  for (var k in btns) { var b = document.querySelector(btns[k]); if (b) b.classList.toggle("active", k === mode); }
}

function initS1MapTools(AMap) {
  state.amap.s1Geocoder = new AMap.Geocoder();
  var bindings = { "#s1MapStd": "standard", "#s1MapTdt": "tianditu" };
  for (var sel in bindings) { (function(s, m) { var btn = document.querySelector(s); if (btn) btn.addEventListener("click", function() { setS1MapMode(AMap, m); }); })(sel, bindings[sel]); }

  // 3D toggle
  var d3Btn = document.querySelector("#s1Map3D");
  if (d3Btn) d3Btn.addEventListener("click", function() {
    state.amap.s1Is3D = !state.amap.s1Is3D;
    var center = state.amap.s1Map.getCenter();
    var zoom = state.amap.s1Map.getZoom();
    state.amap.s1Map.destroy();
    state.amap.s1Map = new AMap.Map("s1AmapMap", {
      center: [center.getLng(), center.getLat()], zoom: zoom,
      viewMode: state.amap.s1Is3D ? "3D" : "2D",
      pitch: state.amap.s1Is3D ? 60 : 0,
      buildingAnimation: state.amap.s1Is3D,
      WebGLParams: { preserveDrawingBuffer: true },
    });
    addAmapControls(AMap, state.amap.s1Map);
    if (state.amap.s1Marker) state.amap.s1Marker.setMap(state.amap.s1Map);
    if (state.amap.s1DistrictLayer) state.amap.s1Map.add(state.amap.s1DistrictLayer);
    state.amap.s1Map.on("click", function(event) {
      try {
        var picked = lngLatFromAmapClick(event);
        document.querySelector("#centerLocation").value = picked.location;
        state.s1Location = picked.location;
        upsertS1Marker(AMap, picked);
        setMapStatus("#s1AmapStatus", "已写入中心点", true);
        if (state.amap.s1Geocoder) { state.amap.s1Geocoder.getAddress([picked.lng, picked.lat], function(s,r) { if (s==="complete"&&r.regeocode) { var g=document.querySelector("#s1AmapGeocoder"); if(g) g.textContent=r.regeocode.formattedAddress; } }); }
        setMapHint("#s1AmapHint", "坐标已写入上方输入框。");
      } catch (err) { writeOutput(err.message); }
    });
    d3Btn.classList.toggle("active", state.amap.s1Is3D);
    setMapStatus("#s1AmapStatus", state.amap.s1Is3D ? "3D视角" : "地图已加载", true);
  });

  // District boundary
  var distBtn = document.querySelector("#s1DistrictBtn");
  if (distBtn) distBtn.addEventListener("click", function() {
    var activeMap = state.amap.s1MapMode === "tianditu" ? state.amap.s1TdtMap : state.amap.s1Map;
    var activeDistrict = state.amap.s1MapMode === "tianditu" ? state.amap.s1TdtDistrictLayer : state.amap.s1DistrictLayer;
    if (!activeMap) return;
    if (activeDistrict) {
      activeMap.remove(activeDistrict);
      if (state.amap.s1MapMode === "tianditu") state.amap.s1TdtDistrictLayer = null;
      else state.amap.s1DistrictLayer = null;
      distBtn.classList.remove("active");
      return;
    }
    var center = s1CenterPoint(); if (!center) return;
    state.amap.s1Geocoder.getAddress([center.lng, center.lat], function(st, res) {
      if (st !== "complete" || !res.regeocode) { setMapStatus("#s1AmapStatus", "逆地理编码失败", false); return; }
      var comp = res.regeocode.addressComponent;
      var adcode = comp.adcode;
      var township = comp.township || "";
      var district = comp.district || "";
      if (!adcode) { setMapStatus("#s1AmapStatus", "无法获取行政区编码", false); return; }
      var ds = new AMap.DistrictSearch({ level: "district", extensions: "all", subdistrict: 0 });
      ds.search(adcode, function(s2, r2) {
        if (s2 !== "complete" || !r2.districtList || !r2.districtList[0]) { setMapStatus("#s1AmapStatus", "行政区查询失败", false); return; }
        var result = r2.districtList[0];
        var boundaries = result.boundaries;
        if (!boundaries || !boundaries.length) { setMapStatus("#s1AmapStatus", "该区域无边界数据", false); return; }
        var paths = [];
        for (var i = 0; i < boundaries.length; i++) { paths.push(boundaries[i]); }
        var poly = new AMap.Polygon({ path: paths, strokeColor: "#1f6f5b", strokeWeight: 2, fillColor: "#1f6f5b", fillOpacity: 0.08, strokeStyle: "dashed", zIndex: 50 });
        activeMap.add(poly);
        if (state.amap.s1MapMode === "tianditu") state.amap.s1TdtDistrictLayer = poly;
        else state.amap.s1DistrictLayer = poly;
        distBtn.classList.add("active");
        var displayName = district || result.name || "行政区";
        if (township && township !== district) displayName = township + "（" + displayName + "边界）";
        setMapStatus("#s1AmapStatus", "已显示: " + displayName, true);
      });
    });
  });

  // Draw polygon
  var drawBtn = document.querySelector("#s1DrawBtn");
  if (drawBtn) drawBtn.addEventListener("click", function() {
    var activeMap = state.amap.s1MapMode === "tianditu" ? state.amap.s1TdtMap : state.amap.s1Map;
    if (!activeMap) return;
    if (state.amap.s1DrawMode === "draw") { if (state.amap.s1MouseTool) state.amap.s1MouseTool.close(true); state.amap.s1DrawMode = null; drawBtn.classList.remove("active"); return; }
    if (!state.amap.s1MouseTool) state.amap.s1MouseTool = new AMap.MouseTool(activeMap);
    state.amap.s1DrawMode = "draw"; drawBtn.classList.add("active");
    state.amap.s1MouseTool.polygon({ strokeColor: "#E04030", strokeWeight: 2, fillColor: "#E04030", fillOpacity: 0.15, strokeStyle: "dashed" });
    setMapHint("#s1AmapHint", "在地图上点击绘制用地范围，双击结束。");
  });

  // Screenshot
  var shotBtn = document.querySelector("#s1ScreenshotBtn");
  if (shotBtn) shotBtn.addEventListener("click", function() {
    var containerId = state.amap.s1MapMode === "tianditu" ? "#s1TdtMap" : "#s1AmapMap";
    var container = document.querySelector(containerId);
    if (!container) return;
    setMapStatus("#s1AmapStatus", "正在截图...", null);
    try {
      var canvases = container.querySelectorAll("canvas");
      if (canvases.length === 0) { setMapStatus("#s1AmapStatus", "截图失败: 无canvas", false); return; }
      var w = 0, h = 0;
      for (var i = 0; i < canvases.length; i++) { if (canvases[i].width > w) w = canvases[i].width; if (canvases[i].height > h) h = canvases[i].height; }
      if (w === 0 || h === 0) { setMapStatus("#s1AmapStatus", "截图失败: canvas尺寸为0", false); return; }
      var merged = document.createElement("canvas"); merged.width = w; merged.height = h;
      var ctx = merged.getContext("2d");
      ctx.fillStyle = "#fff"; ctx.fillRect(0, 0, w, h);
      for (var j = 0; j < canvases.length; j++) { try { ctx.drawImage(canvases[j], 0, 0); } catch(e) {} }
      var link = document.createElement("a");
      link.download = "s1_" + state.amap.s1MapMode + "_" + new Date().toISOString().slice(0,19).replace(/[T:]/g,"-") + ".png";
      link.href = merged.toDataURL("image/png"); link.click();
      setMapStatus("#s1AmapStatus", "截图已下载", true);
    } catch (e) { setMapStatus("#s1AmapStatus", "截图失败: " + e.message, false); }
  });
}

// --- S1 Map: search ---
function initS1AmapSearch(AMap) {
  var input = document.querySelector("#s1AmapSearch");
  var resultsEl = document.querySelector("#s1AmapSearchResults");
  if (!input || !resultsEl) return;
  var debounceTimer = null; var autoComplete = null;
  function clearResults() { resultsEl.innerHTML = ""; resultsEl.hidden = true; }
  function showResults(pois) {
    if (!pois || !pois.length) { clearResults(); return; }
    var html = "";
    for (var i = 0; i < pois.length; i++) { var p = pois[i]; html += '<div class="amap-search-item" data-index="' + i + '"><div class="sr-name">' + escapeHtml(p.name||"") + '</div><div class="sr-addr">' + escapeHtml(p.address||p.cityname||"") + '</div></div>'; }
    resultsEl.innerHTML = html; resultsEl.hidden = false;
    var items = resultsEl.querySelectorAll(".amap-search-item");
    for (var j = 0; j < items.length; j++) { (function(el) { el.addEventListener("click", function() {
      var idx = Number(el.dataset.index); var poi = pois[idx]; if (!poi||!poi.location) return;
      var lng = typeof poi.location.getLng==="function" ? poi.location.getLng() : poi.location.lng;
      var lat = typeof poi.location.getLat==="function" ? poi.location.getLat() : poi.location.lat;
      // Search results are GCJ-02 from AMap
      // Input and standard marker always use GCJ-02
      document.querySelector("#centerLocation").value = formatGcj02(lng,lat);
      state.s1Location = formatGcj02(lng,lat);
      upsertS1Marker(AMap, {lng:lng,lat:lat});
      if (state.amap.s1MapMode === "tianditu") {
        // Convert GCJ-02 → WGS84 for Tianditu map center and marker
        var wgs = gcj02ToWgs84(lng, lat);
        if (state.amap.s1TdtMap) { state.amap.s1TdtMap.setCenter(wgs); state.amap.s1TdtMap.setZoom(17); }
        if (state.amap.s1TdtMarker) { state.amap.s1TdtMarker.setPosition(wgs); }
        else { state.amap.s1TdtMarker = new AMap.Marker({ position: wgs }); state.amap.s1TdtMarker.setMap(state.amap.s1TdtMap); }
      } else {
        var activeMap = state.amap.s1Map;
        if (activeMap) { activeMap.setCenter([lng,lat]); activeMap.setZoom(17); }
      }
      setMapStatus("#s1AmapStatus","已定位: "+poi.name,true);
      clearResults(); input.value = poi.name;
      if (state.amap.s1Geocoder) { state.amap.s1Geocoder.getAddress([lng,lat], function(s,r) { if (s==="complete"&&r.regeocode) { var g=document.querySelector("#s1AmapGeocoder"); if(g) g.textContent=r.regeocode.formattedAddress; } }); }
    }); })(items[j]); }
  }
  if (AMap.AutoComplete) autoComplete = new AMap.AutoComplete({ city: "全国" });
  input.addEventListener("input", function() { clearTimeout(debounceTimer); var kw=input.value.trim(); if(!kw){clearResults();return;} debounceTimer=setTimeout(function(){
    if (autoComplete) { autoComplete.search(kw, function(st,res) { if(st==="complete"&&res.tips){var f=[];for(var i=0;i<res.tips.length;i++){if(res.tips[i].location)f.push(res.tips[i]);}showResults(f);}else{clearResults();} }); }
    else if (AMap.PlaceSearch) { var ps=new AMap.PlaceSearch({city:"全国",pageSize:8}); ps.search(kw,function(st,res){if(st==="complete"&&res.poiList){showResults(res.poiList.pois);}else{clearResults();}}); }
  },300); });
  document.addEventListener("click", function(e) { if(!e.target.closest(".amap-search-wrap"))clearResults(); });
  input.addEventListener("keydown", function(e) { if(e.key==="Enter"){e.preventDefault();var f=resultsEl.querySelector(".amap-search-item");if(f)f.click();} });
}

function findCandidateById(id) {
  const candidates = state.cadPreview?.candidates || [];
  return candidates.find((candidate) => (candidate.label || candidate.id) === id);
}

function updateActiveCandidatePanel() {
  const el = $("#s2ActiveCandidate");
  if (!el) return;
  if (hasStaleControlPoints()) {
    el.textContent = "旧控制点已过期。请先生成迁移诊断或归档旧控制点，再重新拾取。";
    return;
  }
  if (!state.amap.activeCandidateId) {
    el.textContent = "先在左侧候选点点击“地图拾取”。";
    return;
  }
  const candidate = findCandidateById(state.amap.activeCandidateId);
  const role = candidate ? controlFeatureText(candidate.feature_type || "redline_corner") : "候选点";
  el.textContent = `正在拾取 ${state.amap.activeCandidateId} · ${role}`;
}

function setActiveCandidate(id) {
  if (hasStaleControlPoints()) {
    writeOutput("旧控制点已过期，请先归档旧控制点后再重新拾取。");
    return;
  }
  state.amap.activeCandidateId = id || "";
  updateActiveCandidatePanel();
  renderCadPreview();
  const existing = state.controlPoints.find((point) => point.label === id);
  const parsed = parsedLocation(existing?.amap_location);
  if (parsed && state.amap.s2Map?.setCenter) state.amap.s2Map.setCenter([parsed.lng, parsed.lat]);
}

function scrollToS2Map() {
  const panel = $("#s2AmapPanel");
  if (!panel) return;
  panel.scrollIntoView({ behavior: "smooth", block: "start" });
}

function clearS2Markers() {
  state.amap.s2Markers.forEach((marker) => {
    if (marker?.setMap) marker.setMap(null);
  });
  state.amap.s2Markers.clear();
}

function upsertS2Marker(label, point) {
  if (!state.amap.s2Map || !state.amap.sdk || !label || !point) return;
  const AMap = state.amap.sdk;
  const position = [point.lng, point.lat];
  let marker = state.amap.s2Markers.get(label);
  if (!marker) {
    marker = new AMap.Marker({ position });
    marker.on("click", () => setActiveCandidate(label));
    marker.setMap(state.amap.s2Map);
    state.amap.s2Markers.set(label, marker);
  } else {
    marker.setPosition(position);
  }
  marker.setLabel({
    direction: "top",
    content: `<div class="amap-label">${escapeHtml(label)}</div>`,
  });
}

function renderS2Markers() {
  if (!state.amap.s2Map || !state.amap.sdk) return;
  if (hasStaleControlPoints()) {
    clearS2Markers();
    return;
  }
  const labels = new Set();
  state.controlPoints.forEach((point) => {
    const parsed = parsedLocation(point.amap_location);
    if (!point.label || !parsed) return;
    labels.add(point.label);
    upsertS2Marker(point.label, parsed);
  });
  state.amap.s2Markers.forEach((marker, label) => {
    if (!labels.has(label)) {
      if (marker?.setMap) marker.setMap(null);
      state.amap.s2Markers.delete(label);
    }
  });
}

async function ensureS2Map() {
  if (state.page !== "s2" || !state.project || !$("#s2AmapMap")) return;
  const panel = $("#s2AmapPanel");
  const stale = hasStaleControlPoints();
  panel?.classList.toggle("disabled", stale);
  updateActiveCandidatePanel();
  if (stale) {
    setMapStatus("#s2AmapStatus", "旧控制点过期", false);
    setMapHint("#s2AmapHint", "当前旧控制点与 CAD 候选集不匹配，地图拾取已停用。", true);
    clearS2Markers();
    if (!state.amap.s2Map) setMapEmpty("#s2AmapMap", "旧控制点过期。请先处理 stale 提示，再重新拾取。");
    return;
  }
  const center = s1CenterPoint();
  if (!center) {
    setMapStatus("#s2AmapStatus", "缺少 S1 中心点", false);
    setMapHint("#s2AmapHint", "先在 S1 标定中心点，S2 地图才会启动。", true);
    if (!state.amap.s2Map) setMapEmpty("#s2AmapMap", "先在 S1 标定中心点；S2 不使用默认城市。");
    return;
  }
  try {
    const AMap = await ensureAmapSdk();
    if (!state.amap.s2Map) {
      $("#s2AmapMap").innerHTML = "";
      state.amap.s2Map = new AMap.Map("s2AmapMap", {
        center: [center.lng, center.lat],
        zoom: 17,
        viewMode: "2D",
      });
      addAmapControls(AMap, state.amap.s2Map);
      state.amap.s2Map.on("click", (event) => {
        try {
          if (hasStaleControlPoints()) return;
          if (!state.amap.activeCandidateId) {
            setMapStatus("#s2AmapStatus", "先选择 CAD 点", false);
            setMapHint("#s2AmapHint", "请先在候选点卡片上点击“地图拾取”。", true);
            return;
          }
          const candidate = findCandidateById(state.amap.activeCandidateId);
          if (!candidate) throw new Error("当前 CAD 候选点不存在，请重新选择。");
          const picked = lngLatFromAmapClick(event);
          candidate.amap_location = picked.location;
          addCandidateControlPoint(candidate);
          upsertS2Marker(state.amap.activeCandidateId, picked);
          setMapStatus("#s2AmapStatus", "已加入控制点", true);
          setMapHint("#s2AmapHint", `${state.amap.activeCandidateId} 已写入 ${picked.location}`);
        } catch (err) {
          writeOutput(err.message);
        }
      });
    }
    if (state.amap.s2Map.setCenter) state.amap.s2Map.setCenter([center.lng, center.lat]);
    renderS2Markers();
    setMapStatus("#s2AmapStatus", state.amap.activeCandidateId ? "等待地图点击" : "地图已加载", true);
    setMapHint("#s2AmapHint", state.amap.activeCandidateId ? "在地图上点击当前 CAD 点对应的真实位置。" : "先在左侧候选点点击“地图拾取”。");
  } catch (err) {
    setMapStatus("#s2AmapStatus", "地图不可用", false);
    setMapHint("#s2AmapHint", amapFailureHint(err), true);
    setMapEmpty("#s2AmapMap", "内嵌地图暂不可用；请使用外部高德拾取器备用。");
  }
}

function syncAmapUi() {
  updateActiveCandidatePanel();
  if (state.page === "s1") ensureS1Map().catch((err) => writeOutput(err.message));
  if (state.page === "s2") ensureS2Map().catch((err) => writeOutput(err.message));
}

function directionText(east, north) {
  const x = Number(east);
  const y = Number(north);
  if (!Number.isFinite(x) || !Number.isFinite(y)) return "方向未知";
  const ew = Math.abs(x) < 1 ? "" : x > 0 ? "东" : "西";
  const ns = Math.abs(y) < 1 ? "" : y > 0 ? "北" : "南";
  return `${ew}${ns}` || "接近";
}

function residualByLabel(alignment, label) {
  const rows = alignment?.best_fit?.residuals || alignment?.all_points_fit?.residuals || [];
  return rows.find((row) => row.label === label);
}

function residualNote(alignment, label) {
  const residual = residualByLabel(alignment, label);
  if (!residual) return "";
  const outliers = alignment?.best_fit?.outlier_labels || [];
  const expected = Array.isArray(residual.expected_gcj02)
    ? `${residual.expected_gcj02[0].toFixed(6)},${residual.expected_gcj02[1].toFixed(6)}`
    : "";
  const direction = directionText(residual.delta_east_m, residual.delta_north_m);
  const prefix = outliers.includes(label) ? "需复核" : "偏差";
  const reason = outliers.includes(label)
    ? "可能点到了相邻边界、影像角点，或该 CAD 红线点在高德上没有清晰实体。"
    : "小偏差可接受。";
  return `${prefix} ${formatMeters(residual.error_m)}，反推点在${direction}侧${expected ? `，约 ${expected}` : ""}。${reason}`;
}

function detailsJson(data) {
  return `<details class="json-details"><summary>查看 agent 原始 JSON</summary><pre>${escapeHtml(JSON.stringify(data, null, 2))}</pre></details>`;
}

function summarizeInventory(data) {
  const counts = data.counts || {};
  const missing = data.required_missing || [];
  const warnings = data.warnings || [];
  return `
    <div class="summary-card ${data.s0_ready ? "ok" : "warn"}">
      <h3>${data.s0_ready ? "S0 gate 已通过" : "S0 gate 未通过"}</h3>
      <div class="result-grid">
        ${resultRow("项目", data.project_code)}
        ${resultRow("文件总数", counts.total || 0)}
        ${resultRow("区位图", counts.location_map || 0)}
        ${resultRow("任务书", counts.briefing || 0)}
        ${resultRow("地形图", counts.topography || 0)}
        ${resultRow("现场照片", counts.site_photo || 0)}
      </div>
      ${missing.length ? `<p class="result-warning">缺少：${compactList(missing)}</p>` : ""}
      ${warnings.length ? `<p class="result-warning">警告：${compactList(warnings)}</p>` : ""}
      <p class="result-next">${data.s0_ready ? "可以回到对话要求 agent 执行 S0。" : "请先补齐区位图，再重新运行 Inventory。"}</p>
    </div>
  `;
}

function summarizeValidate(data) {
  const stats = data.stats || {};
  const issues = data.issues || [];
  const fatal = issues.filter((item) => item.level === "FATAL");
  const warn = issues.filter((item) => item.level === "WARN");
  return `
    <div class="summary-card ${fatal.length ? "bad" : warn.length ? "warn" : "ok"}">
      <h3>${fatal.length ? "Record 校验失败" : warn.length ? "Record 有警告" : "Record 校验通过"}</h3>
      <div class="result-grid">
        ${resultRow("项目", stats.project_code)}
        ${resultRow("类型", stats.project_type)}
        ${resultRow("阶段", stats.stage)}
        ${resultRow("待问问题", stats.pending_count ?? 0)}
        ${resultRow("低置信字段", stats.low_confidence_count ?? 0)}
        ${resultRow("可继续阶段", Array.isArray(stats.ready_for) ? stats.ready_for.join("、") : "无")}
      </div>
      ${issues.length ? `<p class="result-warning">${issues.map((item) => `${item.level}: ${item.msg}`).map(escapeHtml).join("<br>")}</p>` : ""}
      <p class="result-next">${fatal.length ? "请先修复 FATAL 问题。" : "结构有效，可以继续按对应 skill 执行。"}</p>
    </div>
  `;
}

function summarizeAmap(data) {
  const location = data.location || {};
  const regeo = data.map_context?.regeo || {};
  const seed = data.s1_external_context_seed || {};
  const roads = seed.external_features?.primary_roads || seed.amap_context?.roads || [];
  const water = seed.amap_context?.water || seed.external_features?.landscape_or_culture_nodes || [];
  const controlNeeds = seed.s2_use?.required_control_points || [];
  const poi1000 = seed.amap_context?.poi_1000m || {};
  const poiTotal = Object.values(poi1000).reduce((sum, items) => sum + (Array.isArray(items) ? items.length : 0), 0);
  return `
    <div class="summary-card ${data.status === "ok" ? "ok" : "warn"}">
      <h3>${data.status === "ok" ? "S1 地图证据包已生成" : "S1 地图证据包生成失败"}</h3>
      <div class="result-grid">
        ${resultRow("中心点", location.amap_gcj02)}
        ${resultRow("逆地理地址", regeo.formatted_address)}
        ${resultRow("配准状态", seed.registration_state)}
        ${resultRow("入口判断", seed.entrance_judgment?.level === "candidate" ? "只能候选，未绑定 CAD 边" : seed.entrance_judgment?.level)}
      </div>
      <div class="result-section">
        <b>对设计真正有用的线索</b>
        <p>道路/到达：${compactList(roads)}</p>
        <p>水系/桥梁/边界：${compactList(water)}</p>
        <p>控制点需求：${compactList(controlNeeds, 2)}</p>
      </div>
      <div class="result-section">
        <b>当前不能直接得出的结论</b>
        <p>主次入口不能只靠中心点确定；道路、水系和入口必须等 S1 结合区位图/现场照片，或等 S2 控制点把地图和 CAD 红线配准后再落边。</p>
        <p>附近 POI 共 ${escapeHtml(poiTotal)} 条已保留在原始 JSON，默认不作为设计结论展示。</p>
      </div>
      <p class="result-next">${data.status === "ok" ? "下一步：回到对话执行 S1；若需要精确到红线边，再到 S2 录入 2-3 个地图点 ↔ CAD 点。" : escapeHtml(data.error || "请检查 key 和坐标。")}</p>
    </div>
  `;
}

function summarizeSpatial(data) {
  const context = data.amap_context || {};
  return `
    <div class="summary-card ${data.amap_context_exists ? "ok" : "warn"}">
      <h3>${data.amap_context_exists ? "空间定位已读取" : "尚无空间定位"}</h3>
      <div class="result-grid">
        ${resultRow("项目", data.project)}
        ${resultRow("中心点", context.location?.amap_gcj02)}
        ${resultRow("地址", context.address)}
        ${resultRow("控制点", `${(data.control_points || []).length} 个`)}
      </div>
      <p class="result-next">${data.amap_context_exists ? "刷新页面会自动回填中心点。" : "请在 S1 输入页生成高德上下文。"}</p>
    </div>
  `;
}

function summarizeControlPoints(data) {
  const alignment = data.alignment || {};
  if (alignment.status === "stale_control_points") {
    return `
      <div class="summary-card warn">
        <h3>旧控制点已过期</h3>
        <div class="result-grid">
          ${resultRow("当前候选集", candidateSetShort(alignment.candidate_set_id_current))}
          ${resultRow("保存时候选集", candidateSetShort(alignment.candidate_set_id_at_save))}
        </div>
        <p class="result-warning">请先生成迁移诊断或归档旧控制点，不要继续把这些点用于 S1/S2 合成。</p>
      </div>
    `;
  }
  const best = alignment.best_fit || {};
  const quality = alignment.quality || "未检查";
  const inliers = best.inlier_labels || [];
  const outliers = best.outlier_labels || [];
  const points = data.control_points || [];
  const semanticCount = points.filter((point) =>
    ["road_intersection", "road_centerline", "road_edge", "bridge_endpoint", "bridge_center", "water_edge"].includes(point.feature_type)
    || ["road_binding", "entrance_check", "water_binding"].includes(point.purpose)
  ).length;
  return `
    <div class="summary-card ${quality === "aligned_high" ? "ok" : quality === "aligned_partial" ? "warn" : "ok"}">
      <h3>控制点已保存</h3>
      <div class="result-grid">
        ${resultRow("项目", data.project)}
        ${resultRow("数量", data.count)}
        ${resultRow("文件", data.path)}
        ${resultRow("配准质量", qualityText(quality))}
        ${resultRow("语义控制点", `${semanticCount} 个`)}
      </div>
      ${inliers.length ? `<p class="result-next">可用内点：${compactList(inliers, 8)}</p>` : ""}
      ${outliers.length ? `<p class="result-warning">需复核：${compactList(outliers, 8)}</p>` : ""}
      ${outliers.map((label) => `<p class="result-warning">${escapeHtml(label)}：${escapeHtml(residualNote(alignment, label))}</p>`).join("")}
      <p class="result-next">S2 将读取这些控制点和配准报告，用于判断是否能把高德地图关系绑定到 CAD 红线边。</p>
    </div>
  `;
}

function summarizeMigration(data) {
  const migration = data.migration || data;
  const items = migration.items || [];
  const unmatched = items.filter((item) => item.match_type === "unmatched").length;
  const outliers = items.filter((item) => item.alignment_status === "alignment_outlier").length;
  return `
    <div class="summary-card ${unmatched || outliers ? "warn" : "ok"}">
      <h3>${data.archived ? "旧控制点已归档" : "迁移诊断已生成"}</h3>
      <div class="result-grid">
        ${resultRow("文件", data.migration_report || data.written_to)}
        ${resultRow("诊断点数", items.length)}
        ${resultRow("不匹配", unmatched)}
        ${resultRow("配准外点", outliers)}
      </div>
      ${data.legacy_file ? `<p class="result-next">归档文件：${escapeHtml(data.legacy_file)}</p>` : ""}
      <p class="result-next">诊断只帮助判断旧点能否参考；正式控制点仍需在 S2 页面重新保存。</p>
    </div>
  `;
}

function summarizeCadPreview(data) {
  const boundary = data.selected_boundary || {};
  const candidates = data.candidates || [];
  const semanticStatus = data.candidate_semantics_status || data.cad_semantics?.status || "未生成";
  const locationImages = data.candidate_semantics_location_images || [];
  const findings = data.candidate_semantics_global_findings || [];
  const userPick = data.candidate_semantics_needs_user_pick || [];
  return `
    <div class="summary-card ${data.status === "ok" ? "ok" : "warn"}">
      <h3>${data.status === "ok" ? "CAD 预览已生成" : "CAD 预览生成失败"}</h3>
      <div class="result-grid">
        ${resultRow("源 DXF", data.source_dxf)}
        ${resultRow("红线候选", boundary.handle ? `${boundary.handle} / ${boundary.layer}` : "未识别")}
        ${resultRow("候选控制点", `${candidates.length} 个`)}
        ${resultRow("语义建议", semanticStatus)}
        ${resultRow("综合视觉参考", locationImages.length ? `CAD + ${locationImages.length} 张区位/卫星图` : "仅 CAD")}
        ${resultRow("预览文件", data.preview_svg)}
      </div>
      ${findings.length ? `<p class="result-next">${compactList(findings, 2)}</p>` : ""}
      ${userPick.length ? `<p class="result-warning">${compactList(userPick, 2)}</p>` : ""}
      <p class="result-next">${data.status === "ok" ? "S2 页面已加载 CAD 底图。点击候选点的“地图拾取”，再在高德地图上点选对应位置。" : escapeHtml(data.error || data.stderr || "请检查 DWG/DXF 是否可转换。")}</p>
    </div>
  `;
}

function summarizeUpload(data) {
  return `
    <div class="summary-card ok">
      <h3>上传完成</h3>
      <div class="result-grid">
        ${resultRow("项目", data.project)}
        ${resultRow("分类", BUCKET_LABELS[data.bucket] || data.bucket)}
        ${resultRow("保存数量", data.count)}
        ${resultRow("目标目录", data.target_dir)}
      </div>
      <p class="result-next">${data.count ? "已写入项目目录，可继续运行 Inventory。" : "没有保存文件，请确认已选择文件。"}</p>
    </div>
  `;
}

function summarizeAutoDraft(data) {
  return `
    <div class="summary-card ${data.ok ? "ok" : "warn"}">
      <h3>${data.ok ? "S1 区位分析草稿已生成" : "区位分析草稿生成失败"}</h3>
      <div class="result-grid">
        ${resultRow("项目", data.project_code)}
        ${resultRow("Markdown 文件", data.path || "无")}
        ${resultRow("结构化 JSON", data.json_path || "无")}
      </div>
      ${data.summary ? `<div class="result-section"><b>摘要</b><p>${escapeHtml(data.summary)}</p></div>` : ""}
      ${data.structured_preview ? `<div class="result-section"><b>结构化草稿预览</b><pre style="white-space:pre-wrap;font-size:12px;max-height:400px;overflow:auto;background:rgba(255,253,247,.72);padding:8px;border-radius:6px;border:1px solid var(--line)">${escapeHtml(data.structured_preview)}</pre></div>` : ""}
      ${data.markdown_preview ? `<div class="result-section"><b>Markdown 预览</b><pre style="white-space:pre-wrap;font-size:12px;max-height:300px;overflow:auto;background:rgba(255,253,247,.72);padding:8px;border-radius:6px;border:1px solid var(--line)">${escapeHtml(data.markdown_preview)}</pre></div>` : ""}
      <p class="result-next">${data.ok ? "草稿已保存：Markdown（05_output/s1_location_analysis.md）+ 结构化 JSON（05_output/s1_location_draft.json）。" : escapeHtml(data.error || "请先生成 S1 高德上下文。")}</p>
    </div>
  `;
}

function summarizeGeneric(data) {
  if (typeof data === "string") {
    return `<div class="summary-card warn"><h3>提示</h3><p>${escapeHtml(data)}</p></div>`;
  }
  if (data.project_dir && "s0_ready" in data) return summarizeInventory(data);
  if (data.stats || Array.isArray(data.issues)) return summarizeValidate(data);
  if (data.provider?.name === "amap_webservice" && "location" in data) return summarizeAmap(data);
  if ("amap_context_exists" in data) return summarizeSpatial(data);
  if ("preview_svg" in data && "candidates" in data) return summarizeCadPreview(data);
  if ("control_points" in data && "count" in data && data.path) return summarizeControlPoints(data);
  if ("migration" in data || (Array.isArray(data.items) && "candidate_set_id_current" in data)) return summarizeMigration(data);
  if ("saved" in data && "bucket" in data) return summarizeUpload(data);
  if ("auto_draft" in data) return summarizeAutoDraft(data);
  if (data.provider?.name === "amap_webservice" && !("location" in data)) {
    return `
      <div class="summary-card ${data.provider.configured ? "ok" : "warn"}">
        <h3>${data.provider.configured ? "高德 Key 可用" : "高德 Key 未配置"}</h3>
        <p class="result-next">${data.provider.configured ? `使用环境变量：${escapeHtml(data.provider.key_env)}` : "请在 .env 中配置 AMAP_WEBSERVICE_KEY。"}</p>
      </div>
    `;
  }
  return `<div class="summary-card ok"><h3>操作完成</h3><p class="result-next">详情见下方 JSON。</p></div>`;
}

function writeOutput(data) {
  output.innerHTML = `${summarizeGeneric(data)}${typeof data === "string" ? "" : detailsJson(data)}`;
  $("#resultHint").textContent = new Date().toLocaleTimeString();
}

function typedProjectCode() {
  return $("#projectCode").value.trim();
}

function activeProject() {
  const typed = typedProjectCode();
  if (!state.project) throw new Error("请先创建或选择项目");
  if (typed && typed !== state.project) {
    throw new Error(`当前输入为 ${typed}，但打开的项目仍是 ${state.project}。请先点击“创建/打开项目”。`);
  }
  return state.project;
}

async function api(path, options = {}) {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) {
    const error = new Error(data.error || data.stderr || data.status || "请求失败");
    error.status = response.status;
    error.data = data;
    throw error;
  }
  return data;
}

function canOpenPage(page) {
  return page === "project" || Boolean(state.project);
}

function syncUrlState() {
  const url = new URL(window.location.href);
  if (state.project) url.searchParams.set("project", state.project);
  else url.searchParams.delete("project");
  url.searchParams.set("page", state.page);
  window.history.replaceState({}, "", url);
}

function notifyUploaderState() {
  window.dispatchEvent(
    new CustomEvent("uploader:state", {
      detail: { project: state.project, page: state.page },
    }),
  );
}

function setPage(page, options = {}) {
  const next = PAGES.includes(page) ? page : "project";
  state.page = canOpenPage(next) ? next : "project";
  if (options.syncUrl !== false) syncUrlState();
  setControls();
  notifyUploaderState();
}

function setTab(id, mode) {
  const el = $(id);
  el.classList.remove("active", "ready", "locked");
  el.classList.add(mode);
}

function clearFileInputs() {
  document.querySelectorAll(".bucket input").forEach((input) => {
    input.value = "";
  });
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
      setPage("s0");
      runInventory().catch((err) => writeOutput(err.message));
      loadSpatial().catch((err) => writeOutput(err.message));
      loadCadPreview().catch((err) => writeOutput(err.message));
    });
    list.appendChild(chip);
  });
}

function setActiveProject(code, options = {}) {
  const { clearFiles = true, resetInventory = true } = options;
  state.project = code;
  if (resetInventory) state.inventory = null;
  if (resetInventory) state.cadPreview = null;
  if (resetInventory) state.alignment = null;
  if (resetInventory) state.candidateSetIdCurrent = null;
  if (resetInventory) state.candidateSetIdAtSave = null;
  if (resetInventory) state.controlPointsSaved = false;
  if (resetInventory) state.controlPointsStale = false;
  if (resetInventory) state.migrationReport = null;
  if (resetInventory) state.s1Location = "";
  if (resetInventory) {
    state.amap.activeCandidateId = "";
    clearS2Markers();
  }
  if (code) $("#projectCode").value = code;
  if (clearFiles) clearFileInputs();
  renderProjectList();
  syncUrlState();
  setControls();
  notifyUploaderState();
}

const PAGE_META = {
  project: { title: "创建或选择项目", badge: "项目", crumb: "Architecture Design / Project" },
  s0: { title: "S0 建档输入", badge: "S0", crumb: "Architecture Design / S0 Intake" },
  s1: { title: "S1 区位输入", badge: "S1", crumb: "Architecture Design / S1 Location" },
  s2: { title: "S2 地形与配准输入", badge: "S2", crumb: "Architecture Design / S2 Terrain" },
  workbench: { title: "图纸工作台", badge: "图纸", crumb: "Architecture Design / Drawing Studio" },
  status: { title: "项目检查", badge: "状态", crumb: "Architecture Design / Status" },
};

function updateStudioChrome() {
  const meta = PAGE_META[state.page] || PAGE_META.project;
  const crumb = $("#studioCrumb");
  if (crumb) crumb.textContent = state.project ? `${state.project} / ${meta.crumb.split(" / ").pop()}` : meta.crumb;
  const title = $("#studioTitle");
  if (title) title.textContent = meta.title;
  const badge = $("#studioPageBadge");
  if (badge) badge.textContent = meta.badge;
}

function setControls() {
  const typed = typedProjectCode();
  const mismatch = Boolean(state.project && typed && typed !== state.project);
  const hasProject = Boolean(state.project && !mismatch);
  if (!hasProject && state.page !== "project") state.page = "project";

  $("#activeProject").textContent = state.project ? `当前项目：${state.project}` : "未选择项目";
  if (mismatch) {
    $("#projectHint").textContent = `当前输入为 ${typed}，但打开的项目仍是 ${state.project}。请先点击“创建/打开项目”。`;
  } else {
    $("#projectHint").textContent = hasProject
      ? `已打开 ${state.project}。可以直接进入 S0、S1 或 S2 的输入页。`
      : "请先创建新项目，或从下方已有项目中选择一个。";
  }
  $("#s0Hint").textContent = hasProject
    ? `当前 S0 输入会写入 ${state.project}。上传后可直接执行 S0。`
    : "等待项目创建或选择。";

  document.querySelectorAll(".page").forEach((pageEl) => {
    pageEl.classList.toggle("active", pageEl.dataset.page === state.page);
  });
  $(".studio-pages")?.classList.toggle("workbench-active", state.page === "workbench");

  document.querySelectorAll("[data-page].stage-tab").forEach((tab) => {
    tab.disabled = !canOpenPage(tab.dataset.page);
  });

  document.querySelectorAll(".bucket").forEach((bucketEl) => {
    bucketEl.classList.toggle("locked", !hasProject);
    bucketEl.querySelector("input").disabled = !hasProject;
    bucketEl.querySelector("button").disabled = !hasProject;
  });

  [
    "#runInventory",
    "#runValidate",
    "#runInventoryStatus",
    "#runValidateStatus",
    "#checkAmap",
    "#saveCenter",
    "#runCadPreview",
    "#cadZoomOut",
    "#cadZoomReset",
    "#cadZoomIn",
    "#saveControlPoints",
  ].forEach((selector) => {
    $(selector).disabled = !hasProject;
  });
  $("#saveControlPoints").disabled = !hasProject || hasStaleControlPoints();
  applyCadPreviewZoom();
  ["#centerLocation"].forEach((selector) => {
    $(selector).disabled = !hasProject;
  });

  setTab("#tabProject", state.page === "project" ? "active" : hasProject ? "ready" : "active");
  setTab("#tabS0", !hasProject ? "locked" : state.page === "s0" ? "active" : "ready");
  setTab("#tabS1", !hasProject ? "locked" : state.page === "s1" ? "active" : "ready");
  setTab("#tabS2", !hasProject ? "locked" : state.page === "s2" ? "active" : "ready");
  setTab("#tabWorkbench", !hasProject ? "locked" : state.page === "workbench" ? "active" : "ready");
  setTab("#tabStatus", !hasProject ? "locked" : state.page === "status" ? "active" : "ready");

  updateBucketStates();
  renderStaleBanner();
  renderControlPoints();
  renderCadPreview();
  renderAlignment();
  syncAmapUi();
  updateStudioChrome();
}

function renderStaleBanner() {
  const banner = $("#controlPointStaleBanner");
  if (!banner) return;
  refreshStaleState();
  if (!state.controlPointsStale) {
    banner.hidden = true;
    banner.innerHTML = "";
    return;
  }
  banner.hidden = false;
  banner.innerHTML = `
    <strong>旧控制点与当前 CAD 候选集不匹配</strong>
    <p>当前候选集：${escapeHtml(candidateSetShort(state.candidateSetIdCurrent))}；旧控制点保存时：${escapeHtml(candidateSetShort(state.candidateSetIdAtSave))}。这些点可能已经串号，保存和配准会被阻止。</p>
    <div class="stale-actions">
      <button type="button" id="generateMigrationReport">生成迁移诊断</button>
      <button type="button" id="archiveControlPoints" class="primary">归档旧控制点</button>
    </div>
  `;
  $("#generateMigrationReport").addEventListener("click", () => generateMigrationReport().catch((err) => writeOutput(err.message)));
  $("#archiveControlPoints").addEventListener("click", () => archiveControlPoints().catch((err) => writeOutput(err.message)));
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
    if (!state.project) stateEl.textContent = "先创建/选择项目";
    else if (selected > 0) stateEl.textContent = `已选择 ${selected} 个文件，尚未上传`;
    else if (uploaded > 0) stateEl.textContent = `已入库 ${uploaded} 个文件`;
    else stateEl.textContent = bucket === "location_map" ? "未上传，S0/S1 会被阻塞" : "未上传";
  });
}

async function loadProjects() {
  const data = await api("/api/projects");
  state.projects = data.projects;
  let shouldRefreshProjectData = false;
  if (state.pendingUrlProject) {
    const requested = state.pendingUrlProject;
    state.pendingUrlProject = "";
    if (state.projects.some((project) => project.code === requested)) {
      state.project = requested;
      $("#projectCode").value = requested;
      state.inventory = null;
      state.controlPoints = [];
      state.cadPreview = null;
      state.alignment = null;
      state.candidateSetIdCurrent = null;
      state.candidateSetIdAtSave = null;
      state.controlPointsSaved = false;
      state.controlPointsStale = false;
      state.migrationReport = null;
      state.s1Location = "";
      state.amap.activeCandidateId = "";
      clearS2Markers();
      state.page = PAGES.includes(requestedStagePage) ? requestedStagePage : "s0";
      clearFileInputs();
      shouldRefreshProjectData = true;
    } else {
      writeOutput(`URL 中的项目 ${requested} 不存在。请先创建/打开项目。`);
      state.project = "";
      state.page = "project";
      syncUrlState();
    }
  }
  renderProjectList();
  setControls();
  notifyUploaderState();
  if (shouldRefreshProjectData) await runInventory();
  if (shouldRefreshProjectData) await loadSpatial();
  if (shouldRefreshProjectData) await loadCadPreview();
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
  setPage("s0");
  await runInventory();
  await loadSpatial();
  await loadCadPreview();
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
  if (bucket === "topography" && data.saved?.some((path) => /\.(dwg|dxf)$/i.test(path))) {
    await runCadPreview();
  }
}

async function runInventory() {
  const code = activeProject();
  const data = await api(`/api/inventory?project=${encodeURIComponent(code)}`);
  state.inventory = data;
  const text = data.s0_ready ? "S0 gate 已通过" : "缺少区位图";
  $("#gateStatus").textContent = text;
  $("#statusGate").textContent = text;
  $("#gateStatus").style.color = data.s0_ready ? "#1f6f5b" : "#b94b2f";
  $("#statusGate").style.color = data.s0_ready ? "#1f6f5b" : "#b94b2f";
  writeOutput(data);
  setControls();
}

async function runValidate() {
  const code = activeProject();
  const data = await api(`/api/validate?project=${encodeURIComponent(code)}`);
  writeOutput(data);
}

function setAmapStatus(text, ok = null) {
  const el = $("#amapStatus");
  el.textContent = text;
  el.style.color = ok === null ? "" : ok ? "#1f6f5b" : "#b94b2f";
}

function parseLocationInput(value) {
  const parts = value.replace("，", ",").split(",").map((part) => part.trim());
  if (parts.length !== 2 || !parts[0] || !parts[1]) throw new Error("坐标格式应为：经度,纬度");
  const lng = Number(parts[0]);
  const lat = Number(parts[1]);
  if (!Number.isFinite(lng) || !Number.isFinite(lat) || lng < -180 || lng > 180 || lat < -90 || lat > 90) {
    throw new Error("坐标数值超出范围");
  }
  return `${lng},${lat}`;
}

async function checkAmap() {
  activeProject();
  const data = await api("/api/amap-check");
  const configured = Boolean(data.provider?.configured);
  setAmapStatus(configured ? "高德 Key 可用" : "未配置高德 Key", configured);
  writeOutput(data);
}

async function saveCenter() {
  const code = activeProject();
  const location = parseLocationInput($("#centerLocation").value.trim());
  state.s1Location = location;
  setAmapStatus("正在生成高德上下文...", null);
  const data = await api("/api/amap-context", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project: code, location }),
  });
  const ok = data.status === "ok";
  setAmapStatus(ok ? "已生成高德上下文" : data.status || "生成失败", ok);
  writeOutput(data);
  await loadSpatial();
}

async function autoDraftS1() {
  const code = activeProject();
  if (!code) {
    setAmapStatus("请先打开或创建项目", false);
    return;
  }
  setAmapStatus("正在生成区位分析草稿...", null);
  const data = await api("/api/s1/auto-draft", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project: code }),
  });
  setAmapStatus(data.ok ? "区位分析草稿已生成" : data.error || "生成失败", data.ok);
  writeOutput(data);
}

async function loadSpatial() {
  if (!state.project) return;
  const data = await api(`/api/spatial?project=${encodeURIComponent(state.project)}`);
  state.candidateSetIdCurrent = data.candidate_set_id_current || state.candidateSetIdCurrent;
  state.candidateSetIdAtSave = data.candidate_set_id_at_save || null;
  state.controlPointsSaved = Boolean(data.control_points_exists);
  state.controlPointsStale = Boolean(data.control_points_stale);
  const existing = data.control_points || [];
  state.controlPoints = existing.map((point) => ({
    label: point.label || "",
    cad_x: point.cad_point?.x ?? "",
    cad_y: point.cad_point?.y ?? "",
    amap_location: Array.isArray(point.amap_gcj02) ? point.amap_gcj02.join(",") : "",
    feature_type: point.feature_type || "redline_corner",
    feature_name: point.feature_name || "",
    purpose: point.purpose || "registration",
    confidence: point.confidence || "medium",
    note: point.note || "",
  }));
  state.alignment = data.alignment_report || null;
  if (data.amap_context?.location?.amap_gcj02) {
    state.s1Location = data.amap_context.location.amap_gcj02;
    $("#centerLocation").value = state.s1Location;
    setAmapStatus(`已有上下文：${data.amap_context.location.confidence || "unknown"}`, true);
  }
  refreshStaleState();
  renderStaleBanner();
  renderControlPoints();
  renderAlignment();
  syncAmapUi();
  if (!state.alignment && state.controlPoints.length >= 3 && !state.controlPointsStale) scheduleAlignmentCheck();
}

function alignmentPayload() {
  return {
    project: activeProject(),
    candidate_set_id_at_save: state.candidateSetIdCurrent,
    control_points: state.controlPoints,
  };
}

function scheduleAlignmentCheck() {
  window.clearTimeout(state.alignmentTimer);
  if (hasStaleControlPoints()) {
    state.alignment = { status: "stale_control_points" };
    renderStaleBanner();
    renderAlignment();
    renderControlPoints();
    return;
  }
  if (state.controlPoints.length < 3) {
    state.alignment = null;
    renderAlignment();
    renderControlPoints();
    return;
  }
  state.alignment = { status: "pending" };
  renderAlignment();
  state.alignmentTimer = window.setTimeout(() => {
    checkAlignment().catch((err) => {
      state.alignment = { status: "error", error: err.message };
      renderAlignment();
    });
  }, 250);
}

async function checkAlignment() {
  if (!state.project || state.controlPoints.length < 3) return;
  const data = await api("/api/alignment-check", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(alignmentPayload()),
  });
  state.alignment = data;
  renderAlignment();
  renderControlPoints();
}

function renderAlignment() {
  const panel = $("#alignmentPanel");
  if (!panel) return;
  panel.classList.remove("ok", "warn");
  if (state.controlPoints.length < 3) {
    panel.innerHTML = `
      <b>配准检查</b>
      <p>已加入 ${state.controlPoints.length} 个点。至少 3 个点后自动检查残差。</p>
    `;
    return;
  }
  const alignment = state.alignment;
  if (!alignment || alignment.status === "pending") {
    panel.innerHTML = `
      <b>配准检查</b>
      <p>正在等待自动检查...</p>
    `;
    return;
  }
  if (alignment.status === "error") {
    panel.classList.add("warn");
    panel.innerHTML = `
      <b>配准检查</b>
      <p>${escapeHtml(alignment.error || "检查失败")}</p>
    `;
    return;
  }
  if (alignment.status === "stale_control_points" || hasStaleControlPoints()) {
    panel.classList.add("warn");
    panel.innerHTML = `
      <b>配准检查：旧控制点已过期</b>
      <p>当前候选集和旧控制点保存时的候选集不一致。先生成迁移诊断或归档旧点，再重新加入并保存控制点。</p>
    `;
    return;
  }
  const best = alignment.best_fit || {};
  const outliers = best.outlier_labels || [];
  const inliers = best.inlier_labels || [];
  const ok = alignment.quality === "aligned_high" || (alignment.quality === "aligned_partial" && !outliers.length);
  panel.classList.add(ok ? "ok" : "warn");
  const issueRows = outliers
    .map((label) => `<p><b>${escapeHtml(label)}</b>：${escapeHtml(residualNote(alignment, label))}</p>`)
    .join("");
  const duplicateRows = (alignment.duplicates || [])
    .map((item) => `<p>重复高德坐标：${compactList(item.labels, 8)} 共用 ${escapeHtml(item.amap_gcj02?.join(",") || "")}</p>`)
    .join("");
  panel.innerHTML = `
    <b>配准检查：${escapeHtml(qualityText(alignment.quality))}</b>
    <div class="alignment-stats">
      <div><span>控制点</span><b>${alignment.point_count || state.controlPoints.length} 个</b></div>
      <div><span>内点</span><b>${inliers.length || 0} 个</b></div>
      <div><span>内点 RMS</span><b>${formatMeters(best.rms_error_m)}</b></div>
      <div><span>全点 RMS</span><b>${formatMeters(alignment.all_points_fit?.rms_error_m)}</b></div>
    </div>
    ${outliers.length ? `<p>需复核：${compactList(outliers, 8)}。偏差不一定致命，但不适合做高置信落边。</p>` : `<p>当前点位没有明显外点。</p>`}
    ${issueRows}
    ${duplicateRows}
  `;
}

function projectFileUrl(path) {
  return `/api/project-file?project=${encodeURIComponent(state.project)}&path=${encodeURIComponent(path)}&t=${Date.now()}`;
}

async function loadCadPreview() {
  if (!state.project) return;
  const data = await api(`/api/cad-preview?project=${encodeURIComponent(state.project)}`);
  state.cadPreview = data.exists ? data : null;
  state.candidateSetIdCurrent = data.candidate_set_id || state.candidateSetIdCurrent;
  refreshStaleState();
  renderStaleBanner();
  renderCadPreview();
  syncAmapUi();
}

async function runCadPreview() {
  const code = activeProject();
  setCadPreviewStatus("正在生成 CAD 预览...", null);
  const data = await api("/api/cad-preview", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project: code }),
  });
  state.cadPreview = data.status === "ok" ? data : null;
  state.candidateSetIdCurrent = data.candidate_set_id || state.candidateSetIdCurrent;
  refreshStaleState();
  renderStaleBanner();
  renderCadPreview();
  syncAmapUi();
  writeOutput(data);
}

function setCadPreviewStatus(text, ok = null) {
  const el = $("#cadPreviewStatus");
  if (!el) return;
  el.textContent = text;
  el.style.color = ok === null ? "" : ok ? "#1f6f5b" : "#b94b2f";
}

function clampCadPreviewZoom(value) {
  return Math.min(3, Math.max(0.5, Number(value) || 1));
}

function applyCadPreviewZoom() {
  const zoom = clampCadPreviewZoom(state.cadPreviewZoom);
  state.cadPreviewZoom = zoom;
  const image = $("#cadPreviewFrame .cad-preview-image");
  if (image) {
    image.style.width = `${Math.round(zoom * 100)}%`;
    image.style.minWidth = `${Math.round(720 * zoom)}px`;
  }
  const ready = Boolean(state.project && state.cadPreview?.preview_svg);
  const out = $("#cadZoomOut");
  const reset = $("#cadZoomReset");
  const zoomIn = $("#cadZoomIn");
  if (out) out.disabled = !ready || zoom <= 0.5;
  if (reset) {
    reset.disabled = !ready;
    reset.textContent = `${Math.round(zoom * 100)}%`;
  }
  if (zoomIn) zoomIn.disabled = !ready || zoom >= 3;
}

function setCadPreviewZoom(value) {
  state.cadPreviewZoom = clampCadPreviewZoom(value);
  applyCadPreviewZoom();
}

function renderCadPreview() {
  const frame = $("#cadPreviewFrame");
  const list = $("#cadCandidateList");
  if (!frame || !list) return;
  frame.innerHTML = "";
  list.innerHTML = "";
  const data = state.cadPreview;
  if (!data?.preview_svg) {
    setCadPreviewStatus("尚未生成 CAD 预览", null);
    frame.innerHTML = `<div class="control-empty">上传 DWG/DXF 后，点击“生成 CAD 预览”。</div>`;
    list.innerHTML = `<div class="control-empty">候选 CAD 控制点会显示在这里。</div>`;
    applyCadPreviewZoom();
    return;
  }
  const semantic = data.candidate_semantics_status ? `，语义：${data.candidate_semantics_status}` : "";
  setCadPreviewStatus(`${(data.candidates || []).length} 个候选点${semantic}`, true);
  const image = document.createElement("img");
  image.className = "cad-preview-image";
  image.alt = "CAD 地形图预览和候选控制点";
  image.src = projectFileUrl(data.preview_svg);
  frame.appendChild(image);
  applyCadPreviewZoom();
  const candidates = data.candidates || [];
  if (!candidates.length) {
    list.innerHTML = `<div class="control-empty">未识别到候选控制点。请先重新生成 CAD 预览或补充更清晰的 CAD/区位资料。</div>`;
    return;
  }
  candidates.forEach((candidate) => {
    const item = document.createElement("div");
    const candidateId = candidate.label || candidate.id;
    item.className = `candidate-item ${state.amap.activeCandidateId === candidateId ? "active" : ""}`;
    const point = candidate.cad_point || {};
    const x = Number(point.x);
    const y = Number(point.y);
    const saved = state.controlPoints.find((row) => row.label === (candidate.label || candidate.id));
    const featureType = candidate.feature_type || saved?.feature_type || "redline_corner";
    const purpose = candidate.purpose || saved?.purpose || "registration";
    const confidence = ["low", "medium", "high"].includes(candidate.confidence || saved?.confidence)
      ? candidate.confidence || saved?.confidence
      : "medium";
    candidate.feature_type = featureType;
    candidate.purpose = purpose;
    candidate.confidence = confidence;
    candidate.amap_location = candidate.amap_location || saved?.amap_location || "";
    const role = candidate.role_label || controlFeatureText(featureType);
    const reason = candidate.reason || candidate.note || "候选点由 CAD 几何生成；如 AI 识别不可用，先作为红线配准点使用。";
    const sourceText = candidate.suggestion_source === "vision_model" ? "视觉识别" : "保守建议";
    const pickedText = candidate.amap_location ? `已选 ${candidate.amap_location}` : "尚未拾取地图点";
    item.innerHTML = `
      <b>${escapeHtml(candidate.label || candidate.id)}</b>
      <span>CAD ${Number.isFinite(x) ? x.toFixed(3) : "?"}, ${Number.isFinite(y) ? y.toFixed(3) : "?"}</span>
      <small><b>${escapeHtml(sourceText)}：</b>${escapeHtml(role)}${candidate.feature_name ? ` / ${escapeHtml(candidate.feature_name)}` : ""}</small>
      <small>${escapeHtml(reason)}</small>
      <div class="candidate-pick">
        <button type="button" data-action="map-pick" ${hasStaleControlPoints() ? "disabled" : ""}>地图拾取</button>
        <span class="candidate-location">${escapeHtml(pickedText)}</span>
      </div>
    `;
    item.querySelector("[data-action='map-pick']").addEventListener("click", () => {
      setActiveCandidate(candidateId);
      scrollToS2Map();
      ensureS2Map()
        .then(() => scrollToS2Map())
        .catch((err) => writeOutput(err.message));
    });
    list.appendChild(item);
  });
}

function addCandidateControlPoint(candidate) {
  if (hasStaleControlPoints()) {
    throw new Error("旧控制点与当前 CAD 候选集不匹配。请先生成迁移诊断或归档旧控制点。");
  }
  const point = candidate.cad_point || {};
  const label = candidate.label || candidate.id || `CP${state.controlPoints.length + 1}`;
  const controlPoint = {
    label,
    feature_type: candidate.feature_type || "redline_corner",
    purpose: candidate.purpose || "registration",
    feature_name: candidate.feature_name || "",
    cad_x: point.x ?? "",
    cad_y: point.y ?? "",
    amap_location: parseLocationInput(String(candidate.amap_location || "").trim()),
    confidence: ["low", "medium", "high"].includes(candidate.confidence) ? candidate.confidence : "medium",
    note: candidate.reason || candidate.note || "",
  };
  const existingIndex = state.controlPoints.findIndex((row) => row.label === label);
  if (existingIndex >= 0) state.controlPoints[existingIndex] = controlPoint;
  else state.controlPoints.push(controlPoint);
  state.amap.activeCandidateId = label;
  renderControlPoints();
  renderCadPreview();
  renderS2Markers();
  updateActiveCandidatePanel();
  scheduleAlignmentCheck();
}

function renderControlPoints() {
  const list = $("#controlList");
  if (!list) return;
  list.innerHTML = "";
  $("#controlStatus").textContent = `${state.controlPoints.length} 个控制点`;
  if (!state.controlPoints.length) {
    const empty = document.createElement("div");
    empty.className = "control-empty";
    empty.textContent = "尚未加入控制点。几何配准可用红线角点；判断道路和入口时应补桥头、道路交叉口、道路边线等语义控制点。";
    list.appendChild(empty);
    clearS2Markers();
    return;
  }
  state.controlPoints.forEach((point, index) => {
    const item = document.createElement("div");
    const outliers = state.alignment?.best_fit?.outlier_labels || [];
    const inliers = state.alignment?.best_fit?.inlier_labels || [];
    item.className = `control-item ${outliers.includes(point.label) ? "warn" : inliers.includes(point.label) ? "ok" : ""}`;
    const cad = point.cad_x !== "" && point.cad_y !== "" ? `CAD ${point.cad_x}, ${point.cad_y}` : "CAD 待补";
    const note = residualNote(state.alignment, point.label);
    const feature = [controlFeatureText(point.feature_type), point.feature_name].filter(Boolean).join(" / ");
    const purpose = `${controlPurposeText(point.purpose)} · ${controlConfidenceText(point.confidence)}`;
    item.innerHTML = `
      <b>${escapeHtml(point.label || `CP${index + 1}`)}</b>
      <span>${escapeHtml(feature)}</span>
      <span>${escapeHtml(cad)}</span>
      <span>AMap ${escapeHtml(point.amap_location)}</span>
      <small>${escapeHtml(purpose)}</small>
      ${point.note ? `<small>${escapeHtml(point.note)}</small>` : ""}
      ${note ? `<small>${escapeHtml(note)}</small>` : ""}
    `;
    const remove = document.createElement("button");
    remove.type = "button";
    remove.textContent = "删除";
    remove.addEventListener("click", () => {
      state.controlPoints.splice(index, 1);
      renderControlPoints();
      scheduleAlignmentCheck();
    });
    item.appendChild(remove);
    list.appendChild(item);
  });
  renderS2Markers();
}

async function generateMigrationReport() {
  const code = activeProject();
  const data = await api("/api/control-points/migration-report", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project: code }),
  });
  state.migrationReport = data.migration || data;
  writeOutput(data);
}

async function archiveControlPoints() {
  const code = activeProject();
  const data = await api("/api/control-points/archive", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ project: code }),
  });
  state.migrationReport = data.migration || data;
  state.controlPoints = [];
  state.candidateSetIdAtSave = null;
  state.controlPointsSaved = false;
  state.controlPointsStale = false;
  state.alignment = null;
  state.amap.activeCandidateId = "";
  clearS2Markers();
  updateActiveCandidatePanel();
  writeOutput(data);
  await loadSpatial();
  await loadCadPreview();
}

async function saveControlPoints() {
  const code = activeProject();
  if (!state.candidateSetIdCurrent) {
    throw new Error("请先生成 CAD 预览，获得当前 candidate_set_id 后再保存控制点。");
  }
  if (hasStaleControlPoints()) {
    throw new Error("旧控制点与当前 CAD 候选集不匹配。请先生成迁移诊断或归档旧控制点。");
  }
  const data = await api("/api/control-points", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      project: code,
      candidate_set_id_at_save: state.candidateSetIdCurrent,
      control_points: state.controlPoints,
    }),
  });
  writeOutput(data);
  state.candidateSetIdAtSave = state.candidateSetIdCurrent;
  state.controlPointsSaved = true;
  state.controlPointsStale = false;
  state.alignment = data.alignment || state.alignment;
  renderStaleBanner();
  renderAlignment();
  renderControlPoints();
  renderS2Markers();
  await loadSpatial();
}

function bind() {
  $("#createProject").addEventListener("click", () => createProject().catch((err) => writeOutput(err.message)));
  $("#refreshProjects").addEventListener("click", () => loadProjects().catch((err) => writeOutput(err.message)));
  $("#wbHome")?.addEventListener("click", () => setPage("project"));
  $("#runInventory").addEventListener("click", () => { setPage("status"); runInventory().catch((err) => writeOutput(err.message)); });
  $("#runValidate").addEventListener("click", () => { setPage("status"); runValidate().catch((err) => writeOutput(err.message)); });
  $("#runInventoryStatus").addEventListener("click", () => runInventory().catch((err) => writeOutput(err.message)));
  $("#runValidateStatus").addEventListener("click", () => runValidate().catch((err) => writeOutput(err.message)));
  $("#checkAmap").addEventListener("click", () => checkAmap().catch((err) => writeOutput(err.message)));
  $("#runCadPreview").addEventListener("click", () => runCadPreview().catch((err) => {
    setCadPreviewStatus("生成失败", false);
    writeOutput(err.message);
  }));
  $("#cadZoomOut").addEventListener("click", () => setCadPreviewZoom(state.cadPreviewZoom - 0.25));
  $("#cadZoomReset").addEventListener("click", () => setCadPreviewZoom(1));
  $("#cadZoomIn").addEventListener("click", () => setCadPreviewZoom(state.cadPreviewZoom + 0.25));
  $("#saveCenter").addEventListener("click", () => saveCenter().catch((err) => {
    setAmapStatus("生成失败", false);
    writeOutput(err.message);
  }));
  $("#autoDraftS1").addEventListener("click", () => autoDraftS1().catch((err) => {
    setAmapStatus("草稿生成失败", false);
    writeOutput(err.message);
  }));
  $("#centerLocation").addEventListener("change", () => {
    const parsed = parsedLocation($("#centerLocation").value);
    if (parsed) {
      state.s1Location = parsed.location;
      ensureS1Map().catch((err) => writeOutput(err.message));
      ensureS2Map().catch((err) => writeOutput(err.message));
    }
  });
  $("#saveControlPoints").addEventListener("click", () => saveControlPoints().catch((err) => writeOutput(err.message)));
  $("#projectCode").addEventListener("input", () => {
    if ($("#projectCode").value.trim() !== state.project) {
      setActiveProject("", { clearFiles: true, resetInventory: true });
      setPage("project");
    }
  });

  document.querySelectorAll("[data-page].stage-tab").forEach((tab) => {
    tab.addEventListener("click", () => setPage(tab.dataset.page));
  });
  document.querySelectorAll("[data-goto]").forEach((button) => {
    button.addEventListener("click", () => setPage(button.dataset.goto));
  });
  document.querySelectorAll(".bucket").forEach((bucketEl) => {
    const bucket = bucketEl.dataset.bucket;
    const input = bucketEl.querySelector("input");
    const button = bucketEl.querySelector("button");
    input.addEventListener("change", updateBucketStates);
    button.addEventListener("click", () => upload(bucket, input).catch((err) => writeOutput(err.message)));
  });
}

window.architectureUploader = {
  getProject: () => state.project,
  getPage: () => state.page,
  api,
};

if (!PAGES.includes(state.page)) state.page = "project";
bind();
setControls();
notifyUploaderState();
loadProjects().catch((err) => writeOutput(err.message));
