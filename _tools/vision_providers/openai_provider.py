"""OpenAI vision provider implementation."""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .base import VisionProvider

DEFAULT_API_BASE = "https://api.openai.com/v1"


class OpenAIProvider(VisionProvider):
    """OpenAI 视觉模型 Provider（支持 GPT-4o, GPT-4V 等）"""

    def __init__(self):
        self.api_key = os.environ.get("OPENAI_API_KEY")
        self.model = os.environ.get("VISION_MODEL") or os.environ.get("OPENAI_VISION_MODEL")
        self.api_base = os.environ.get("OPENAI_API_BASE", DEFAULT_API_BASE).rstrip("/")

    def is_configured(self) -> bool:
        return bool(self.api_key and self.model)

    def get_config_info(self) -> dict[str, Any]:
        return {
            "provider": "openai",
            "model": self.model,
            "api_base": self.api_base,
            "configured": self.is_configured(),
        }

    def _data_url(self, path: Path) -> str:
        """将图片文件转换为 data URL"""
        mime = mimetypes.guess_type(str(path))[0] or "image/png"
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        return f"data:{mime};base64,{encoded}"

    def _extract_output_text(self, payload: dict[str, Any]) -> str:
        """从 OpenAI 响应中提取文本"""
        if isinstance(payload.get("output_text"), str):
            return payload["output_text"]
        parts: list[str] = []
        for item in payload.get("output", []) or []:
            for content in item.get("content", []) or []:
                text = content.get("text")
                if isinstance(text, str):
                    parts.append(text)
        return "\n".join(parts).strip()

    def _parse_json_text(self, text: str) -> dict[str, Any] | None:
        """解析 JSON 文本"""
        stripped = text.strip()
        if stripped.startswith("```"):
            stripped = stripped.strip("`")
            if stripped.lower().startswith("json"):
                stripped = stripped[4:].strip()
        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return None
        return parsed if isinstance(parsed, dict) else None

    def analyze_image(self, image_path: Path, prompt: str, timeout: int = 90) -> dict[str, Any]:
        if not self.is_configured():
            return {
                "status": "error",
                "summary": None,
                "raw_text": None,
                "error": "OpenAI provider not configured",
                "model": None,
            }

        body = {
            "model": self.model,
            "input": [
                {
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": self._data_url(image_path), "detail": "high"},
                    ],
                }
            ],
        }

        request = urllib.request.Request(
            f"{self.api_base}/responses",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )

        try:
            with urllib.request.urlopen(request, timeout=timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            try:
                detail = exc.read().decode("utf-8", errors="replace")
            except Exception:
                detail = str(exc)
            return {
                "status": "error",
                "summary": None,
                "raw_text": None,
                "error": detail,
                "model": self.model,
            }
        except Exception as exc:
            return {
                "status": "error",
                "summary": None,
                "raw_text": None,
                "error": str(exc),
                "model": self.model,
            }

        output_text = self._extract_output_text(payload)
        parsed = self._parse_json_text(output_text)

        return {
            "status": "ok" if parsed else "raw_text_only",
            "model": self.model,
            "summary": parsed,
            "raw_text": output_text if not parsed else None,
            "response_id": payload.get("id"),
        }
