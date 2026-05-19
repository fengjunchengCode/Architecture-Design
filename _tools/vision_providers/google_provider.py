"""Google vision provider implementation."""
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

DEFAULT_MODEL = "gemini-1.5-pro"


class GoogleProvider(VisionProvider):
    """Google 视觉模型 Provider（支持 Gemini Pro Vision, Gemini 1.5 等）"""

    def __init__(self):
        self.api_key = os.environ.get("GOOGLE_API_KEY")
        self.model = os.environ.get("GOOGLE_VISION_MODEL", DEFAULT_MODEL)

    def is_configured(self) -> bool:
        return bool(self.api_key)

    def get_config_info(self) -> dict[str, Any]:
        return {
            "provider": "google",
            "model": self.model,
            "configured": self.is_configured(),
        }

    def _get_mime_type(self, path: Path) -> str:
        """获取图片 MIME 类型"""
        mime = mimetypes.guess_type(str(path))[0]
        if mime and mime.startswith("image/"):
            return mime
        ext = path.suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".webp": "image/webp",
            ".gif": "image/gif",
        }
        return mime_map.get(ext, "image/png")

    def _encode_image(self, path: Path) -> tuple[str, str]:
        """编码图片为 base64，返回 (mime_type, data)"""
        mime_type = self._get_mime_type(path)
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return mime_type, data

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
                "error": "Google provider not configured",
                "model": None,
            }

        mime_type, image_data = self._encode_image(image_path)

        body = {
            "contents": [
                {
                    "parts": [
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": image_data,
                            }
                        },
                        {
                            "text": prompt,
                        },
                    ]
                }
            ],
            "generationConfig": {
                "temperature": 0.1,
                "maxOutputTokens": 4096,
            },
        }

        url = f"https://generativelanguage.googleapis.com/v1beta/models/{self.model}:generateContent?key={self.api_key}"

        request = urllib.request.Request(
            url,
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
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

        # 提取响应文本
        output_text = ""
        for candidate in payload.get("candidates", []):
            content = candidate.get("content", {})
            for part in content.get("parts", []):
                if "text" in part:
                    output_text += part["text"]

        parsed = self._parse_json_text(output_text)

        return {
            "status": "ok" if parsed else "raw_text_only",
            "model": self.model,
            "summary": parsed,
            "raw_text": output_text if not parsed else None,
            "response_id": payload.get("responseId"),
        }
