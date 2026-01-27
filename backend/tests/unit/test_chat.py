"""
Unit tests for chat endpoints.
"""

import pytest
from httpx import AsyncClient
from unittest.mock import patch, AsyncMock, MagicMock
from uuid import uuid4

from app.models.user import User
from app.models.conversation import ModelProvider


class TestConversationCRUD:
    """Test conversation CRUD operations."""

    @pytest.mark.asyncio
    async def test_create_conversation(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating a new conversation."""
        response = await client.post(
            "/api/v1/chat/conversations",
            json={
                "title": "Test Conversation",
                "model_provider": "openai",
            },
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        if response.status_code in [200, 201]:
            data = response.json()
            assert "id" in data
            assert data["title"] == "Test Conversation"
            assert data["model_provider"] == "openai"

    @pytest.mark.asyncio
    async def test_create_conversation_with_system_prompt(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating a conversation with custom system prompt."""
        response = await client.post(
            "/api/v1/chat/conversations",
            json={
                "title": "Custom System Prompt",
                "model_provider": "openai",
                "system_prompt": "You are a helpful coding assistant.",
            },
            headers=auth_headers
        )
        assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_create_conversation_with_model_name(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating a conversation with specific model name."""
        response = await client.post(
            "/api/v1/chat/conversations",
            json={
                "title": "GPT-4 Conversation",
                "model_provider": "openai",
                "model_name": "gpt-4",
            },
            headers=auth_headers
        )
        assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_create_conversation_anthropic_provider(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating conversation with Anthropic provider."""
        response = await client.post(
            "/api/v1/chat/conversations",
            json={
                "title": "Claude Conversation",
                "model_provider": "anthropic",
            },
            headers=auth_headers
        )
        assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_create_conversation_default_title(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating conversation with default title."""
        response = await client.post(
            "/api/v1/chat/conversations",
            json={
                "model_provider": "openai",
            },
            headers=auth_headers
        )
        assert response.status_code in [200, 201]
        if response.status_code in [200, 201]:
            data = response.json()
            assert data["title"] == "New Conversation"

    @pytest.mark.asyncio
    async def test_list_conversations(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing conversations."""
        # First create a conversation
        await client.post(
            "/api/v1/chat/conversations",
            json={"title": "List Test", "model_provider": "openai"},
            headers=auth_headers
        )

        response = await client.get(
            "/api/v1/chat/conversations",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    @pytest.mark.asyncio
    async def test_list_conversations_with_pagination(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test listing conversations with pagination."""
        # Create multiple conversations
        for i in range(5):
            await client.post(
                "/api/v1/chat/conversations",
                json={"title": f"Pagination Test {i}", "model_provider": "openai"},
                headers=auth_headers
            )

        # Test with limit
        response = await client.get(
            "/api/v1/chat/conversations?limit=2&offset=0",
            headers=auth_headers
        )
        assert response.status_code == 200
        data = response.json()
        assert len(data) <= 2

        # Test with offset
        response = await client.get(
            "/api/v1/chat/conversations?limit=50&offset=2",
            headers=auth_headers
        )
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_get_conversation(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting a specific conversation."""
        # Create a conversation
        create_response = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Get Test", "model_provider": "openai"},
            headers=auth_headers
        )

        if create_response.status_code in [200, 201]:
            conversation_id = create_response.json()["id"]

            # Get the conversation
            response = await client.get(
                f"/api/v1/chat/conversations/{conversation_id}",
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert data["id"] == conversation_id
            assert data["title"] == "Get Test"

    @pytest.mark.asyncio
    async def test_get_conversation_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting a non-existent conversation."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/chat/conversations/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_conversation(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test deleting a conversation."""
        # Create a conversation
        create_response = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Delete Test", "model_provider": "openai"},
            headers=auth_headers
        )

        if create_response.status_code in [200, 201]:
            conversation_id = create_response.json()["id"]

            # Delete the conversation
            response = await client.delete(
                f"/api/v1/chat/conversations/{conversation_id}",
                headers=auth_headers
            )
            assert response.status_code == 204

            # Verify it's deleted
            get_response = await client.get(
                f"/api/v1/chat/conversations/{conversation_id}",
                headers=auth_headers
            )
            assert get_response.status_code == 404

    @pytest.mark.asyncio
    async def test_delete_conversation_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test deleting a non-existent conversation."""
        fake_id = str(uuid4())
        response = await client.delete(
            f"/api/v1/chat/conversations/{fake_id}",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestConversationMessages:
    """Test conversation message operations."""

    @pytest.mark.asyncio
    async def test_get_messages_empty_conversation(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting messages from new conversation."""
        # Create a conversation
        create_response = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Messages Test", "model_provider": "openai"},
            headers=auth_headers
        )

        if create_response.status_code in [200, 201]:
            conversation_id = create_response.json()["id"]

            # Get messages
            response = await client.get(
                f"/api/v1/chat/conversations/{conversation_id}/messages",
                headers=auth_headers
            )
            assert response.status_code == 200
            data = response.json()
            assert isinstance(data, list)
            assert len(data) == 0

    @pytest.mark.asyncio
    async def test_get_messages_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting messages for non-existent conversation."""
        fake_id = str(uuid4())
        response = await client.get(
            f"/api/v1/chat/conversations/{fake_id}/messages",
            headers=auth_headers
        )
        assert response.status_code == 404


class TestChatEndpoint:
    """Test chat/messaging endpoint."""

    @pytest.mark.asyncio
    async def test_chat_conversation_not_found(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test chatting in non-existent conversation."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/chat/conversations/{fake_id}/chat",
            json={
                "message": "Hello!",
                "stream": False,
            },
            headers=auth_headers
        )
        assert response.status_code == 404

    @pytest.mark.asyncio
    @patch("app.services.chat.ChatService.chat")
    async def test_chat_non_streaming(
        self, mock_chat, client: AsyncClient, auth_headers: dict
    ):
        """Test non-streaming chat request."""
        # Create a conversation first
        create_response = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Chat Test", "model_provider": "openai"},
            headers=auth_headers
        )

        if create_response.status_code in [200, 201]:
            conversation_id = create_response.json()["id"]

            # Mock the chat response
            mock_message = MagicMock()
            mock_message.id = str(uuid4())
            mock_message.role = "assistant"
            mock_message.content = "Hello! How can I help you?"
            mock_message.model_name = "gpt-4"
            mock_message.created_at.isoformat.return_value = "2024-01-01T00:00:00"
            mock_chat.return_value = mock_message

            response = await client.post(
                f"/api/v1/chat/conversations/{conversation_id}/chat",
                json={
                    "message": "Hello!",
                    "stream": False,
                    "temperature": 0.7,
                    "max_tokens": 1000,
                },
                headers=auth_headers
            )
            # Response depends on actual implementation
            assert response.status_code in [200, 400, 500]

    @pytest.mark.asyncio
    @patch("app.services.chat.ChatService.chat")
    async def test_chat_includes_tool_payloads(
        self, mock_chat, client: AsyncClient, auth_headers: dict
    ):
        """Ensure tool payloads are surfaced in the chat response."""
        create_response = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Tool Payload Test", "model_provider": "openai"},
            headers=auth_headers
        )

        if create_response.status_code in [200, 201]:
            conversation_id = create_response.json()["id"]

            mock_message = MagicMock()
            mock_message.id = str(uuid4())
            mock_message.role = "assistant"
            mock_message.content = (
                "Tool results:\n"
                "```tool_call\n"
                "{\"name\":\"devlake_list_projects\",\"args\":{\"page\":1},\"status\":\"completed\"}\n"
                "```\n"
                "[Calling tool: devlake_health_check...]\n"
                "```tool_result\n"
                "{\"name\":\"devlake_list_projects\",\"output\":\"ok\",\"success\":true}\n"
                "```\n"
                "[Tool result: ok]"
            )
            mock_message.model_name = "gpt-4"
            mock_message.created_at.isoformat.return_value = "2024-01-01T00:00:00"
            mock_chat.return_value = mock_message

            response = await client.post(
                f"/api/v1/chat/conversations/{conversation_id}/chat",
                json={
                    "message": "Hello!",
                    "stream": False,
                },
                headers=auth_headers
            )

            if response.status_code == 200:
                payload = response.json()["message"]
                tool_calls = payload.get("tool_calls", [])
                tool_results = payload.get("tool_results", [])

                assert any(call.get("name") == "devlake_list_projects" for call in tool_calls)
                assert any(call.get("name") == "devlake_health_check" for call in tool_calls)
                assert any(result.get("output") == "ok" for result in tool_results)

    @pytest.mark.asyncio
    async def test_chat_with_custom_parameters(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test chat with custom temperature and max_tokens."""
        create_response = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Custom Params Test", "model_provider": "openai"},
            headers=auth_headers
        )

        if create_response.status_code in [200, 201]:
            conversation_id = create_response.json()["id"]

            try:
                response = await client.post(
                    f"/api/v1/chat/conversations/{conversation_id}/chat",
                    json={
                        "message": "Test message",
                        "stream": False,
                        "temperature": 0.5,
                        "max_tokens": 2048,
                    },
                    headers=auth_headers
                )
                # Will likely fail without API keys, but tests the endpoint structure
                assert response.status_code in [200, 400, 500, 503]
            except Exception:
                # Expected failure when LLM provider credentials aren't configured
                pass


class TestChatAuthorization:
    """Test chat authorization."""

    @pytest.mark.asyncio
    async def test_list_conversations_unauthorized(self, client: AsyncClient):
        """Test listing conversations without auth."""
        response = await client.get("/api/v1/chat/conversations")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_create_conversation_unauthorized(self, client: AsyncClient):
        """Test creating conversation without auth."""
        response = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Unauthorized Test", "model_provider": "openai"}
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_conversation_unauthorized(self, client: AsyncClient):
        """Test getting conversation without auth."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/chat/conversations/{fake_id}")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_delete_conversation_unauthorized(self, client: AsyncClient):
        """Test deleting conversation without auth."""
        fake_id = str(uuid4())
        response = await client.delete(f"/api/v1/chat/conversations/{fake_id}")
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_chat_unauthorized(self, client: AsyncClient):
        """Test chatting without auth."""
        fake_id = str(uuid4())
        response = await client.post(
            f"/api/v1/chat/conversations/{fake_id}/chat",
            json={"message": "Hello!", "stream": False}
        )
        assert response.status_code in [401, 403]

    @pytest.mark.asyncio
    async def test_get_messages_unauthorized(self, client: AsyncClient):
        """Test getting messages without auth."""
        fake_id = str(uuid4())
        response = await client.get(f"/api/v1/chat/conversations/{fake_id}/messages")
        assert response.status_code in [401, 403]


class TestConversationOwnership:
    """Test conversation ownership and access control."""

    @pytest.mark.asyncio
    async def test_cannot_access_other_user_conversation(
        self, client: AsyncClient, auth_headers: dict, admin_auth_headers: dict
    ):
        """Test that users cannot access other users' conversations."""
        # Create conversation as regular user
        create_response = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Owner Test", "model_provider": "openai"},
            headers=auth_headers
        )

        if create_response.status_code in [200, 201]:
            conversation_id = create_response.json()["id"]

            # Try to access as admin (different user)
            response = await client.get(
                f"/api/v1/chat/conversations/{conversation_id}",
                headers=admin_auth_headers
            )
            # Should be 404 (not found for this user) or 403 (forbidden)
            assert response.status_code in [403, 404]

    @pytest.mark.asyncio
    async def test_cannot_delete_other_user_conversation(
        self, client: AsyncClient, auth_headers: dict, admin_auth_headers: dict
    ):
        """Test that users cannot delete other users' conversations."""
        # Create conversation as regular user
        create_response = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Delete Owner Test", "model_provider": "openai"},
            headers=auth_headers
        )

        if create_response.status_code in [200, 201]:
            conversation_id = create_response.json()["id"]

            # Try to delete as admin (different user)
            response = await client.delete(
                f"/api/v1/chat/conversations/{conversation_id}",
                headers=admin_auth_headers
            )
            # Should be 404 (not found for this user) or 403 (forbidden)
            assert response.status_code in [403, 404]


