"""
LangServe integration for NexusAI.

Exposes ChatService as LangChain runnables for standardized API deployment.
"""

from .runnable import ChatRunnable

__all__ = ["ChatRunnable"]
