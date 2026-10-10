"""Input validation utilities for adversarial input protection."""

import re
from fastapi import HTTPException, status


_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]{0,127}$")


def validate_cypher_identifier(value: str, field_name: str = "identifier") -> str:
    """Validate a value is safe to use as a Cypher label or relationship type.

    Only allows alphanumeric characters and underscores, starting with
    a letter or underscore, up to 128 characters.
    """
    if not _IDENTIFIER_RE.match(value):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}: must be alphanumeric/underscore, "
            f"start with a letter or underscore, max 128 chars.",
        )
    return value


def validate_no_path_traversal(value: str, field_name: str = "path") -> str:
    """Reject path traversal attempts in file keys/paths."""
    if ".." in value or value.startswith("/") or "\x00" in value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid {field_name}: path traversal not allowed.",
        )
    return value


def sanitize_error_string(value: str, max_length: int = 200) -> str:
    """Sanitize a user-provided value before including it in error messages."""
    sanitized = value[:max_length]
    sanitized = re.sub(r"[<>&\"']", "", sanitized)
    return sanitized
