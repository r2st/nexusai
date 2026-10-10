"""Code Review API endpoints."""

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from pydantic import BaseModel, Field
import structlog

from app.api.deps import get_current_user
from app.models.user import User
from app.services.code_review import (
    CodeReviewService,
    CodeReview,
    PRInfo,
    get_code_review_service,
)

logger = structlog.get_logger()

router = APIRouter(prefix="/code-review", tags=["code-review"])


# Request/Response Models
class ReviewPRRequest(BaseModel):
    """Request to review a PR."""

    owner: str = Field(..., description="Repository owner")
    repo: str = Field(..., description="Repository name")
    pr_number: int = Field(..., description="Pull request number")
    post_review: bool = Field(True, description="Post review to GitHub/GitLab")
    context: dict[str, Any] | None = Field(None, description="Additional context")


class ReviewMRRequest(BaseModel):
    """Request to review a GitLab MR."""

    project: str = Field(..., description="Project path or ID")
    mr_iid: int = Field(..., description="Merge request IID")
    post_review: bool = Field(True, description="Post review to GitLab")
    context: dict[str, Any] | None = Field(None, description="Additional context")


class ReviewDiffRequest(BaseModel):
    """Request to review a diff directly."""

    diff: str = Field(..., description="Unified diff content")
    pr_info: dict[str, Any] = Field(..., description="PR information")
    context: dict[str, Any] | None = Field(None, description="Additional context")


class ReviewResponse(BaseModel):
    """Code review response."""

    pr_number: int
    repository: str
    summary: str
    overall_quality: float
    comments_count: int
    smells_count: int
    approval_recommendation: str
    metrics: dict[str, Any]


# Dependencies
async def get_review_service() -> CodeReviewService:
    """Get code review service instance."""
    return get_code_review_service()


# Endpoints
@router.post("/github/review", response_model=ReviewResponse)
async def review_github_pr(
    request: ReviewPRRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CodeReviewService, Depends(get_review_service)],
) -> ReviewResponse:
    """Review a GitHub pull request.

    Analyzes the PR diff, detects code smells, and generates
    LLM-powered review comments. Optionally posts the review
    to GitHub.
    """
    try:
        review = await service.review_github_pr(
            owner=request.owner,
            repo=request.repo,
            pr_number=request.pr_number,
            post_review=request.post_review,
            context=request.context,
        )

        return ReviewResponse(
            pr_number=review.pr_number,
            repository=review.repository,
            summary=review.summary,
            overall_quality=review.overall_quality,
            comments_count=len(review.comments),
            smells_count=len(review.smells),
            approval_recommendation=review.approval_recommendation,
            metrics=review.metrics,
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid review request. Please check the repository and PR details.",
        )
    except Exception as e:
        logger.error("Failed to review GitHub PR", owner=request.owner, repo=request.repo, pr=request.pr_number, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to review PR. Please try again later.",
        )


@router.post("/gitlab/review", response_model=ReviewResponse)
async def review_gitlab_mr(
    request: ReviewMRRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    service: Annotated[CodeReviewService, Depends(get_review_service)],
) -> ReviewResponse:
    """Review a GitLab merge request.

    Analyzes the MR diff, detects code smells, and generates
    LLM-powered review comments. Optionally posts the review
    to GitLab.
    """
    try:
        review = await service.review_gitlab_mr(
            project=request.project,
            mr_iid=request.mr_iid,
            post_review=request.post_review,
            context=request.context,
        )

        return ReviewResponse(
            pr_number=review.pr_number,
            repository=review.repository,
            summary=review.summary,
            overall_quality=review.overall_quality,
            comments_count=len(review.comments),
            smells_count=len(review.smells),
            approval_recommendation=review.approval_recommendation,
            metrics=review.metrics,
        )

    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid review request. Please check the project and MR details.",
        )
    except Exception as e:
        logger.error("Failed to review GitLab MR", project=request.project, mr_iid=request.mr_iid, error=str(e))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to review MR. Please try again later.",
        )


@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    service: Annotated[CodeReviewService, Depends(get_review_service)],
    x_github_event: Annotated[str, Header()],
    x_hub_signature_256: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Handle GitHub webhook events.

    Automatically reviews PRs when they are opened, synchronized,
    or reopened.
    """
    payload = await request.json()

    try:
        review = await service.handle_webhook(
            provider="github",
            event_type=x_github_event,
            payload=payload,
            signature=x_hub_signature_256,
        )

        if review:
            return {
                "status": "reviewed",
                "pr_number": review.pr_number,
                "quality": review.overall_quality,
                "recommendation": review.approval_recommendation,
            }

        return {"status": "skipped", "reason": "Event not configured for review"}

    except Exception as e:
        logger.error("GitHub webhook processing failed", event=x_github_event, error=str(e))
        return {"status": "error", "error": "Webhook processing failed"}


@router.post("/webhook/gitlab")
async def gitlab_webhook(
    request: Request,
    service: Annotated[CodeReviewService, Depends(get_review_service)],
    x_gitlab_token: Annotated[str | None, Header()] = None,
) -> dict[str, Any]:
    """Handle GitLab webhook events.

    Automatically reviews MRs when they are opened or updated.
    """
    payload = await request.json()
    event_type = payload.get("object_kind", "")

    try:
        review = await service.handle_webhook(
            provider="gitlab",
            event_type=event_type,
            payload=payload,
            signature=x_gitlab_token,
        )

        if review:
            return {
                "status": "reviewed",
                "mr_iid": review.pr_number,
                "quality": review.overall_quality,
                "recommendation": review.approval_recommendation,
            }

        return {"status": "skipped", "reason": "Event not configured for review"}

    except Exception as e:
        logger.error("GitLab webhook processing failed", event=event_type, error=str(e))
        return {"status": "error", "error": "Webhook processing failed"}


@router.get("/health")
async def health_check() -> dict[str, str]:
    """Check code review service health."""
    return {"status": "healthy", "service": "code-review"}