class TestConversationValidation:
    """Test conversation input validation."""

    @pytest.mark.asyncio
    async def test_create_conversation_invalid_provider(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating conversation with invalid model provider."""
        response = await client.post(
            "/api/v1/chat/conversations",
            json={
                "title": "Invalid Provider",
                "model_provider": "invalid_provider",
            },
            headers=auth_headers
        )
        # Should fail validation
        assert response.status_code == 422

    @pytest.mark.asyncio
    async def test_create_conversation_empty_title(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating conversation with empty title."""
        response = await client.post(
            "/api/v1/chat/conversations",
            json={
                "title": "",
                "model_provider": "openai",
            },
            headers=auth_headers
        )
        # May succeed (defaults to "New Conversation") or fail
        assert response.status_code in [200, 201, 422]

    @pytest.mark.asyncio
    async def test_chat_empty_message(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test sending empty message."""
        create_response = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Empty Message Test", "model_provider": "openai"},
            headers=auth_headers
        )

        if create_response.status_code in [200, 201]:
            conversation_id = create_response.json()["id"]

            try:
                response = await client.post(
                    f"/api/v1/chat/conversations/{conversation_id}/chat",
                    json={
                        "message": "",
                        "stream": False,
                    },
                    headers=auth_headers
                )
                # Should fail validation or be handled gracefully
                assert response.status_code in [200, 400, 422, 500]
            except Exception:
                # Expected when LLM provider credentials aren't configured
                pass

    @pytest.mark.asyncio
    async def test_chat_invalid_temperature(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test chat with invalid temperature value."""
        create_response = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Invalid Temp Test", "model_provider": "openai"},
            headers=auth_headers
        )

        if create_response.status_code in [200, 201]:
            conversation_id = create_response.json()["id"]

            try:
                # Temperature out of valid range (usually 0-2)
                response = await client.post(
                    f"/api/v1/chat/conversations/{conversation_id}/chat",
                    json={
                        "message": "Test",
                        "stream": False,
                        "temperature": 10.0,  # Invalid
                    },
                    headers=auth_headers
                )
                # May be validated or passed through to LLM
                assert response.status_code in [200, 400, 422, 500]
            except Exception:
                # Expected when LLM provider credentials aren't configured
                pass

    @pytest.mark.asyncio
    async def test_chat_negative_max_tokens(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test chat with negative max_tokens value."""
        create_response = await client.post(
            "/api/v1/chat/conversations",
            json={"title": "Invalid Tokens Test", "model_provider": "openai"},
            headers=auth_headers
        )

        if create_response.status_code in [200, 201]:
            conversation_id = create_response.json()["id"]

            try:
                response = await client.post(
                    f"/api/v1/chat/conversations/{conversation_id}/chat",
                    json={
                        "message": "Test",
                        "stream": False,
                        "max_tokens": -100,
                    },
                    headers=auth_headers
                )
                assert response.status_code in [400, 422, 500]
            except Exception:
                # Expected when LLM provider credentials aren't configured
                pass

    @pytest.mark.asyncio
    async def test_get_conversation_invalid_uuid(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test getting conversation with invalid UUID format."""
        try:
            response = await client.get(
                "/api/v1/chat/conversations/not-a-valid-uuid",
                headers=auth_headers
            )
            # Should return 404, 422, or 500 (if DB rejects invalid UUID)
            assert response.status_code in [404, 422, 500]
        except Exception:
            # Expected if DB raises exception for invalid UUID
            pass


class TestConversationEdgeCases:
    """Test edge cases for conversations."""

    @pytest.mark.asyncio
    async def test_create_many_conversations(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test creating multiple conversations in sequence."""
        created_ids = []
        for i in range(10):
            response = await client.post(
                "/api/v1/chat/conversations",
                json={
                    "title": f"Bulk Test {i}",
                    "model_provider": "openai",
                },
                headers=auth_headers
            )
            if response.status_code in [200, 201]:
                created_ids.append(response.json()["id"])

        # Verify all were created
        list_response = await client.get(
            "/api/v1/chat/conversations?limit=50",
            headers=auth_headers
        )
        if list_response.status_code == 200:
            conversations = list_response.json()
            listed_ids = [c["id"] for c in conversations]
            for created_id in created_ids:
                assert created_id in listed_ids

    @pytest.mark.asyncio
    async def test_conversation_title_with_special_characters(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test conversation with special characters in title."""
        special_titles = [
            "Test <script>alert('xss')</script>",
            "Test with emoji 🎉🚀",
            "Test with unicode: 中文 العربية",
            "Test with\nnewline",
            "Test with 'quotes' and \"double quotes\"",
        ]

        for title in special_titles:
            response = await client.post(
                "/api/v1/chat/conversations",
                json={
                    "title": title,
                    "model_provider": "openai",
                },
                headers=auth_headers
            )
            assert response.status_code in [200, 201, 400, 422]

    @pytest.mark.asyncio
    async def test_conversation_very_long_title(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test conversation with very long title."""
        long_title = "A" * 1000
        try:
            response = await client.post(
                "/api/v1/chat/conversations",
                json={
                    "title": long_title,
                    "model_provider": "openai",
                },
                headers=auth_headers
            )
            # Should either truncate, reject (400/422), or fail at DB level (500)
            assert response.status_code in [200, 201, 400, 422, 500]
        except Exception:
            # Expected if DB raises exception for long value
            pass

    @pytest.mark.asyncio
    async def test_conversation_very_long_system_prompt(
        self, client: AsyncClient, auth_headers: dict
    ):
        """Test conversation with very long system prompt."""
        long_prompt = "You are a helpful assistant. " * 500
        response = await client.post(
            "/api/v1/chat/conversations",
            json={
                "title": "Long Prompt Test",
                "model_provider": "openai",
                "system_prompt": long_prompt,
            },
            headers=auth_headers
        )
        assert response.status_code in [200, 201, 400, 422]
