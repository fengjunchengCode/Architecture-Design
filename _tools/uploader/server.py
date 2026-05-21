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
import webbrowser
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, unquote_to_bytes, urlparse


REPO_ROOT = Path(__file__).resolve().parents[2]
STATIC_DIR = Path(__file__).resolve().parent / "static"
PROJECTS_DIR = REPO_ROOT / "projects"

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
        mime = mimetypes.guess_type(str(target))[0] or "application/octet-stream"
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)

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
