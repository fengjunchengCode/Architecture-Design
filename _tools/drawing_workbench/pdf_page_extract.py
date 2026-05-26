#!/usr/bin/env python3
"""Extract a single PDF page to a PNG reference image."""
from __future__ import annotations

import argparse
from pathlib import Path


def extract_page(pdf_path: Path, page: int, output_path: Path, *, dpi: int = 200) -> Path:
    if page < 1:
        raise ValueError("page must be 1-based and greater than 0")
    if dpi <= 0:
        raise ValueError("dpi must be positive")
    pdf_path = Path(pdf_path)
    output_path = Path(output_path)
    if not pdf_path.exists():
        raise FileNotFoundError(pdf_path)
    try:
        from pdf2image import convert_from_path
    except ImportError as exc:
        raise RuntimeError("pdf2image is not installed; run python -m pip install -r requirements.txt") from exc

    try:
        images = convert_from_path(
            str(pdf_path),
            dpi=dpi,
            first_page=page,
            last_page=page,
            fmt="png",
        )
    except Exception as exc:
        if "poppler" in str(exc).lower() or "pdfinfo" in str(exc).lower():
            raise RuntimeError("pdf2image requires Poppler; install Poppler and ensure pdftoppm/pdfinfo are in PATH") from exc
        raise
    if not images:
        raise RuntimeError(f"no image returned for page {page}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    images[0].save(output_path)
    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Extract one PDF page to PNG.")
    parser.add_argument("pdf")
    parser.add_argument("page", type=int)
    parser.add_argument("output")
    parser.add_argument("--dpi", type=int, default=200)
    args = parser.parse_args()
    out = extract_page(Path(args.pdf), args.page, Path(args.output), dpi=args.dpi)
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
