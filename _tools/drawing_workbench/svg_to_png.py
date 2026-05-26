#!/usr/bin/env python3
"""Mechanical SVG export for drawing workbench outputs."""
from __future__ import annotations

import argparse
from pathlib import Path


PAGE_PIXELS = {
    "A3": (4960, 3508),
}


def export_svg(
    svg_path: Path,
    output_dir: Path,
    *,
    formats: list[str] | tuple[str, ...] = ("png", "pdf"),
    dpi: int = 300,
    page_size: str = "A3",
) -> dict[str, Path]:
    svg_path = Path(svg_path)
    output_dir = Path(output_dir)
    if not svg_path.exists():
        raise FileNotFoundError(svg_path)
    try:
        import cairosvg
    except ImportError as exc:
        raise RuntimeError("cairosvg is not installed; run python -m pip install -r requirements.txt") from exc
    except OSError as exc:
        raise RuntimeError("cairosvg requires system Cairo; install Cairo/GTK runtime and ensure libcairo is available") from exc

    width, height = PAGE_PIXELS.get(page_size.upper(), PAGE_PIXELS["A3"])
    outputs: dict[str, Path] = {}
    stem = svg_path.stem
    wanted = {fmt.lower() for fmt in formats}
    if "png" in wanted:
        png_path = output_dir / "png" / f"{stem}.png"
        png_path.parent.mkdir(parents=True, exist_ok=True)
        cairosvg.svg2png(
            url=str(svg_path),
            write_to=str(png_path),
            output_width=width,
            output_height=height,
            dpi=dpi,
        )
        outputs["png"] = png_path
    if "pdf" in wanted:
        pdf_path = output_dir / "pdf" / f"{stem}.pdf"
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        cairosvg.svg2pdf(url=str(svg_path), write_to=str(pdf_path), dpi=dpi)
        outputs["pdf"] = pdf_path
    return outputs


def main() -> int:
    parser = argparse.ArgumentParser(description="Export an SVG drawing to PNG/PDF.")
    parser.add_argument("svg")
    parser.add_argument("output_dir")
    parser.add_argument("--formats", default="png,pdf")
    parser.add_argument("--dpi", type=int, default=300)
    parser.add_argument("--page-size", default="A3")
    args = parser.parse_args()
    outputs = export_svg(
        Path(args.svg),
        Path(args.output_dir),
        formats=[item.strip() for item in args.formats.split(",") if item.strip()],
        dpi=args.dpi,
        page_size=args.page_size,
    )
    for key, path in outputs.items():
        print(f"{key}: {path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
