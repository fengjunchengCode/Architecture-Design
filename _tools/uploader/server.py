#!/usr/bin/env python3
"""Local upload UI for architecture project intake."""
from __future__ import annotations

import argparse
import json
import mimetypes
import os
import re
import subprocess
import sys
import tempfile
import time
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote_to_bytes, urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"
PROJECTS_DIR = REPO_ROOT / "projects"
ENV_FILE = REPO_ROOT / ".env"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from _tools.drawing_workbench.registry import (
    DRAWING_REGISTRY,
    DRAWING_TYPES,
    OBJECT_TYPE_REGISTRY,
    default_base_path_for,
    default_object_style,
)
from _tools.drawing_workbench.schema import (
    drawing_output_paths,
    empty_drawing,
    normalize_drawing,
)
from _tools.drawing_workbench.style_schema import validate_style_spec
from _tools.drawing_workbench.svg_to_png import export_svg
from _tools.drawing_workbench.task_pack import build_task_pack

CODE_REGEX = re.compile(r"^\d{2}-[A-Z]{2,3}-[A-Za-z0-9]{2,8}$")
VALID_TYPES = {
    "school",
    "residential",
    "commercial",
    "park",
    "street_scape",
    "renovation",
    "hospital",
    "cultural",
    "industrial",
    "cultural_tourism",
    "unknown",
}

BUCKETS = {
    "briefing": "01_briefing",
    "location_map": "02_site/区位图",
    "topography": "02_site/地形图",
    "site_photo": "02_site/现场照片",
    "reference": "03_references",
    "chat": "04_chat",
}
CAD_SEMANTICS_REL = Path("05_output/cad/control_point_candidate_semantics.json")
CAD_CANDIDATES_REL = Path("05_output/cad/control_point_candidates.json")
CONTROL_POINTS_REL = Path("05_output/amap/control_points.json")

CONTROL_FEATURE_TYPES = {
    "redline_corner",
    "road_intersection",
    "road_centerline",
    "road_edge",
    "bridge_endpoint",
    "bridge_center",
    "water_edge",
    "building_corner",
    "visible_landmark",
    "other",
}
CONTROL_PURPOSES = {
    "registration",
    "road_binding",
    "entrance_check",
    "water_binding",
    "reference_only",
}
CONTROL_CONFIDENCE = {"low", "medium", "high"}

AMAP_JSAPI_REFERER_HINT = (
    "AMAP_JSAPI_KEY 需在高德控制台勾选 'Web 端' 并把 referer 白名单加入 "
    "http://127.0.0.1:8765 / http://localhost:8765"
)


def safe_project(code: str) -> str:
    code = code.strip()
    if not CODE_REGEX.match(code):
        raise ValueError("项目代号格式应为 26-SZ-NSXX")
    return code


def project_dir(code: str) -> Path:
    code = safe_project(code)
    path = (PROJECTS_DIR / code).resolve()
    if PROJECTS_DIR.resolve() not in path.parents:
        raise ValueError("项目路径越界")
    return path


def sanitize_filename(name: str) -> str:
    base = Path(name.replace("\\", "/")).name.strip()
    base = re.sub(r"[\x00-\x1f<>:\"|?*]", "_", base)
    base = base.strip(" .")
    return base or "upload.bin"


def unique_path(directory: Path, filename: str) -> Path:
    target = directory / filename
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    index = 2
    while True:
        candidate = directory / f"{stem}_{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def unique_dash_path(directory: Path, filename: str) -> Path:
    target = directory / filename
    if not target.exists():
        return target
    stem = target.stem
    suffix = target.suffix
    index = 1
    while True:
        candidate = directory / f"{stem}-{index}{suffix}"
        if not candidate.exists():
            return candidate
        index += 1


def parse_header_params(value: str) -> dict[str, str]:
    params: dict[str, str] = {}
    parts = value.split(";")
    params[""] = parts[0].strip().lower() if parts else ""
    for part in parts[1:]:
        if "=" not in part:
            continue
        key, raw_value = part.split("=", 1)
        raw_value = raw_value.strip()
        if len(raw_value) >= 2 and raw_value[0] == raw_value[-1] == '"':
            raw_value = raw_value[1:-1].replace(r"\"", '"').replace(r"\\", "\\")
        params[key.strip().lower()] = raw_value
    return params


def decode_header_bytes(value: bytes) -> str:
    for encoding in ("utf-8", "gb18030", "latin-1"):
        try:
            return value.decode(encoding)
        except UnicodeDecodeError:
            continue
    return value.decode("utf-8", errors="replace")


def decode_filename(disposition_params: dict[str, str]) -> str | None:
    encoded = disposition_params.get("filename*")
    if encoded:
        try:
            charset, _, quoted = encoded.split("'", 2)
            return unquote_to_bytes(quoted).decode(charset or "utf-8")
        except (LookupError, UnicodeDecodeError, ValueError):
            pass
    return disposition_params.get("filename")


def iter_multipart_files(content_type: str, body: bytes) -> list[tuple[str, bytes]]:
    boundary = parse_header_params(content_type).get("boundary")
    if not boundary:
        return []
    delimiter = b"--" + boundary.encode("ascii", errors="ignore")
    files: list[tuple[str, bytes]] = []
    for part in body.split(delimiter):
        part = part.strip(b"\r\n")
        if not part or part == b"--":
            continue
        if part.endswith(b"--"):
            part = part[:-2].rstrip(b"\r\n")
        headers_raw, sep, payload = part.partition(b"\r\n\r\n")
        if not sep:
            continue
        headers: dict[str, bytes] = {}
        for line in headers_raw.split(b"\r\n"):
            name, colon, value = line.partition(b":")
            if colon:
                headers[name.decode("ascii", errors="ignore").strip().lower()] = value.strip()
        disposition = headers.get("content-disposition")
        if not disposition:
            continue
        filename = decode_filename(parse_header_params(decode_header_bytes(disposition)))
        if filename:
            files.append((filename, payload))
    return files


