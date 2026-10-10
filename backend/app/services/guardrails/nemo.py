"""Optional NeMo Guardrails integration."""

from __future__ import annotations

import asyncio
from typing import Any

import structlog

from app.core.config import settings

logger = structlog.get_logger()


class NeMoGuardrailsAdapter:
    """Thin async wrapper around NeMo Guardrails with lazy initialization."""

    def __init__(self, config_path: str):
        self.config_path = config_path
        self._rails: Any | None = None
        self._init_lock = asyncio.Lock()
        self._init_attempted = False

    @property
    def is_ready(self) -> bool:
        """Return True when NeMo rails is initialized and ready."""
        return self._rails is not None

    async def _ensure_initialized(self) -> bool:
        """Initialize NeMo rails once."""
        if self._rails is not None:
            return True

        async with self._init_lock:
            if self._rails is not None:
                return True
            if self._init_attempted:
                return False

            self._init_attempted = True

            try:
                from nemoguardrails import LLMRails, RailsConfig  # type: ignore

                config = RailsConfig.from_path(self.config_path)
                self._rails = LLMRails(config)
                logger.info(
                    "NeMo Guardrails initialized",
                    config_path=self.config_path,
                )
                return True
            except Exception as e:
                logger.warning(
                    "NeMo Guardrails unavailable; falling back to local guardrails",
                    config_path=self.config_path,
                    error=str(e),
                )
                self._rails = None
                return False

    async def generate(self, messages: list[dict[str, str]]) -> str | None:
        """
        Generate a guarded response using NeMo rails.

        Returns None when unavailable or when generation fails.
        """
        if not messages:
            return None

        initialized = await self._ensure_initialized()
        if not initialized or self._rails is None:
            return None

        try:
            response = await self._rails.generate_async(messages=messages)
        except Exception as e:
            logger.warning("NeMo Guardrails generation failed", error=str(e))
            return None

        if isinstance(response, str):
            return response

        if isinstance(response, dict):
            content = response.get("content")
            if isinstance(content, str):
                return content

            msgs = response.get("messages")
            if isinstance(msgs, list):
                for msg in reversed(msgs):
                    if (
                        isinstance(msg, dict)
                        and msg.get("role") == "assistant"
                        and isinstance(msg.get("content"), str)
                    ):
                        return msg["content"]

        content_attr = getattr(response, "content", None)
        if isinstance(content_attr, str):
            return content_attr

        return None


_nemo_guardrails_adapter: NeMoGuardrailsAdapter | None = None


def get_nemo_guardrails_adapter() -> NeMoGuardrailsAdapter | None:
    """Get singleton NeMo adapter when enabled and configured."""
    global _nemo_guardrails_adapter

    if not settings.NEMO_GUARDRAILS_ENABLED:
        return None
    if not settings.NEMO_GUARDRAILS_CONFIG_PATH:
        logger.warning(
            "NeMo Guardrails enabled but config path is missing; skipping integration"
        )
        return None

    if _nemo_guardrails_adapter is None:
        _nemo_guardrails_adapter = NeMoGuardrailsAdapter(
            config_path=settings.NEMO_GUARDRAILS_CONFIG_PATH
        )
    return _nemo_guardrails_adapter
