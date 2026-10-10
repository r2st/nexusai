"""Unit tests for chat guardrails integration in ChatService."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.multitenancy import set_current_tenant_id
from app.models.conversation import ModelProvider
from app.services.chat import ChatService
from app.services.guardrails.models import GuardrailResult, ThreatLevel


def _conversation() -> SimpleNamespace:
    return SimpleNamespace(
        id="conv-1",
        model_name="gpt-4o",
        model_provider=ModelProvider.OPENAI.value,
        system_prompt=None,
        settings={},
    )


def _message(role: str, content: str) -> SimpleNamespace:
    return SimpleNamespace(role=role, content=content)


class _Chunk:
    def __init__(self, content: str):
        self.content = content
        self.tool_calls = None


class TestChatGuardrails:
    def test_resolve_guardrails_service_uses_tenant_overrides(self):
        service = ChatService(db=AsyncMock(), user_id="user-1")
        conv = _conversation()

        set_current_tenant_id("tenant-abc")
        try:
            with patch("app.services.chat.settings") as mock_settings:
                mock_settings.GUARDRAILS_TENANT_POLICIES = (
                    '{"tenant-abc":{"injection_block_threshold":0.95,"enable_content_filter":false}}'
                )
                resolved, tenant_id = service._resolve_guardrails_service(conv)

                assert resolved is not None
                assert tenant_id == "tenant-abc"
                assert resolved.config.injection_block_threshold == 0.95
                assert resolved.config.enable_content_filter is False
        finally:
            set_current_tenant_id(None)

    @pytest.mark.asyncio
    async def test_chat_blocks_input_before_llm(self):
        service = ChatService(db=AsyncMock(), user_id="user-1")
        conv = _conversation()

        service._apply_input_guardrails = AsyncMock(
            return_value=GuardrailResult(
                blocked=True,
                passed=False,
                message="blocked by guardrails",
                threat_level=ThreatLevel.HIGH,
            )
        )
        service._apply_output_guardrails = AsyncMock(return_value=None)
        service.add_message = AsyncMock(
            side_effect=[
                SimpleNamespace(id="m1", role="user", content="bad"),
                SimpleNamespace(id="m2", role="assistant", content="blocked by guardrails"),
            ]
        )
        service.get_messages = AsyncMock(return_value=[])
        service._get_llm = MagicMock()

        result = await service.chat(conv, "bad prompt")

        assert result.content == "blocked by guardrails"
        assert service._get_llm.call_count == 0
        assert service.add_message.call_count == 2

    @pytest.mark.asyncio
    async def test_chat_uses_modified_input_and_modified_output(self):
        service = ChatService(db=AsyncMock(), user_id="user-1")
        conv = _conversation()

        service._apply_input_guardrails = AsyncMock(
            return_value=GuardrailResult(
                modified=True,
                modified_content="cleaned user text",
            )
        )
        service.get_messages = AsyncMock(
            return_value=[_message("user", "cleaned user text")]
        )
        service._generate_with_nemo = AsyncMock(return_value=None)

        llm_response = SimpleNamespace(content="raw llm output", usage_metadata=None)
        llm = SimpleNamespace(ainvoke=AsyncMock(return_value=llm_response))
        service._get_llm = MagicMock(return_value=llm)
        service._apply_output_guardrails = AsyncMock(
            return_value=GuardrailResult(
                modified=True,
                modified_content="redacted llm output",
            )
        )

        service.add_message = AsyncMock(
            side_effect=[
                SimpleNamespace(id="u1", role="user", content="cleaned user text"),
                SimpleNamespace(id="a1", role="assistant", content="redacted llm output"),
            ]
        )

        result = await service.chat(conv, "raw user text")

        first_call = service.add_message.await_args_list[0]
        assert first_call.args[2] == "cleaned user text"
        assert result.content == "redacted llm output"

    @pytest.mark.asyncio
    async def test_chat_stream_blocks_input(self):
        service = ChatService(db=AsyncMock(), user_id="user-1")
        conv = _conversation()

        service._apply_input_guardrails = AsyncMock(
            return_value=GuardrailResult(
                blocked=True,
                passed=False,
                message="input blocked",
            )
        )
        service.add_message = AsyncMock(
            side_effect=[
                SimpleNamespace(id="m1", role="user", content="bad"),
                SimpleNamespace(id="m2", role="assistant", content="input blocked"),
            ]
        )

        chunks = []
        with patch("app.services.chat.settings.DEFAULT_AI_PROVIDER", "openai"):
            async for chunk in service.chat_stream(conv, "bad", use_mcp_tools=False):
                chunks.append(chunk)

        assert chunks == ["input blocked"]

    @pytest.mark.asyncio
    async def test_chat_stream_blocks_harmful_partial_output(self):
        service = ChatService(db=AsyncMock(), user_id="user-1")
        conv = _conversation()
        service._stream_holdback_chars = 0

        service._apply_input_guardrails = AsyncMock(return_value=None)
        service.add_message = AsyncMock(
            side_effect=[
                SimpleNamespace(id="u1", role="user", content="hello"),
                SimpleNamespace(id="a1", role="assistant", content="blocked by stream guard"),
            ]
        )
        service.get_messages = AsyncMock(return_value=[_message("user", "hello")])

        async def _astream(_messages):
            yield _Chunk("This is safe. ")
            yield _Chunk("How to make a bomb.")

        service._get_llm = MagicMock(return_value=SimpleNamespace(astream=_astream))
        service._mcp_tools = {}

        async def _stream_guard(text, conversation=None):
            if "bomb" in text.lower():
                return GuardrailResult(
                    blocked=True,
                    passed=False,
                    message="blocked by stream guard",
                )
            return GuardrailResult(passed=True)

        service._apply_stream_output_guardrails = AsyncMock(side_effect=_stream_guard)
        service._apply_output_guardrails = AsyncMock(
            return_value=GuardrailResult(
                blocked=True,
                passed=False,
                message="blocked by stream guard",
            )
        )

        streamed = []
        with patch("app.services.chat.settings.DEFAULT_AI_PROVIDER", "openai"):
            async for chunk in service.chat_stream(conv, "hello", use_mcp_tools=False):
                streamed.append(chunk)

        output_text = "".join(streamed).lower()
        assert "blocked by stream guard" in output_text
        assert "bomb" not in output_text
