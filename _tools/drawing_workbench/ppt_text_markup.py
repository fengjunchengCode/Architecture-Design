#!/usr/bin/env python3
"""Lightweight PPT drawing text markup shared by preview and PPTX export."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TextRun:
    role: str
    text: str


@dataclass(frozen=True)
class Paragraph:
    runs: list[TextRun]


def _parse_inline(line: str) -> list[TextRun]:
    runs: list[TextRun] = []
    index = 0
    while index < len(line):
        if line.startswith("**", index):
            end = line.find("**", index + 2)
            if end > index + 2:
                runs.append(TextRun("heading", line[index + 2:end]))
                index = end + 2
                continue
        if line[index] == "*" and (index + 1 >= len(line) or line[index + 1] != "*"):
            end = line.find("*", index + 1)
            if end > index + 1 and (end + 1 >= len(line) or line[end + 1] != "*"):
                runs.append(TextRun("brand", line[index + 1:end]))
                index = end + 1
                continue
        next_index = len(line)
        next_heading = line.find("**", index + 1)
        next_brand = line.find("*", index + 1)
        if next_heading != -1:
            next_index = min(next_index, next_heading)
        if next_brand != -1:
            next_index = min(next_index, next_brand)
        runs.append(TextRun("body", line[index:next_index]))
        index = next_index
    return [run for run in runs if run.text]


def _apply_colon_fallback(runs: list[TextRun]) -> list[TextRun]:
    if any(run.role != "body" for run in runs):
        return runs
    text = "".join(run.text for run in runs)
    for separator in ("：", ":"):
        index = text.find(separator)
        if 0 <= index < 28:
            prefix = text[: index + 1]
            suffix = text[index + 1:]
            result = [TextRun("heading", prefix)]
            if suffix:
                result.append(TextRun("body", suffix))
            return result
    return runs


def parse_ppt_text_markup(markup: str) -> list[Paragraph]:
    text = str(markup or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    return [Paragraph(_apply_colon_fallback(_parse_inline(line))) for line in lines]