def run_tool(args: list[str]) -> tuple[int, str, str]:
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        [sys.executable, *args],
        cwd=REPO_ROOT,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
        env=env,
    )
    return completed.returncode, completed.stdout, completed.stderr


def load_env_file(path: Path = ENV_FILE) -> list[str]:
    if not path.exists():
        return []
    loaded: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key or key in os.environ:
            continue
        os.environ[key] = value.strip().strip('"').strip("'")
        loaded.append(key)
    return loaded


def content_type_for(path: Path) -> str:
    mime = mimetypes.guess_type(str(path))[0] or "application/octet-stream"
    if path.suffix.lower() == ".svg":
        mime = "image/svg+xml"
    if (
        mime.startswith("text/")
        or mime in {"application/javascript", "application/json", "image/svg+xml"}
    ):
        return f"{mime}; charset=utf-8"
    return mime


def read_current_candidate_set_id(proj: Path) -> str | None:
    path = proj / CAD_CANDIDATES_REL
    if not path.exists():
        return None
    data = json.loads(path.read_text(encoding="utf-8"))
    value = data.get("candidate_set_id")
    return str(value) if value else None


def short_candidate_set_id(value: object) -> str:
    text = str(value or "").strip()
    if not text:
        return "unknown"
    if ":" in text:
        text = text.split(":", 1)[1]
    text = re.sub(r"[^0-9a-fA-F]", "", text)
    return text[:16] or "unknown"


