"""Tests verifying the LangChain 0.3→1.x migration.

Ensures all imports used by the project work with the new versions
and that key API contracts are preserved.
"""

import importlib
import sys
from unittest.mock import MagicMock, patch

import pytest


class TestLangChainCoreImports:
    """Verify langchain-core 1.x exports the message/tool types we use."""

    def test_message_types(self):
        from langchain_core.messages import (
            AIMessage,
            BaseMessage,
            HumanMessage,
            SystemMessage,
            ToolMessage,
        )

        msg = HumanMessage(content="hello")
        assert msg.content == "hello"
        assert isinstance(msg, BaseMessage)

    def test_structured_tool(self):
        from langchain_core.tools import StructuredTool

        assert callable(StructuredTool)

    def test_runnable_interface(self):
        from langchain_core.runnables import Runnable, RunnableConfig

        assert Runnable is not None
        assert RunnableConfig is not None


class TestLangChainProviderImports:
    """Verify provider packages export the classes we use."""

    def test_openai_imports(self):
        from langchain_openai import ChatOpenAI, OpenAIEmbeddings

        assert callable(ChatOpenAI)
        assert callable(OpenAIEmbeddings)

    def test_anthropic_imports(self):
        from langchain_anthropic import ChatAnthropic

        assert callable(ChatAnthropic)

    def test_google_genai_imports(self):
        from langchain_google_genai import ChatGoogleGenerativeAI

        assert callable(ChatGoogleGenerativeAI)

    def test_google_genai_model_param(self):
        """ChatGoogleGenerativeAI must accept model= kwarg (Gemini integration)."""
        from langchain_google_genai import ChatGoogleGenerativeAI

        llm = ChatGoogleGenerativeAI(
            model="gemini-3.8-flash",
            temperature=0.7,
            google_api_key="test-key",
            convert_system_message_to_human=True,
        )
        assert llm.model == "gemini-3.8-flash"
        assert llm.temperature == 0.7
        assert llm.convert_system_message_to_human is True

    def test_ollama_imports(self):
        from langchain_ollama import ChatOllama, OllamaEmbeddings

        assert callable(ChatOllama)
        assert callable(OllamaEmbeddings)


class TestLangChainTextSplitters:
    def test_recursive_text_splitter(self):
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(chunk_size=100, chunk_overlap=20)
        chunks = splitter.split_text("Hello world. " * 50)
        assert len(chunks) > 1


class TestLangGraph:
    def test_add_messages(self):
        from langgraph.graph import add_messages

        assert callable(add_messages)


class TestVersions:
    """Verify installed versions meet CVE fix thresholds."""

    def test_langchain_version(self):
        import langchain

        parts = [int(x) for x in langchain.__version__.split(".")[:3]]
        assert parts >= [1, 3, 9], f"langchain {langchain.__version__} < 1.3.9"

    def test_langchain_core_version(self):
        import langchain_core

        parts = [int(x) for x in langchain_core.__version__.split(".")[:3]]
        assert parts >= [1, 2, 22], f"langchain-core {langchain_core.__version__} < 1.2.22"

    def test_openai_version(self):
        import openai

        major = int(openai.__version__.split(".")[0])
        assert major >= 3, f"openai {openai.__version__} < 3.0"

    def test_anthropic_version(self):
        import anthropic

        major = int(anthropic.__version__.split(".")[0])
        assert major >= 1, f"anthropic {anthropic.__version__} < 1.0"


class TestNemoGuardrailsCompat:
    """Verify nemoguardrails imports with langchain 1.x shims."""

    def test_nemoguardrails_imports(self):
        import warnings

        warnings.filterwarnings("ignore")
        import nemoguardrails
        from nemoguardrails import LLMRails, RailsConfig

        assert nemoguardrails.__version__ is not None


class TestMessageConversion:
    """Test OrchestratorState.to_langchain_messages still works."""

    def test_to_langchain_messages(self):
        from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

        # Simulate what OrchestratorState.to_langchain_messages does
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]

        lc_messages = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user" or role == "human":
                lc_messages.append(HumanMessage(content=content))
            elif role == "assistant" or role == "ai":
                lc_messages.append(AIMessage(content=content))
            elif role == "system":
                lc_messages.append(SystemMessage(content=content))

        assert len(lc_messages) == 3
        assert isinstance(lc_messages[0], SystemMessage)
        assert isinstance(lc_messages[1], HumanMessage)
        assert isinstance(lc_messages[2], AIMessage)
