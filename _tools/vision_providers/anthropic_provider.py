"""Anthropic vision provider implementation."""
from __future__ import annotations

import base64
import json
import mimetypes
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from .base import VisionProvider, has_real_config_value

DEFAULT_API_BASE = "https://api.anthropic.com"
DEFAULT_MODEL = "claude-sonnet-4-20250514"


class AnthropicProvider(VisionProvider):
    """Anthropic 视觉模型 Provider（支持 Claude 3.5 Sonnet, Claude 3 Opus 等）"""

    def __init__(self):
        self.api_key = os.environ.get("ANTHROPIC_API_KEY")
        self.model = os.environ.get("ANTHROPIC_VISION_MODEL", DEFAULT_MODEL)
        self.api_base = os.environ.get("ANTHROPIC_API_BASE", DEFAULT_API_BASE).rstrip("/")

    def is_configured(self) -> bool:
        return has_real_config_value(self.api_key)

    def get_config_info(self) -> dict[str, Any]:
        return {
            "provider": "anthropic",
            "model": self.model,
            "api_base": self.api_base,
            "configured": self.is_configured(),
        }

    def _get_mime_type(self, path: Path) -> str:
        """获取图片 MIME 类型"""
        mime = mimetypes.guess_type(str(path))[0]
        if mime and mime.startswith("image/"):
            return mime
        # 根据扩展名推断
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
        """编码图片为 base64，返回 (media_type, data)"""
        media_type = self._get_mime_type(path)
        data = base64.b64encode(path.read_bytes()).decode("ascii")
        return media_type, data

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
                "error": "Anthropic provider not configured",
                "model": None,
            }

        media_type, image_data = self._encode_image(image_path)

        body = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": image_data,
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
        }

        request = urllib.request.Request(
            f"{self.api_base}/v1/messages",
            data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
            headers={
                "x-api-key": self.api_key,
                "anthropic-version": "2023-06-01",
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
        for content in payload.get("content", []):
            if content.get("type") == "text":
                output_text += content.get("text", "")

        parsed = self._parse_json_text(output_text)

        return {
            "status": "ok" if parsed else "raw_text_only",
            "model": self.model,
            "summary": parsed,
            "raw_text": output_text if not parsed else None,
            "response_id": payload.get("id"),
        }
