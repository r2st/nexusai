"""Langfuse Prompt Management integration.

Provides centralized prompt management via Langfuse with:
- Fetch prompts by name/label/version with client-side caching
- Create and sync prompts to Langfuse for UI editing
- Compile prompts with variable substitution
- Link prompts to LLM generations for per-version analytics
- Graceful fallback when Langfuse is unavailable
"""

import asyncio
from typing import Any, Literal

import structlog

logger = structlog.get_logger()

# Try to import langfuse prompt types
try:
    from langfuse import Langfuse
    from langfuse.model import (
        ChatPromptClient,
        PromptClient,
        TextPromptClient,
    )

    LANGFUSE_AVAILABLE = True
except ImportError:
    LANGFUSE_AVAILABLE = False
    Langfuse = None  # type: ignore[assignment,misc]
    PromptClient = None  # type: ignore[assignment,misc]
    TextPromptClient = None  # type: ignore[assignment,misc]
    ChatPromptClient = None  # type: ignore[assignment,misc]


class LangfusePromptManager:
    """Manages prompts via Langfuse's prompt management API.

    Features:
    - Fetch prompts with label-based deployment (production/staging/latest)
    - Client-side caching with stale-while-revalidate (60s default TTL)
    - Create/update prompts programmatically
    - Compile templates with {{variable}} substitution
    - Return raw PromptClient for linking to generations
    - Graceful fallback when Langfuse is unavailable

    Usage:
        manager = LangfusePromptManager(langfuse_client)
        prompt = await manager.get_prompt("my-prompt")
        compiled = prompt.compile(name="Alice", task="summarize")
    """

    def __init__(self, client: Any | None = None) -> None:
        """Initialize the prompt manager.

        Args:
            client: A Langfuse SDK client instance. If None, prompt
                    operations will return None (fallback mode).
        """
        self._client = client
        self._enabled = client is not None and LANGFUSE_AVAILABLE

    @property
    def enabled(self) -> bool:
        """Whether Langfuse prompt management is available."""
        return self._enabled

    async def get_prompt(
        self,
        name: str,
        *,
        label: str | None = None,
        version: int | None = None,
        type: Literal["text", "chat"] = "text",
        cache_ttl_seconds: int | None = None,
        fallback: str | None = None,
    ) -> Any | None:
        """Fetch a prompt from Langfuse.

        Fetches the prompt with label-based deployment. Defaults to the
        ``production`` label when neither label nor version is specified.

        Args:
            name: Prompt name in Langfuse.
            label: Label to fetch (e.g. "production", "staging", "latest").
                   Defaults to "production" via the Langfuse SDK.
            version: Fetch a specific version number. Cannot combine with label.
            type: Prompt type - "text" or "chat".
            cache_ttl_seconds: Override the default 60s cache TTL.
            fallback: Hardcoded fallback template if fetch fails entirely.

        Returns:
            A TextPromptClient or ChatPromptClient, or None if unavailable.
        """
        if not self._enabled:
            return None

        try:
            kwargs: dict[str, Any] = {"name": name, "type": type}
            if label is not None:
                kwargs["label"] = label
            if version is not None:
                kwargs["version"] = version
            if cache_ttl_seconds is not None:
                kwargs["cache_ttl_seconds"] = cache_ttl_seconds
            if fallback is not None:
                kwargs["fallback"] = fallback

            # Langfuse SDK is synchronous - run in thread pool
            prompt = await asyncio.to_thread(self._client.get_prompt, **kwargs)

            logger.debug(
                "langfuse_prompt_fetched",
                name=name,
                version=prompt.version if prompt else None,
                labels=prompt.labels if prompt else [],
                is_fallback=prompt.is_fallback if prompt else None,
            )
            return prompt

        except Exception as e:
            logger.warning(
                "langfuse_prompt_fetch_failed",
                name=name,
                error=str(e),
            )
            return None

    async def get_chat_prompt(
        self,
        name: str,
        *,
        label: str | None = None,
        version: int | None = None,
        cache_ttl_seconds: int | None = None,
        fallback: list[dict[str, str]] | None = None,
    ) -> Any | None:
        """Fetch a chat prompt from Langfuse.

        Convenience method that sets type="chat".

        Args:
            name: Prompt name in Langfuse.
            label: Label to fetch.
            version: Specific version number.
            cache_ttl_seconds: Override cache TTL.
            fallback: Fallback chat messages list.

        Returns:
            A ChatPromptClient or None if unavailable.
        """
        return await self.get_prompt(
            name,
            label=label,
            version=version,
            type="chat",
            cache_ttl_seconds=cache_ttl_seconds,
            fallback=fallback,
        )

    async def compile_prompt(
        self,
        name: str,
        variables: dict[str, Any],
        *,
        label: str | None = None,
        version: int | None = None,
        fallback: str | None = None,
    ) -> tuple[str | None, Any | None]:
        """Fetch and compile a text prompt in one call.

        Args:
            name: Prompt name.
            variables: Template variables to substitute.
            label: Label to fetch.
            version: Specific version.
            fallback: Fallback template string.

        Returns:
            Tuple of (compiled_text, prompt_client). Both are None if
            Langfuse is unavailable.
        """
        prompt = await self.get_prompt(
            name,
            label=label,
            version=version,
            type="text",
            fallback=fallback,
        )
        if prompt is None:
            return None, None

        try:
            compiled = prompt.compile(**variables)
            return compiled, prompt
        except Exception as e:
            logger.warning(
                "langfuse_prompt_compile_failed",
                name=name,
                error=str(e),
            )
            return None, prompt

    async def compile_chat_prompt(
        self,
        name: str,
        variables: dict[str, Any],
        *,
        label: str | None = None,
        version: int | None = None,
    ) -> tuple[list[dict[str, Any]] | None, Any | None]:
        """Fetch and compile a chat prompt in one call.

        Args:
            name: Prompt name.
            variables: Template variables to substitute.
            label: Label to fetch.
            version: Specific version.

        Returns:
            Tuple of (compiled_messages, prompt_client). Both None if unavailable.
        """
        prompt = await self.get_chat_prompt(
            name, label=label, version=version
        )
        if prompt is None:
            return None, None

        try:
            compiled = prompt.compile(**variables)
            return compiled, prompt
        except Exception as e:
            logger.warning(
                "langfuse_chat_prompt_compile_failed",
                name=name,
                error=str(e),
            )
            return None, prompt

    async def create_prompt(
        self,
        name: str,
        template: str,
        *,
        labels: list[str] | None = None,
        tags: list[str] | None = None,
        config: dict[str, Any] | None = None,
        commit_message: str | None = None,
        type: Literal["text", "chat"] = "text",
    ) -> Any | None:
        """Create or update a prompt in Langfuse.

        If a prompt with the same name already exists, creates a new version.

        Args:
            name: Prompt name (identifier).
            template: Template string (for text) or chat messages.
            labels: Labels to assign (e.g. ["production"]).
            tags: Tags for organization.
            config: Additional config (model params, etc.).
            commit_message: Version change description.
            type: "text" or "chat".

        Returns:
            The created PromptClient, or None if unavailable.
        """
        if not self._enabled:
            return None

        try:
            kwargs: dict[str, Any] = {
                "name": name,
                "prompt": template,
                "type": type,
            }
            if labels is not None:
                kwargs["labels"] = labels
            if tags is not None:
                kwargs["tags"] = tags
            if config is not None:
                kwargs["config"] = config
            if commit_message is not None:
                kwargs["commit_message"] = commit_message

            prompt = await asyncio.to_thread(
                self._client.create_prompt, **kwargs
            )

            logger.info(
                "langfuse_prompt_created",
                name=name,
                version=prompt.version if prompt else None,
                labels=labels,
            )
            return prompt

        except Exception as e:
            logger.error(
                "langfuse_prompt_create_failed",
                name=name,
                error=str(e),
            )
            return None

    async def create_chat_prompt(
        self,
        name: str,
        messages: list[dict[str, str]],
        *,
        labels: list[str] | None = None,
        tags: list[str] | None = None,
        config: dict[str, Any] | None = None,
        commit_message: str | None = None,
    ) -> Any | None:
        """Create a chat prompt in Langfuse.

        Args:
            name: Prompt name.
            messages: List of {"role": ..., "content": ...} dicts.
            labels: Labels to assign.
            tags: Tags for organization.
            config: Additional config.
            commit_message: Version description.

        Returns:
            The created ChatPromptClient, or None if unavailable.
        """
        if not self._enabled:
            return None

        try:
            kwargs: dict[str, Any] = {
                "name": name,
                "prompt": messages,
                "type": "chat",
            }
            if labels is not None:
                kwargs["labels"] = labels
            if tags is not None:
                kwargs["tags"] = tags
            if config is not None:
                kwargs["config"] = config
            if commit_message is not None:
                kwargs["commit_message"] = commit_message

            prompt = await asyncio.to_thread(
                self._client.create_prompt, **kwargs
            )

            logger.info(
                "langfuse_chat_prompt_created",
                name=name,
                version=prompt.version if prompt else None,
            )
            return prompt

        except Exception as e:
            logger.error(
                "langfuse_chat_prompt_create_failed",
                name=name,
                error=str(e),
            )
            return None

    async def sync_from_local(
        self,
        name: str,
        template: str,
        *,
        system_prompt: str | None = None,
        config: dict[str, Any] | None = None,
        labels: list[str] | None = None,
        tags: list[str] | None = None,
        commit_message: str | None = None,
    ) -> Any | None:
        """Sync a local prompt to Langfuse.

        Creates a new version in Langfuse from local prompt data.
        If the template matches the current Langfuse version, skips.

        Args:
            name: Prompt name.
            template: The prompt template text.
            system_prompt: Optional system prompt (stored in config).
            config: Model parameters and other config.
            labels: Labels to assign.
            tags: Tags for organization.
            commit_message: Description of this version.

        Returns:
            The PromptClient if created, None if skipped or unavailable.
        """
        if not self._enabled:
            return None

        # Check if current version already matches
        existing = await self.get_prompt(name, label="latest", cache_ttl_seconds=0)
        if existing and hasattr(existing, "prompt") and existing.prompt == template:
            logger.debug(
                "langfuse_prompt_sync_skipped",
                name=name,
                reason="template_unchanged",
            )
            return existing

        # Build config with system_prompt if provided
        full_config = dict(config or {})
        if system_prompt is not None:
            full_config["system_prompt"] = system_prompt

        return await self.create_prompt(
            name,
            template,
            labels=labels or ["production"],
            tags=tags,
            config=full_config if full_config else None,
            commit_message=commit_message or "Synced from local",
        )


# ---------------------------------------------------------------------------
# Singleton
# ---------------------------------------------------------------------------

_prompt_manager: LangfusePromptManager | None = None


async def get_langfuse_prompt_manager() -> LangfusePromptManager:
    """Get or create the global LangfusePromptManager.

    Uses the existing LangfuseClient's underlying SDK client.
    Returns a disabled manager if Langfuse is not configured.
    """
    global _prompt_manager

    if _prompt_manager is not None:
        return _prompt_manager

    # Get the underlying Langfuse SDK client from the existing LangfuseClient
    from app.services.observability.langfuse_client import get_langfuse_client

    langfuse_client = await get_langfuse_client()
    sdk_client = getattr(langfuse_client, "_client", None)

    _prompt_manager = LangfusePromptManager(client=sdk_client)
    logger.info(
        "langfuse_prompt_manager_initialized",
        enabled=_prompt_manager.enabled,
    )
    return _prompt_manager
