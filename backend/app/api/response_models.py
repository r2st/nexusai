"""Shared API response models for consistent error and pagination formats."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ErrorResponse(BaseModel):
    """Standard error response format for all API endpoints."""

    detail: str
    code: str | None = None


class PaginatedResponse(BaseModel, Generic[T]):
    """Standard paginated response wrapper."""

    items: list[Any] = Field(default_factory=list)
    total: int
    page: int
    page_size: int
    has_more: bool


class StatusResponse(BaseModel):
    """Generic status response for mutations that don't return a resource."""

    status: str
    message: str | None = None
