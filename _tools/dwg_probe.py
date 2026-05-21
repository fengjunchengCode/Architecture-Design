#!/usr/bin/env python3
"""Convert DWG files through ODA File Converter and summarize DXF facts for S2."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import sys
import tempfile
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Iterable

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


REPO_ROOT = Path(__file__).resolve().parents[1]
PROJECTS_DIR = REPO_ROOT / "projects"
CAD_EXTS = {".dwg", ".dxf"}
LOCK_EXTS = {".dwl", ".dwl2"}

UNITS = {
    0: "unitless",
    1: "inches",
    2: "feet",
    3: "miles",
    4: "millimeters",
    5: "centimeters",
    6: "meters",
    7: "kilometers",
    8: "microinches",
    9: "mils",
    10: "yards",
    11: "angstroms",
    12: "nanometers",
    13: "microns",
    14: "decimeters",
    15: "decameters",
    16: "hectometers",
    17: "gigameters",
    18: "astronomical_units",
    19: "light_years",
    20: "parsecs",
}


@dataclass
class ToolStatus:
    ezdxf: str
    oda_file_converter: str
    oda_path: str | None


def sha1_file(path: Path) -> str:
    digest = hashlib.sha1()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def resolve_project(code_or_path: str) -> Path:
    direct = Path(code_or_path).expanduser()
    if direct.exists():
        return direct.resolve()
    return (PROJECTS_DIR / code_or_path).resolve()


def rel_to_project(path: Path, project_dir: Path) -> str:
    try:
        return path.relative_to(project_dir).as_posix()
    except ValueError:
        return str(path)


def iter_cad_files(project_dir: Path) -> list[Path]:
    site_dir = project_dir / "02_site"
    if not site_dir.exists():
        return []
    files: list[Path] = []
    for path in site_dir.rglob("*"):
        if not path.is_file():
            continue
        ext = path.suffix.lower()
        if ext in LOCK_EXTS:
            continue
        if ext in CAD_EXTS:
            files.append(path)
    return sorted(files, key=lambda item: item.as_posix().lower())


def existing_file(path: str | os.PathLike[str] | None) -> Path | None:
    if not path:
        return None
    candidate = Path(str(path).strip().strip('"')).expanduser()
    return candidate if candidate.is_file() else None


def oda_candidates() -> Iterable[Path]:
    for env_name in ("ODA_FILE_CONVERTER", "ODAFC_PATH", "ODA_FILE_CONVERTER_EXE"):
        env_path = existing_file(os.environ.get(env_name))
        if env_path:
            yield env_path

    for command in ("ODAFileConverter", "ODAFileConverter.exe"):
        found = shutil.which(command)
        if found:
            yield Path(found)

    try:
        import ezdxf
        from ezdxf.addons import odafc

        configured = existing_file(odafc.get_win_exec_path())
        if configured:
            yield configured
    except Exception:
        pass

    roots: list[Path] = []
    for env_name in ("LOCALAPPDATA", "ProgramFiles", "ProgramFiles(x86)"):
        value = os.environ.get(env_name)
        if value:
            roots.append(Path(value))

    patterns = [
        "ODAFC*/ODAFileConverter.exe",
        "ODA/ODAFileConverter*/ODAFileConverter.exe",
        "ODAFileConverter*/ODAFileConverter.exe",
        "ODA*/**/ODAFileConverter.exe",
    ]
    for root in roots:
        if not root.exists():
            continue
        for pattern in patterns:
            yield from root.glob(pattern)


def find_oda() -> Path | None:
    seen: set[str] = set()
    for candidate in oda_candidates():
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        key = str(resolved).lower()
        if key in seen:
            continue
        seen.add(key)
        if resolved.is_file():
            return resolved
    return None


def import_ezdxf() -> tuple[Any | None, Any | None, str | None]:
    try:
        import ezdxf
        from ezdxf.addons import odafc

        return ezdxf, odafc, None
    except Exception as exc:
        return None, None, str(exc)


def configure_odafc(ezdxf: Any, oda_path: Path | None) -> None:
    if oda_path is None:
        return
    ezdxf.options.set("odafc-addon", "WIN_EXEC_PATH", str(oda_path))


def install_guidance(oda_path: Path | None = None) -> dict[str, Any]:
    guidance: dict[str, Any] = {
        "ezdxf": "python -m pip install ezdxf",
        "oda_file_converter": {
            "official_download": "https://www.opendesign.com/guestfiles/oda_file_converter",
            "windows_note": "Install the ODA File Converter MSI as administrator, or extract it to a user-writable folder.",
            "user_extract_example": [
                "$msi = Join-Path $env:TEMP 'ODAFileConverter_QT6_vc16_amd64dll_27.1.msi'",
                "$target = Join-Path $env:LOCALAPPDATA 'ODAFC271Extract'",
                "New-Item -ItemType Directory -Force -Path $target | Out-Null",
                "Start-Process msiexec.exe -ArgumentList @('/a', $msi, '/qn', \"TARGETDIR=$target\") -Wait -WindowStyle Hidden",
            ],
            "env_var": "Set ODA_FILE_CONVERTER to the full ODAFileConverter.exe path when using a nonstandard install path.",
        },
    }
    if oda_path:
        guidance["oda_file_converter"]["detected_path"] = str(oda_path)
        guidance["oda_file_converter"]["set_user_env"] = (
            f"[Environment]::SetEnvironmentVariable('ODA_FILE_CONVERTER', '{oda_path}', 'User')"
        )
    return guidance


def shoelace_area(points: list[tuple[float, float]]) -> float | None:
    if len(points) < 3:
        return None
    area = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        area += x1 * y2 - x2 * y1
    return abs(area) / 2.0


def polyline_metrics(points: list[tuple[float, float]]) -> dict[str, Any]:
    if not points:
        return {}
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    perimeter = 0.0
    for index, (x1, y1) in enumerate(points):
        x2, y2 = points[(index + 1) % len(points)]
        perimeter += ((x2 - x1) ** 2 + (y2 - y1) ** 2) ** 0.5
    return {
        "perimeter_xy": perimeter,
        "bbox_xy": {
            "min": [min(xs), min(ys)],
            "max": [max(xs), max(ys)],
            "size": [max(xs) - min(xs), max(ys) - min(ys)],
        },
        "centroid_xy_vertices": [sum(xs) / len(xs), sum(ys) / len(ys)],
    }


def point2(point: Any) -> tuple[float, float]:
    return (float(point[0]), float(point[1]))


def polyline_candidates(msp: Any, limit: int = 25) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    for entity in msp:
        dxftype = entity.dxftype()
        points: list[tuple[float, float]] = []
        closed = False
        has_bulge = False

        if dxftype == "LWPOLYLINE":
            closed = bool(entity.closed)
            raw_points = list(entity.get_points("xyb"))
            points = [(float(item[0]), float(item[1])) for item in raw_points]
            has_bulge = any(abs(float(item[2])) > 1e-12 for item in raw_points)
        elif dxftype == "POLYLINE" and entity.is_2d_polyline:
            closed = bool(entity.is_closed)
            points = [point2(vertex.dxf.location) for vertex in entity.vertices]
        else:
            continue

        area = shoelace_area(points) if closed else None
        candidates.append(
            {
                "type": dxftype,
                "layer": entity.dxf.layer,
                "closed": closed,
                "vertex_count": len(points),
                "area_xy": area,
                "area_note": "shoelace_from_vertices_bulges_ignored" if has_bulge else "shoelace_from_vertices",
                "handle": entity.dxf.handle,
                **polyline_metrics(points),
            }
        )

    candidates.sort(key=lambda item: item.get("area_xy") or 0.0, reverse=True)
    return candidates[:limit]


def extract_text_samples(msp: Any, limit: int = 80) -> list[dict[str, Any]]:
    samples: list[dict[str, Any]] = []
    for entity in msp:
        dxftype = entity.dxftype()
        if dxftype == "TEXT":
            text = entity.dxf.text
            insert = entity.dxf.insert
        elif dxftype == "MTEXT":
            text = entity.plain_text()
            insert = entity.dxf.insert
        elif dxftype == "DIMENSION":
            text = entity.dxf.get("text", "")
            insert = entity.dxf.get("defpoint", (0, 0, 0))
        else:
            continue
        text = " ".join(str(text).split())
        if not text:
            continue
        samples.append(
            {
                "type": dxftype,
                "layer": entity.dxf.layer,
                "text": text[:240],
                "insert_xy": [float(insert[0]), float(insert[1])],
            }
        )
        if len(samples) >= limit:
            break
    return samples


def bbox_summary(msp: Any) -> dict[str, Any] | None:
    try:
        from ezdxf import bbox

        box = bbox.extents(msp, fast=True)
        if not box.has_data:
            return None
        return {
            "min": [float(box.extmin.x), float(box.extmin.y), float(box.extmin.z)],
            "max": [float(box.extmax.x), float(box.extmax.y), float(box.extmax.z)],
            "size": [
                float(box.extmax.x - box.extmin.x),
                float(box.extmax.y - box.extmin.y),
                float(box.extmax.z - box.extmin.z),
            ],
        }
    except Exception as exc:
        return {"error": str(exc)}


def parse_dxf(ezdxf: Any, dxf_path: Path) -> dict[str, Any]:
    doc = ezdxf.readfile(str(dxf_path))
    msp = doc.modelspace()
    entity_counts = Counter(entity.dxftype() for entity in msp)
    layer_entity_counts = Counter(entity.dxf.layer for entity in msp)
    units_code = int(doc.header.get("$INSUNITS", 0) or 0)
    layers = []
    for layer in doc.layers:
        layers.append(
            {
                "name": layer.dxf.name,
                "color": layer.color,
                "linetype": layer.dxf.get("linetype", ""),
                "is_off": bool(layer.is_off()),
                "is_frozen": bool(layer.is_frozen()),
                "entity_count": layer_entity_counts.get(layer.dxf.name, 0),
            }
        )
    layers.sort(key=lambda item: (-item["entity_count"], item["name"].lower()))
    return {
        "dxf_version": doc.dxfversion,
        "units": {"code": units_code, "name": UNITS.get(units_code, "unknown")},
        "entity_counts": dict(sorted(entity_counts.items())),
        "layers": layers,
        "bbox": bbox_summary(msp),
        "closed_polyline_candidates": polyline_candidates(msp),
        "text_samples": extract_text_samples(msp),
    }


def convert_to_dxf(odafc: Any, source: Path, dest: Path, version: str, audit: bool) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    odafc.convert(str(source), str(dest), version=version, audit=audit, replace=True)


def output_path_for(project_dir: Path, source: Path, out_dir: Path) -> Path:
    rel = source.relative_to(project_dir)
    safe_parts = list(rel.parts)
    safe_parts[-1] = Path(safe_parts[-1]).with_suffix(".dxf").name
    return out_dir.joinpath(*safe_parts)


def write_report(project_dir: Path, report: dict[str, Any]) -> Path:
    out_dir = project_dir / "05_output"
    out_dir.mkdir(exist_ok=True)
    out = out_dir / "dwg_probe.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    return out


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Probe DWG/DXF files for S2 geometry facts")
    parser.add_argument("project", help="Project code or path")
    parser.add_argument("--json", action="store_true", help="Print JSON only")
    parser.add_argument("--write", action="store_true", help="Write 05_output/dwg_probe.json and converted DXF files")
    parser.add_argument("--version", default="R2018", help="Output DXF version for ODA conversion")
    parser.add_argument("--no-audit", action="store_true", help="Disable ODA audit during conversion")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    project_dir = resolve_project(args.project)
    if not project_dir.exists():
        print(f"ERROR: project not found: {project_dir}", file=sys.stderr)
        return 3

    cad_files = iter_cad_files(project_dir)
    ezdxf, odafc, ezdxf_error = import_ezdxf()
    oda_path = find_oda()
    if ezdxf is not None:
        configure_odafc(ezdxf, oda_path)

    tool_status = ToolStatus(
        ezdxf="installed" if ezdxf is not None else f"missing: {ezdxf_error}",
        oda_file_converter="installed" if oda_path else "missing",
        oda_path=str(oda_path) if oda_path else None,
    )

    report: dict[str, Any] = {
        "project_dir": str(project_dir),
        "project_code": project_dir.name,
        "status": "ok",
        "tools": asdict(tool_status),
        "install_guidance": install_guidance(oda_path),
        "files": [],
        "warnings": [],
    }

    if not cad_files:
        report["status"] = "missing_inputs"
        report["warnings"].append("No DWG/DXF files were found under 02_site.")
    elif ezdxf is None:
        report["status"] = "ezdxf_missing"
        report["warnings"].append("Install ezdxf before parsing DXF or converting DWG.")
    elif any(path.suffix.lower() == ".dwg" for path in cad_files) and oda_path is None:
        report["status"] = "oda_not_installed"
        report["warnings"].append("DWG files require ODA File Converter before parsing.")

    output_dir = project_dir / "05_output" / "cad" if args.write else None
    failures = 0

    with tempfile.TemporaryDirectory(prefix="dwg_probe_") as tmp:
        temp_dir = Path(tmp)
        for source in cad_files:
            item: dict[str, Any] = {
                "path": rel_to_project(source, project_dir),
                "size_bytes": source.stat().st_size,
                "sha1": sha1_file(source),
                "ext": source.suffix.lower(),
                "conversion": None,
                "parse": None,
            }

            parse_source = source
            if source.suffix.lower() == ".dwg":
                if ezdxf is None or odafc is None or oda_path is None:
                    item["conversion"] = {"status": "skipped_missing_tool"}
                    report["files"].append(item)
                    continue
                dest = output_path_for(project_dir, source, output_dir or temp_dir)
                try:
                    convert_to_dxf(odafc, source, dest, args.version, audit=not args.no_audit)
                    item["conversion"] = {
                        "status": "ok",
                        "dxf_path": rel_to_project(dest, project_dir) if args.write else str(dest),
                    }
                    parse_source = dest
                except Exception as exc:
                    failures += 1
                    item["conversion"] = {"status": "error", "error": str(exc)}
                    report["files"].append(item)
                    continue

            if ezdxf is not None:
                try:
                    item["parse"] = {"status": "ok", **parse_dxf(ezdxf, parse_source)}
                except Exception as exc:
                    failures += 1
                    item["parse"] = {"status": "error", "error": str(exc)}
            report["files"].append(item)

    if failures and report["status"] == "ok":
        report["status"] = "partial"
        report["warnings"].append(f"{failures} CAD file(s) failed conversion or parsing.")

    if args.write:
        report["written_to"] = str(write_report(project_dir, report))

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        print(f"== dwg_probe :: {project_dir}")
        print(f"  status: {report['status']}")
        print(f"  ezdxf: {report['tools']['ezdxf']}")
        print(f"  oda_file_converter: {report['tools']['oda_file_converter']}")
        if report["tools"]["oda_path"]:
            print(f"  oda_path: {report['tools']['oda_path']}")
        print(f"  cad_files: {len(report['files'])}")
        for warning in report["warnings"]:
            print(f"  warning: {warning}")

    return 0 if report["status"] in {"ok", "partial", "missing_inputs"} else 2


if __name__ == "__main__":
    sys.exit(main())
