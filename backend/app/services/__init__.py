"""Business logic services."""

__all__ = [
    "AuthService",
    "ChatService",
    "DocumentService",
]


def __getattr__(name: str):
    if name == "AuthService":
        from app.services.auth import AuthService
        return AuthService
    if name == "ChatService":
        from app.services.chat import ChatService
        return ChatService
    if name == "DocumentService":
        from app.services.document import DocumentService
        return DocumentService
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
