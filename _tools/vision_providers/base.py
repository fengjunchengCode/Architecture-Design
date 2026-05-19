"""Vision provider abstract base class."""
from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class VisionProvider(ABC):
    """视觉模型 Provider 抽象基类"""

    @abstractmethod
    def is_configured(self) -> bool:
        """检查 provider 是否已配置"""
        pass

    @abstractmethod
    def analyze_image(self, image_path: Path, prompt: str, timeout: int = 90) -> dict[str, Any]:
        """
        分析图片并返回结果

        Args:
            image_path: 图片文件路径
            prompt: 分析提示词
            timeout: 超时时间（秒）

        Returns:
            {
                "status": "ok" | "raw_text_only" | "error",
                "summary": dict | None,
                "raw_text": str | None,
                "error": str | None,
                "model": str | None,
            }
        """
        pass

    @abstractmethod
    def get_config_info(self) -> dict[str, Any]:
        """返回配置信息（用于日志和调试）

        Returns:
            {
                "provider": str,
                "model": str | None,
                "configured": bool,
                ... 其他 provider 特定信息
            }
        """
        pass

    def get_provider_name(self) -> str:
        """获取 provider 名称"""
        return self.__class__.__name__.replace("Provider", "").lower()
