"""Vision providers package.

Supports multiple vision model providers:
- OpenAI (GPT-4o, GPT-4V)
- Anthropic (Claude 3.5 Sonnet, Claude 3 Opus)
- Google (Gemini Pro Vision, Gemini 1.5)

Usage:
    from vision_providers import get_provider

    # Auto-detect available provider
    provider = get_provider()

    # Or specify provider explicitly
    provider = get_provider("anthropic")

    # Use provider
    if provider.is_configured():
        result = provider.analyze_image(image_path, prompt)
"""
from __future__ import annotations

import os
from typing import Any

from .base import VisionProvider
from .openai_provider import OpenAIProvider
from .anthropic_provider import AnthropicProvider
from .google_provider import GoogleProvider

__all__ = [
    "VisionProvider",
    "OpenAIProvider",
    "AnthropicProvider",
    "GoogleProvider",
    "get_provider",
    "list_providers",
]

# Provider 注册表
PROVIDERS: dict[str, type[VisionProvider]] = {
    "openai": OpenAIProvider,
    "anthropic": AnthropicProvider,
    "google": GoogleProvider,
}

# 自动检测优先级
AUTO_DETECT_ORDER = [
    OpenAIProvider,
    AnthropicProvider,
    GoogleProvider,
]


def get_provider(name: str | None = None) -> VisionProvider:
    """
    获取视觉模型 Provider

    Args:
        name: Provider 名称，可选值：openai, anthropic, google, auto
              如果为 None 或 "auto"，则自动检测可用的 provider

    Returns:
        VisionProvider 实例

    Raises:
        ValueError: 如果指定的 provider 不存在
    """
    if name is None:
        name = os.environ.get("VISION_PROVIDER", "auto")

    name = name.strip().lower()

    if name == "auto":
        return _auto_detect()

    if name not in PROVIDERS:
        available = ", ".join(PROVIDERS.keys())
        raise ValueError(f"Unknown provider: {name}. Available: {available}")

    return PROVIDERS[name]()


def _auto_detect() -> VisionProvider:
    """
    自动检测可用的 provider

    按优先级尝试各 provider，返回第一个已配置的。
    如果都未配置，返回 OpenAI provider（会触发降级机制）。
    """
    for provider_class in AUTO_DETECT_ORDER:
        provider = provider_class()
        if provider.is_configured():
            return provider

    # 都未配置，返回默认 OpenAI（会触发降级）
    return OpenAIProvider()


def list_providers() -> list[dict[str, Any]]:
    """
    列出所有可用的 provider 及其配置状态

    Returns:
        list of {
            "name": str,
            "configured": bool,
            "config_info": dict,
        }
    """
    result = []
    for name, provider_class in PROVIDERS.items():
        provider = provider_class()
        result.append({
            "name": name,
            "configured": provider.is_configured(),
            "config_info": provider.get_config_info(),
        })
    return result
