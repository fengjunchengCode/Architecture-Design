#!/usr/bin/env python3
"""Safe text extraction gate for agent workflows.

This script intentionally refuses legacy .doc binary files. Convert them to
.docx, PDF, or TXT before semantic extraction.
"""
from __future__ import annotations

import argparse
import json
import sys
import zipfile
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET

from inventory import read_policy_for


TEXT_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030")
TEXT_POLICIES = {"direct_text"}
DOCX_EXT = ".docx"


def read_text_file(path: Path) -> tuple[str, str]:
    last_error: Exception | None = None
    for encoding in TEXT_ENCODINGS:
        try:
            return path.read_text(encoding=encoding), encoding
        except UnicodeDecodeError as exc:
            last_error = exc
    raise UnicodeDecodeError("unknown", b"", 0, 1, f"cannot decode with {TEXT_ENCODINGS}: {last_error}")


def extract_docx(path: Path) -> str:
    with zipfile.ZipFile(path) as docx:
        xml = docx.read("word/document.xml")
    root = ET.fromstring(xml)
    paragraphs: list[str] = []
    for paragraph in root.iter():
        if not paragraph.tag.endswith("}p"):
            continue
        parts: list[str] = []
        for node in paragraph.iter():
            if node.tag.endswith("}t") and node.text:
                parts.append(node.text)
            elif node.tag.endswith("}tab"):
                parts.append("\t")
            elif node.tag.endswith("}br"):
                parts.append("\n")
        text = "".join(parts).strip()
        if text:
            paragraphs.append(text)
    return "\n".join(paragraphs)


def truncate(text: str, max_chars: int) -> tuple[str, bool]:
    if max_chars <= 0 or len(text) <= max_chars:
        return text, False
    return text[:max_chars], True


def extract(path: Path, max_chars: int) -> tuple[int, dict[str, Any]]:
    if not path.exists() or not path.is_file():
        return 3, {"ok": False, "path": str(path), "error": "file not found"}

    policy, requires_conversion, note = read_policy_for(path)
    result: dict[str, Any] = {
        "ok": False,
        "path": str(path),
        "ext": path.suffix.lower(),
        "read_policy": policy,
        "requires_conversion": requires_conversion,
        "agent_note": note,
    }

    if requires_conversion:
        result["error"] = "conversion_required"
        return 2, result

    try:
        if policy in TEXT_POLICIES:
            text, encoding = read_text_file(path)
            result["encoding"] = encoding
        elif path.suffix.lower() == DOCX_EXT:
            text = extract_docx(path)
            result["encoding"] = "docx-xml"
        else:
            result["error"] = "unsupported_for_text_extraction"
            return 2, result
    except Exception as exc:
        result["error"] = str(exc)
        return 1, result

    result["text"], result["truncated"] = truncate(text, max_chars)
    result["chars"] = len(text)
    result["ok"] = True
    return 0, result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Safely extract text for agent workflows")
    parser.add_argument("path", help="Input file path")
    parser.add_argument("--max-chars", type=int, default=20000)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    code, payload = extract(Path(args.path), args.max_chars)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