class UploaderHandler(BaseHTTPRequestHandler):
    server_version = "ArchitectureUploader/0.1"

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/projects":
                self.handle_projects()
            elif parsed.path == "/api/inventory":
                self.handle_inventory(parsed.query)
            elif parsed.path == "/api/validate":
                self.handle_validate(parsed.query)
            elif parsed.path == "/api/amap-check":
                self.handle_amap_check()
            elif parsed.path == "/api/amap-jsapi-config":
                self.handle_amap_jsapi_config()
            elif parsed.path == "/api/spatial":
                self.handle_spatial(parsed.query)
            elif parsed.path == "/api/cad-preview":
                self.handle_cad_preview(parsed.query, run=False)
            elif parsed.path == "/api/drawing/registry":
                self.handle_drawing_registry()
            elif parsed.path == "/api/drawing/load":
                self.handle_drawing_load(parsed.query)
            elif parsed.path == "/api/drawing/supporting/list":
                self.handle_supporting_list(parsed.query)
            elif parsed.path == "/api/style/load":
                self.handle_style_load(parsed.query)
            elif parsed.path == "/api/project-file":
                self.serve_project_file(parsed.query)
            else:
                self.serve_static(parsed.path)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        try:
            if parsed.path == "/api/projects":
                self.handle_create_project()
            elif parsed.path == "/api/upload":
                self.handle_upload(parsed.query)
            elif parsed.path == "/api/amap-context":
                self.handle_amap_context()
            elif parsed.path == "/api/control-points":
                self.handle_control_points()
            elif parsed.path == "/api/control-points/archive":
                self.handle_control_points_archive(archive=True)
            elif parsed.path == "/api/control-points/migration-report":
                self.handle_control_points_archive(archive=False)
            elif parsed.path == "/api/cad-candidate-semantics":
                self.handle_cad_candidate_semantics()
            elif parsed.path == "/api/alignment-check":
                self.handle_alignment_check()
            elif parsed.path == "/api/cad-preview":
                self.handle_cad_preview("", run=True)
            elif parsed.path == "/api/drawing/base/upload":
                self.handle_drawing_base_upload(parsed.query)
            elif parsed.path == "/api/drawing/save":
                self.handle_drawing_save()
            elif parsed.path == "/api/drawing/supporting/upload":
                self.handle_supporting_upload(parsed.query)
            elif parsed.path == "/api/drawing/supporting/update":
                self.handle_supporting_update()
            elif parsed.path == "/api/drawing/supporting/delete":
                self.handle_supporting_delete()
            elif parsed.path == "/api/drawing/task-pack":
                self.handle_drawing_task_pack()
            elif parsed.path == "/api/drawing/export":
                self.handle_drawing_export(parsed.query)
            elif parsed.path == "/api/style/save":
                self.handle_style_save()
            else:
                self.send_json({"error": "not found"}, HTTPStatus.NOT_FOUND)
        except Exception as exc:
            self.send_json({"error": str(exc)}, HTTPStatus.BAD_REQUEST)

    def log_message(self, format: str, *args: object) -> None:
        print(f"[uploader] {self.address_string()} - {format % args}")

    def send_json(self, payload: object, status: HTTPStatus = HTTPStatus.OK) -> None:
        body = json.dumps(payload, ensure_ascii=False, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length)
        return json.loads(raw.decode("utf-8"))

    def serve_static(self, path: str) -> None:
        if path in ("", "/"):
            path = "/index.html"
        rel = path.lstrip("/")
        target = (STATIC_DIR / rel).resolve()
        if STATIC_DIR.resolve() not in target.parents and target != STATIC_DIR.resolve():
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type_for(target))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def serve_project_file(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        rel = str(params.get("path", [""])[0]).replace("\\", "/").lstrip("/")
        if not rel.startswith("05_output/"):
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        proj = project_dir(code)
        target = (proj / rel).resolve()
        output_dir = (proj / "05_output").resolve()
        if output_dir not in target.parents and target != output_dir:
            self.send_error(HTTPStatus.FORBIDDEN)
            return
        if not target.exists() or not target.is_file():
            self.send_error(HTTPStatus.NOT_FOUND)
            return
        content = target.read_bytes()
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", content_type_for(target))
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

    def drawing_paths(self, proj: Path, drawing_type: str) -> dict[str, Path]:
        rels = drawing_output_paths(drawing_type)
        return {key: proj / rel for key, rel in rels.items()}

    def project_file_url(self, code: str, rel_path: str | None) -> str | None:
        if not rel_path:
            return None
        return f"/api/project-file?project={code}&path={rel_path}"

    def default_drawing_for_project(self, code: str, proj: Path, drawing_type: str) -> dict[str, object]:
        base_rel = default_base_path_for(drawing_type)
        width = 1
        height = 1
        base_path = proj / base_rel
        if base_path.exists():
            try:
                from PIL import Image

                with Image.open(base_path) as image:
                    width, height = image.size
            except Exception:
                width = height = 1
        return empty_drawing(
            project_code=code,
            drawing_type=drawing_type,
            base_path=base_rel,
            natural_width=width,
            natural_height=height,
            base_source="user_upload",
        )

    def handle_drawing_registry(self) -> None:
        drawings = {}
        for dt_id, dt_info in DRAWING_REGISTRY.items():
            drawings[dt_id] = {
                "label": dt_info["label"],
                "status": dt_info["status"],
                "category": dt_info["category"],
                "default_base_path": dt_info["default_base_path"],
                "object_types": dt_info["object_types"],
                "tools": dt_info["tools"],
            }
        objects = {}
        for ot_id, ot_info in OBJECT_TYPE_REGISTRY.items():
            objects[ot_id] = {
                "label": ot_info["label"],
                "geometry": ot_info["geometry"],
                "closed": ot_info["closed"],
                "default_style": default_object_style(ot_id),
            }
        self.send_json({
            "ok": True,
            "schema_version": "1.0",
            "default_drawing_type": "functional_zoning",
            "drawings": drawings,
            "objects": objects,
        })

    def handle_supporting_list(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        drawing_type = str(params.get("drawing_type", [""])[0]).strip()
        if drawing_type not in DRAWING_TYPES:
            raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
        proj = project_dir(code)
        manifest_path = proj / "05_output" / "drawings" / "supporting" / drawing_type / "manifest.json"
        if not manifest_path.exists():
            self.send_json({"ok": True, "project": code, "drawing_type": drawing_type, "images": [], "count": 0})
            return
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        images = manifest.get("images", [])
        self.send_json({
            "ok": True,
            "project": code,
            "drawing_type": drawing_type,
            "images": images,
            "count": len(images),
        })

    def handle_supporting_upload(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        drawing_type = str(params.get("drawing_type", [""])[0]).strip()
        if drawing_type not in DRAWING_TYPES:
            raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
        proj = project_dir(code)

        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b""
        files = iter_multipart_files(content_type, body) if "multipart/form-data" in content_type else []
        if not files:
            raise ValueError("请选择图片文件")

        allowed_ext = {".jpg", ".jpeg", ".png", ".webp"}
        sup_dir = proj / "05_output" / "drawings" / "supporting" / drawing_type
        sup_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = sup_dir / "manifest.json"

        if manifest_path.exists():
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        else:
            manifest = {"schema_version": "1.0", "project_code": code, "drawing_type": drawing_type, "updated_at": now_iso(), "images": []}

        saved = []
        for fname, payload in files:
            filename = sanitize_filename(fname)
            suffix = Path(filename).suffix.lower()
            if suffix not in allowed_ext:
                raise ValueError(f"不支持的文件格式: {suffix}")
            out = unique_dash_path(sup_dir, filename)
            out.write_bytes(payload)
            rel = str(out.relative_to(proj)).replace("\\", "/")
            img_id = f"img-{datetime.now().strftime('%Y%m%d-%H%M%S')}-{len(manifest['images'])+1:03d}"
            entry = {
                "id": img_id,
                "file": rel,
                "original_name": filename,
                "caption": "",
                "sort_order": len(manifest["images"]) + 1,
                "notes": "",
                "uploaded_at": now_iso(),
            }
            manifest["images"].append(entry)
            saved.append(entry)

        manifest["updated_at"] = now_iso()
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

        self.send_json({
            "ok": True,
            "project": code,
            "drawing_type": drawing_type,
            "saved": saved,
            "count": len(saved),
        })

    def handle_supporting_update(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        drawing_type = str(payload.get("drawing_type", "")).strip()
        if drawing_type not in DRAWING_TYPES:
            raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
        proj = project_dir(code)
        manifest_path = proj / "05_output" / "drawings" / "supporting" / drawing_type / "manifest.json"
        if not manifest_path.exists():
            raise ValueError("manifest 不存在")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        image_id = str(payload.get("image_id", "")).strip()
        for img in manifest.get("images", []):
            if img.get("id") == image_id:
                if "caption" in payload:
                    img["caption"] = str(payload["caption"])
                if "notes" in payload:
                    img["notes"] = str(payload["notes"])
                if "sort_order" in payload:
                    img["sort_order"] = int(payload["sort_order"])
                break
        else:
            raise ValueError(f"image_id {image_id} not found")
        manifest["updated_at"] = now_iso()
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self.send_json({"ok": True, "project": code, "drawing_type": drawing_type})

    def handle_supporting_delete(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        drawing_type = str(payload.get("drawing_type", "")).strip()
        if drawing_type not in DRAWING_TYPES:
            raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
        proj = project_dir(code)
        manifest_path = proj / "05_output" / "drawings" / "supporting" / drawing_type / "manifest.json"
        if not manifest_path.exists():
            raise ValueError("manifest 不存在")
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        image_id = str(payload.get("image_id", "")).strip()
        sup_dir = proj / "05_output" / "drawings" / "supporting" / drawing_type
        new_images = []
        deleted_file = None
        for img in manifest.get("images", []):
            if img.get("id") == image_id:
                file_path = (proj / img.get("file", "")).resolve()
                if sup_dir.resolve() in file_path.parents and file_path.exists():
                    file_path.unlink()
                    deleted_file = img.get("file")
            else:
                new_images.append(img)
        manifest["images"] = new_images
        manifest["updated_at"] = now_iso()
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        self.send_json({"ok": True, "project": code, "drawing_type": drawing_type, "deleted_file": deleted_file})

    def handle_drawing_load(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        drawing_type = str(params.get("drawing_type", [""])[0]).strip()
        if drawing_type not in DRAWING_TYPES:
            raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
        proj = project_dir(code)
        paths = self.drawing_paths(proj, drawing_type)
        rels = drawing_output_paths(drawing_type)
        semantic_path = paths["semantic"]
        if semantic_path.exists():
            drawing = normalize_drawing(
                json.loads(semantic_path.read_text(encoding="utf-8")),
                project_code=code,
            )
            exists = True
        else:
            drawing = self.default_drawing_for_project(code, proj, drawing_type)
            exists = False

        self.send_json(
            {
                "ok": True,
                "project": code,
                "drawing_type": drawing_type,
                "exists": exists,
                "drawing": drawing,
                "paths": rels,
                "base_image_exists": (proj / drawing["base_image"]["path"]).exists(),
                "base_image_url": self.project_file_url(code, drawing["base_image"]["path"]),
                "svg_exists": paths["svg"].exists(),
                "svg_url": self.project_file_url(code, rels["svg"]) if paths["svg"].exists() else None,
                "png_exists": paths["png"].exists(),
                "png_url": self.project_file_url(code, rels["png"]) if paths["png"].exists() else None,
                "pdf_exists": paths["pdf"].exists(),
                "pdf_url": self.project_file_url(code, rels["pdf"]) if paths["pdf"].exists() else None,
            }
        )

    def handle_drawing_base_upload(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        proj = project_dir(code)
        if not proj.exists():
            raise ValueError("请先创建项目，再上传底图")

        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b""
        files = iter_multipart_files(content_type, body) if "multipart/form-data" in content_type else []
        if not files:
            raise ValueError("请选择 JPG 或 PNG 底图文件")

        fname, payload = files[0]
        filename = sanitize_filename(fname)
        suffix = Path(filename).suffix.lower()
        if suffix not in {".jpg", ".jpeg", ".png"}:
            raise ValueError("底图只支持 JPG/PNG")
        target_dir = proj / "05_output" / "drawings" / "base"
        target_dir.mkdir(parents=True, exist_ok=True)
        out = unique_dash_path(target_dir, filename)
        out.write_bytes(payload)
        rel = str(out.relative_to(proj)).replace("\\", "/")
        self.send_json(
            {
                "ok": True,
                "project": code,
                "path": rel,
                "url": self.project_file_url(code, rel),
                "filename": out.name,
            }
        )

    def handle_drawing_save(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        proj = project_dir(code)
        drawing = normalize_drawing(payload.get("drawing") or payload, project_code=code)
        paths = self.drawing_paths(proj, drawing["drawing_type"])
        paths["semantic"].parent.mkdir(parents=True, exist_ok=True)
        paths["semantic"].write_text(json.dumps(drawing, ensure_ascii=False, indent=2), encoding="utf-8")
        rels = drawing_output_paths(drawing["drawing_type"])
        self.send_json(
            {
                "ok": True,
                "project": code,
                "drawing_type": drawing["drawing_type"],
                "path": rels["semantic"],
                "drawing": drawing,
            }
        )

    def handle_drawing_task_pack(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        drawing_type = str(payload.get("drawing_type") or "").strip()
        if drawing_type not in DRAWING_TYPES:
            raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
        rels = drawing_output_paths(drawing_type)
        pack_path = build_task_pack(
            code,
            drawing_type,
            sketch_path=rels["semantic"],
            user_notes=str(payload.get("user_notes") or ""),
        )
        self.send_json(
            {
                "ok": True,
                "project": code,
                "drawing_type": drawing_type,
                "task_pack": str(pack_path.relative_to(REPO_ROOT)).replace("\\", "/"),
                "task_pack_project_path": str(pack_path.relative_to(project_dir(code))).replace("\\", "/"),
            }
        )

    def handle_drawing_export(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        drawing_type = str(params.get("drawing_type", [""])[0]).strip()
        if drawing_type not in DRAWING_TYPES:
            raise ValueError(f"drawing_type must be one of {sorted(DRAWING_TYPES)}")
        proj = project_dir(code)
        rels = drawing_output_paths(drawing_type)
        svg_path = proj / rels["svg"]
        outputs = export_svg(svg_path, proj / "05_output" / "drawings", formats=("png", "pdf"), dpi=300, page_size="A3")
        rel_outputs = {key: str(path.relative_to(proj)).replace("\\", "/") for key, path in outputs.items()}
        self.send_json(
            {
                "ok": True,
                "project": code,
                "drawing_type": drawing_type,
                "outputs": rel_outputs,
                "urls": {key: self.project_file_url(code, rel) for key, rel in rel_outputs.items()},
            }
        )

    def handle_style_load(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        proj = project_dir(code)
        path = proj / "05_output" / "style" / "style_spec.json"
        rel = "05_output/style/style_spec.json"
        if not path.exists():
            self.send_json({"ok": True, "project": code, "exists": False, "path": rel})
            return
        style_spec = validate_style_spec(json.loads(path.read_text(encoding="utf-8")))
        self.send_json(
            {
                "ok": True,
                "project": code,
                "exists": True,
                "path": rel,
                "style_spec": style_spec,
            }
        )

    def handle_style_save(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        proj = project_dir(code)
        style_spec = validate_style_spec(payload.get("style_spec") or payload)
        path = proj / "05_output" / "style" / "style_spec.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(style_spec, ensure_ascii=False, indent=2), encoding="utf-8")
        rel = "05_output/style/style_spec.json"
        self.send_json(
            {
                "ok": True,
                "project": code,
                "path": rel,
                "style_spec": style_spec,
            }
        )

    def handle_projects(self) -> None:
        PROJECTS_DIR.mkdir(exist_ok=True)
        projects = []
        for path in sorted(PROJECTS_DIR.iterdir()):
            if not path.is_dir():
                continue
            record = path / "05_output" / "record.md"
            projects.append(
                {
                    "code": path.name,
                    "record_exists": record.exists(),
                    "path": str(path.relative_to(REPO_ROOT)),
                }
            )
        self.send_json({"projects": projects})

    def handle_create_project(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("code", "")))
        name = str(payload.get("name") or code).strip()
        project_type = str(payload.get("type") or "unknown")
        if project_type not in VALID_TYPES:
            raise ValueError(f"未知项目类型: {project_type}")
        args = [
            "_tools/init_project/scaffold.py",
            code,
            "--type",
            project_type,
            "--name",
            name,
            "--resume",
        ]
        rc, stdout, stderr = run_tool(args)
        self.send_json(
            {
                "ok": rc == 0,
                "returncode": rc,
                "stdout": stdout,
                "stderr": stderr,
                "project": code,
            },
            HTTPStatus.OK if rc == 0 else HTTPStatus.BAD_REQUEST,
        )

    def handle_upload(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        bucket = params.get("bucket", [""])[0]
        if bucket not in BUCKETS:
            raise ValueError("未知资料分类")
        proj = project_dir(code)
        if not proj.exists():
            raise ValueError("请先创建项目，再上传资料")
        target_dir = proj / BUCKETS[bucket]
        if not target_dir.exists():
            target_dir.mkdir(parents=True, exist_ok=True)

        content_type = self.headers.get("Content-Type", "")
        length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(length) if length > 0 else b""

        saved = []
        if "multipart/form-data" in content_type:
            for fname, payload in iter_multipart_files(content_type, body):
                filename = sanitize_filename(fname)
                out = unique_path(target_dir, filename)
                out.write_bytes(payload)
                saved.append(str(out.relative_to(proj)).replace("\\", "/"))

        self.send_json(
            {
                "ok": True,
                "project": code,
                "bucket": bucket,
                "target_dir": BUCKETS[bucket],
                "saved": saved,
                "count": len(saved),
            }
        )

    def handle_inventory(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        args = ["_tools/inventory.py", code, "--json", "--write"]
        rc, stdout, stderr = run_tool(args)
        payload = json.loads(stdout) if stdout.strip().startswith("{") else {"stdout": stdout}
        payload.update({"ok": rc == 0, "returncode": rc, "stderr": stderr})
        self.send_json(payload, HTTPStatus.OK if rc in (0, 2) else HTTPStatus.BAD_REQUEST)

    def handle_validate(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        args = ["_tools/validate_record.py", code, "--json"]
        rc, stdout, stderr = run_tool(args)
        payload = json.loads(stdout) if stdout.strip().startswith("{") else {"stdout": stdout}
        payload.update({"ok": rc == 0, "returncode": rc, "stderr": stderr})
        self.send_json(payload, HTTPStatus.OK if rc in (0, 2) else HTTPStatus.BAD_REQUEST)

    def handle_amap_check(self) -> None:
        args = ["_tools/amap_context.py", "--check", "--json"]
        rc, stdout, stderr = run_tool(args)
        payload = json.loads(stdout) if stdout.strip().startswith("{") else {"stdout": stdout}
        payload.update({"ok": rc == 0, "returncode": rc, "stderr": stderr})
        self.send_json(payload, HTTPStatus.OK if rc in (0, 2) else HTTPStatus.BAD_REQUEST)

    def handle_amap_jsapi_config(self) -> None:
        loaded_env = load_env_file()
        key = os.environ.get("AMAP_JSAPI_KEY", "").strip()
        service_host = os.environ.get("AMAP_JSAPI_SERVICE_HOST", "").strip()
        security_jscode = os.environ.get("AMAP_JSAPI_SECURITY_JSCODE", "").strip()
        warnings = [AMAP_JSAPI_REFERER_HINT]

        security: dict[str, object] = {"mode": "none"}
        if service_host:
            security = {"mode": "service_host", "service_host": service_host}
        elif security_jscode:
            security = {"mode": "security_jscode", "security_jscode": security_jscode}
        elif key:
            warnings.append("未配置 AMAP_JSAPI_SECURITY_JSCODE 或 AMAP_JSAPI_SERVICE_HOST；若控制台启用安全密钥，地图会加载失败。")

        if not key:
            warnings.append("未配置 AMAP_JSAPI_KEY，内嵌地图不可用；可继续使用外部高德坐标拾取器。")

        self.send_json(
            {
                "ok": True,
                "configured": bool(key),
                "key": key or None,
                "key_env": "AMAP_JSAPI_KEY" if key else None,
                "security": security,
                "warnings": warnings,
                "env_loaded": loaded_env,
            }
        )

    def handle_amap_context(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        location = str(payload.get("location") or "").strip()
        address = str(payload.get("address") or "").strip()
        args = ["_tools/amap_context.py", code, "--json", "--write"]
        if location:
            args.extend(["--location", location])
        elif address:
            args.extend(["--address", address])
        rc, stdout, stderr = run_tool(args)
        result = json.loads(stdout) if stdout.strip().startswith("{") else {"stdout": stdout}
        result.update({"ok": rc == 0 and result.get("status") == "ok", "returncode": rc, "stderr": stderr})
        self.send_json(result, HTTPStatus.OK if rc == 0 else HTTPStatus.BAD_REQUEST)

    def handle_spatial(self, query: str) -> None:
        params = parse_qs(query)
        code = safe_project(params.get("project", [""])[0])
        proj = project_dir(code)
        amap_dir = proj / "05_output" / "amap"
        context_path = amap_dir / "s1_map_context.json"
        control_path = amap_dir / "control_points.json"
        candidate_set_id_current = read_current_candidate_set_id(proj)
        payload: dict[str, object] = {
            "project": code,
            "amap_context_exists": context_path.exists(),
            "control_points_exists": control_path.exists(),
            "candidate_set_id_current": candidate_set_id_current,
            "candidate_set_id_at_save": None,
            "control_points_stale": False,
            "control_points": [],
        }
        if context_path.exists():
            try:
                context = json.loads(context_path.read_text(encoding="utf-8"))
                payload["amap_context"] = {
                    "status": context.get("status"),
                    "location": context.get("location"),
                    "address": (context.get("map_context") or {}).get("regeo", {}).get("formatted_address"),
                    "path": str(context_path.relative_to(proj)).replace("\\", "/"),
                }
            except json.JSONDecodeError as exc:
                payload["amap_context_error"] = str(exc)
        if control_path.exists():
            try:
                saved = json.loads(control_path.read_text(encoding="utf-8"))
                payload["control_points"] = saved.get("control_points", [])
                candidate_set_id_at_save = saved.get("candidate_set_id_at_save")
                payload["candidate_set_id_at_save"] = candidate_set_id_at_save
                payload["control_points_stale"] = bool(
                    candidate_set_id_current and candidate_set_id_at_save != candidate_set_id_current
                )
                payload["control_points_path"] = str(control_path.relative_to(proj)).replace("\\", "/")
            except json.JSONDecodeError as exc:
                payload["control_points_error"] = str(exc)
        alignment_path = amap_dir / "cad_alignment_report.json"
        if alignment_path.exists():
            try:
                payload["alignment_report"] = json.loads(alignment_path.read_text(encoding="utf-8"))
                payload["alignment_report_path"] = str(alignment_path.relative_to(proj)).replace("\\", "/")
            except json.JSONDecodeError as exc:
                payload["alignment_report_error"] = str(exc)
        self.send_json(payload)

    def read_cad_preview_payload(self, proj: Path, code: str) -> dict[str, object]:
        preview_path = proj / "05_output" / "cad" / "site_preview.svg"
        candidate_path = proj / "05_output" / "cad" / "control_point_candidates.json"
        semantics_path = proj / CAD_SEMANTICS_REL
        payload: dict[str, object] = {
            "ok": True,
            "project": code,
            "exists": preview_path.exists() and candidate_path.exists(),
            "preview_svg": "05_output/cad/site_preview.svg" if preview_path.exists() else None,
            "candidate_json": "05_output/cad/control_point_candidates.json" if candidate_path.exists() else None,
            "candidate_semantics": str(CAD_SEMANTICS_REL).replace("\\", "/") if semantics_path.exists() else None,
            "candidates": [],
        }
        if candidate_path.exists():
            try:
                saved = json.loads(candidate_path.read_text(encoding="utf-8"))
                payload.update(saved)
                payload["ok"] = saved.get("status") == "ok"
                payload["exists"] = preview_path.exists()
                if semantics_path.exists():
                    semantics = json.loads(semantics_path.read_text(encoding="utf-8"))
                    payload["candidate_semantics"] = str(CAD_SEMANTICS_REL).replace("\\", "/")
                    payload["candidate_semantics_updated_at"] = semantics.get("updated_at")
                    payload["candidates"] = self.merge_candidate_semantics(
                        payload.get("candidates", []),
                        semantics.get("candidates", []),
                    )
                    payload["candidate_semantics_status"] = semantics.get("status")
                    payload["candidate_semantics_provider"] = semantics.get("provider")
                    payload["candidate_semantics_fallback_reason"] = semantics.get("fallback_reason")
                    payload["candidate_semantics_vision_image"] = semantics.get("vision_image")
                    payload["candidate_semantics_cad_image"] = semantics.get("cad_vision_image")
                    payload["candidate_semantics_location_images"] = semantics.get("location_images", [])
                    vision_result = semantics.get("vision_result") if isinstance(semantics.get("vision_result"), dict) else {}
                    payload["candidate_semantics_global_findings"] = vision_result.get("global_findings", [])
                    payload["candidate_semantics_needs_user_pick"] = vision_result.get("needs_user_pick", [])
            except json.JSONDecodeError as exc:
                payload["ok"] = False
                payload["error"] = str(exc)
        return payload

    def clean_candidate_semantics(self, items: object) -> list[dict[str, object]]:
        if not isinstance(items, list):
            raise ValueError("candidates 必须是数组")
        cleaned = []
        for index, raw in enumerate(items, start=1):
            if not isinstance(raw, dict):
                raise ValueError(f"候选点 {index} 格式错误")
            candidate_id = str(raw.get("id") or raw.get("label") or f"CAD-{index:02d}").strip()
            label = str(raw.get("label") or candidate_id).strip()
            feature_type = str(raw.get("feature_type") or "redline_corner").strip()
            feature_name = str(raw.get("feature_name") or "").strip()
            purpose = str(raw.get("purpose") or "registration").strip()
            confidence = str(raw.get("confidence") or "medium").strip()
            role_label = str(raw.get("role_label") or "").strip()
            reason = str(raw.get("reason") or "").strip()
            suggestion_source = str(raw.get("suggestion_source") or "").strip()
            note = str(raw.get("note") or "").strip()
            if feature_type not in CONTROL_FEATURE_TYPES:
                feature_type = "other"
            if purpose not in CONTROL_PURPOSES:
                purpose = "registration"
            if confidence not in CONTROL_CONFIDENCE:
                confidence = "medium"
            cleaned.append(
                {
                    "id": candidate_id,
                    "label": label,
                    "feature_type": feature_type,
                    "feature_name": feature_name or None,
                    "purpose": purpose,
                    "confidence": confidence,
                    "role_label": role_label or None,
                    "reason": reason or None,
                    "suggestion_source": suggestion_source or None,
                    "note": note or None,
                    "source": "uploader_ui",
                }
            )
        return cleaned

    def merge_candidate_semantics(self, candidates: object, semantics: object) -> list[dict[str, object]]:
        if not isinstance(candidates, list):
            return []
        semantic_rows = semantics if isinstance(semantics, list) else []
        by_key = {}
        for item in semantic_rows:
            if not isinstance(item, dict):
                continue
            for key in (item.get("id"), item.get("label")):
                if key:
                    by_key[str(key)] = item
        merged = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                continue
            row = dict(candidate)
            semantic = by_key.get(str(row.get("id"))) or by_key.get(str(row.get("label")))
            if semantic:
                for field in ("feature_type", "feature_name", "purpose", "confidence", "note", "role_label", "reason", "suggestion_source"):
                    if semantic.get(field) is not None:
                        row[field] = semantic.get(field)
            merged.append(row)
        return merged

    def handle_cad_preview(self, query: str, run: bool) -> None:
        if run:
            payload = self.read_json()
            code = safe_project(str(payload.get("project", "")))
        else:
            params = parse_qs(query)
            code = safe_project(params.get("project", [""])[0])
        proj = project_dir(code)
        if not proj.exists():
            raise ValueError("请先创建项目，再生成 CAD 预览")
        if not run:
            self.send_json(self.read_cad_preview_payload(proj, code))
            return

        probe_rc, probe_stdout, probe_stderr = run_tool(["_tools/dwg_probe.py", code, "--json", "--write"])
        probe = json.loads(probe_stdout) if probe_stdout.strip().startswith("{") else {"stdout": probe_stdout}
        if probe_rc not in (0, 2) or probe.get("status") not in {"ok", "partial"}:
            probe.update({"ok": False, "returncode": probe_rc, "stderr": probe_stderr})
            self.send_json(probe, HTTPStatus.BAD_REQUEST)
            return

        rc, stdout, stderr = run_tool(["_tools/cad_preview.py", code, "--json", "--write"])
        result = json.loads(stdout) if stdout.strip().startswith("{") else {"stdout": stdout}
        semantic_rc = 0
        semantic_stdout = ""
        semantic_stderr = ""
        semantic_payload: dict[str, object] = {}
        if rc == 0 and result.get("status") == "ok":
            semantic_rc, semantic_stdout, semantic_stderr = run_tool(
                ["_tools/cad_semantics.py", code, "--json", "--write", "--timeout", "60"]
            )
            semantic_payload = (
                json.loads(semantic_stdout)
                if semantic_stdout.strip().startswith("{")
                else {"stdout": semantic_stdout}
            )
        result.update(
            {
                "ok": rc == 0 and result.get("status") == "ok",
                "returncode": rc,
                "stderr": stderr,
                "dwg_probe_status": probe.get("status"),
                "cad_semantics": semantic_payload,
                "cad_semantics_returncode": semantic_rc,
                "cad_semantics_stderr": semantic_stderr,
            }
        )
        if rc == 0:
            result.update(self.read_cad_preview_payload(proj, code))
        self.send_json(result, HTTPStatus.OK if rc == 0 else HTTPStatus.BAD_REQUEST)

    def clean_candidate_set_id_at_save(self, payload: dict) -> str:
        if "candidate_set_id_at_save" not in payload:
            raise ValueError("请求体缺少 candidate_set_id_at_save，请先重新加载 CAD 预览后再保存控制点")
        value = str(payload.get("candidate_set_id_at_save") or "").strip()
        if not value:
            raise ValueError("candidate_set_id_at_save 不能为空，请先生成 CAD 预览")
        return value

    def stale_control_points_payload(self, proj: Path, candidate_set_id_at_save: str) -> dict[str, object] | None:
        candidate_set_id_current = read_current_candidate_set_id(proj)
        if not candidate_set_id_current:
            raise ValueError("当前项目还没有 candidate_set_id，请先生成 CAD 预览")
        if candidate_set_id_at_save != candidate_set_id_current:
            return {
                "status": "stale_control_points",
                "candidate_set_id_current": candidate_set_id_current,
                "candidate_set_id_at_save": candidate_set_id_at_save,
            }
        return None

    def clean_control_points(self, points: object, candidate_set_id_at_save: str | None = None) -> list[dict[str, object]]:
        if not candidate_set_id_at_save:
            raise ValueError("请求体缺少 candidate_set_id_at_save，请先重新加载 CAD 预览后再保存控制点")
        if not isinstance(points, list):
            raise ValueError("control_points 必须是数组")
        cleaned = []
        for index, raw in enumerate(points, start=1):
            if not isinstance(raw, dict):
                raise ValueError(f"控制点 {index} 格式错误")
            label = str(raw.get("label") or f"CP{index}").strip()
            cad_x = str(raw.get("cad_x") or "").strip()
            cad_y = str(raw.get("cad_y") or "").strip()
            amap_location = str(raw.get("amap_location") or "").strip()
            feature_type = str(raw.get("feature_type") or "redline_corner").strip()
            feature_name = str(raw.get("feature_name") or "").strip()
            purpose = str(raw.get("purpose") or "registration").strip()
            confidence = str(raw.get("confidence") or "medium").strip()
            note = str(raw.get("note") or "").strip()
            if feature_type not in CONTROL_FEATURE_TYPES:
                feature_type = "other"
            if purpose not in CONTROL_PURPOSES:
                purpose = "registration"
            if confidence not in CONTROL_CONFIDENCE:
                confidence = "medium"
            if not amap_location:
                raise ValueError(f"控制点 {label} 缺少高德坐标")
            parts = [part.strip() for part in amap_location.replace("，", ",").split(",")]
            if len(parts) != 2:
                raise ValueError(f"控制点 {label} 的高德坐标应为 经度,纬度")
            lng = float(parts[0])
            lat = float(parts[1])
            if not (-180 <= lng <= 180 and -90 <= lat <= 90):
                raise ValueError(f"控制点 {label} 的高德坐标超出范围")
            cad_point = None
            if cad_x or cad_y:
                if not cad_x or not cad_y:
                    raise ValueError(f"控制点 {label} 的 CAD X/Y 需同时填写")
                cad_point = {"x": float(cad_x), "y": float(cad_y)}
            cleaned.append(
                {
                    "label": label,
                    "cad_point": cad_point,
                    "amap_gcj02": [lng, lat],
                    "feature_type": feature_type,
                    "feature_name": feature_name or None,
                    "purpose": purpose,
                    "confidence": confidence,
                    "note": note or None,
                    "source": "uploader_ui",
                }
            )
        return cleaned

    def handle_alignment_check(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        proj = project_dir(code)
        candidate_set_id_at_save = self.clean_candidate_set_id_at_save(payload)
        stale = self.stale_control_points_payload(proj, candidate_set_id_at_save)
        if stale:
            self.send_json(stale, HTTPStatus.CONFLICT)
            return
        cleaned = self.clean_control_points(payload.get("control_points"), candidate_set_id_at_save)
        with tempfile.TemporaryDirectory(prefix="alignment_check_") as tmp:
            source = Path(tmp) / "control_points.json"
            source.write_text(
                json.dumps(
                    {
                        "candidate_set_id_at_save": candidate_set_id_at_save,
                        "control_points": cleaned,
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
            rc, stdout, stderr = run_tool(
                ["_tools/cad_align.py", code, "--json", "--input", str(source)]
            )
        result = json.loads(stdout) if stdout.strip().startswith("{") else {"stdout": stdout}
        result.update({"ok": rc == 0, "returncode": rc, "stderr": stderr, "preview": True})
        self.send_json(result, HTTPStatus.OK if rc == 0 else HTTPStatus.BAD_REQUEST)

    def handle_control_points(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        proj = project_dir(code)
        candidate_set_id_at_save = self.clean_candidate_set_id_at_save(payload)
        stale = self.stale_control_points_payload(proj, candidate_set_id_at_save)
        if stale:
            self.send_json(stale, HTTPStatus.CONFLICT)
            return
        cleaned = self.clean_control_points(payload.get("control_points"), candidate_set_id_at_save)
        out_dir = proj / "05_output" / "amap"
        out_dir.mkdir(parents=True, exist_ok=True)
        out = {
            "schema_version": "1.0",
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "project": code,
            "candidate_set_id_at_save": candidate_set_id_at_save,
            "coordinate_system": {
                "map": "GCJ-02 / AMap",
                "cad": "project CAD units; unit and CRS must be confirmed in S2",
            },
            "control_points": cleaned,
            "agent_note": (
                "Use these points only as user-provided correspondence evidence. "
                "S2 must still verify CAD handles/layers and transformation quality."
            ),
        }
        target = out_dir / "control_points.json"
        target.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        align_rc, align_stdout, align_stderr = run_tool(["_tools/cad_align.py", code, "--json", "--write"])
        alignment = json.loads(align_stdout) if align_stdout.strip().startswith("{") else {"stdout": align_stdout}
        alignment.update({"ok": align_rc == 0, "returncode": align_rc, "stderr": align_stderr})
        self.send_json(
            {
                "ok": True,
                "project": code,
                "count": len(cleaned),
                "path": str(target.relative_to(proj)).replace("\\", "/"),
                "control_points": cleaned,
                "alignment": alignment,
            }
        )

    def handle_control_points_archive(self, archive: bool) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        proj = project_dir(code)
        control_path = proj / CONTROL_POINTS_REL
        if not control_path.exists():
            raise ValueError("当前项目没有 control_points.json 可处理")

        rc, stdout, stderr = run_tool(["_tools/cad_align.py", code, "--migration-report", "--write", "--json"])
        migration = json.loads(stdout) if stdout.strip().startswith("{") else {"stdout": stdout}
        if rc != 0 or migration.get("status") != "ok":
            migration.update({"ok": False, "returncode": rc, "stderr": stderr})
            self.send_json(migration, HTTPStatus.BAD_REQUEST)
            return

        response: dict[str, object] = {
            "ok": True,
            "project": code,
            "archived": False,
            "migration_report": str(Path(migration.get("written_to", "")).resolve().relative_to(proj)).replace("\\", "/")
            if migration.get("written_to")
            else None,
            "migration": migration,
        }

        if archive:
            saved = json.loads(control_path.read_text(encoding="utf-8"))
            at_save = saved.get("candidate_set_id_at_save")
            suffix = short_candidate_set_id(at_save)
            out_dir = control_path.parent
            filename = f"control_points.legacy_{time.strftime('%Y-%m-%d')}_{suffix}.json"
            legacy_path = unique_path(out_dir, filename)
            control_path.replace(legacy_path)
            response.update(
                {
                    "archived": True,
                    "legacy_file": str(legacy_path.relative_to(proj)).replace("\\", "/"),
                }
            )

        self.send_json(response)

    def handle_cad_candidate_semantics(self) -> None:
        payload = self.read_json()
        code = safe_project(str(payload.get("project", "")))
        cleaned = self.clean_candidate_semantics(payload.get("candidates"))
        proj = project_dir(code)
        out_dir = (proj / CAD_SEMANTICS_REL).parent
        out_dir.mkdir(parents=True, exist_ok=True)
        out = {
            "schema_version": "1.0",
            "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "project": code,
            "candidates": cleaned,
            "agent_note": (
                "Semantic annotations for CAD-side candidate points. They do not replace "
                "AMap coordinates; use them to decide which candidate points are useful "
                "for road, bridge, entrance, water, or registration reasoning."
            ),
        }
        target = proj / CAD_SEMANTICS_REL
        target.write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
        self.send_json(
            {
                "ok": True,
                "project": code,
                "count": len(cleaned),
                "path": str(target.relative_to(proj)).replace("\\", "/"),
                "candidates": cleaned,
            }
        )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run local architecture upload UI")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--no-browser", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    server = ThreadingHTTPServer((args.host, args.port), UploaderHandler)
    url = f"http://{args.host}:{args.port}"
    print(f"Architecture uploader running at {url}")
    if not args.no_browser:
        webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping uploader")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
