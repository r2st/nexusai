"""Organization management API endpoints.

Provides endpoints for:
- Organization CRUD operations
- Member management
- Invitations
- Settings and configuration
"""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, EmailStr, Field, field_validator
import re as _re
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
import structlog

from app.api.deps import get_current_user, get_db

from app.core.authorization import (
    grant_org_membership,
    revoke_org_membership,
    openfga_client,
    AuthorizationTuple,
)
from app.core.multitenancy import generate_tenant_id, set_tenant_context
from app.models.organization import (
    Organization,
    OrganizationMember,
    OrganizationInvite,
    MemberRole,
    OrganizationTier,
)
from app.models.user import User

router = APIRouter()


# Request/Response Models
class OrganizationCreate(BaseModel):
    """Create organization request."""

    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(..., min_length=2, max_length=100)
    description: str | None = Field(default=None, max_length=2000)
    website: str | None = Field(default=None, max_length=500)

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        if not _re.match(r"^[a-z0-9][a-z0-9-]*[a-z0-9]$", v) and len(v) > 1:
            raise ValueError("Slug must contain only lowercase alphanumeric characters and hyphens, and cannot start/end with a hyphen")
        return v


class OrganizationUpdate(BaseModel):
    """Update organization request."""

    name: str | None = None
    description: str | None = None
    website: str | None = None
    logo_url: str | None = None
    settings: dict[str, Any] | None = None


class OrganizationResponse(BaseModel):
    """Organization response."""

    id: str
    name: str
    slug: str
    description: str | None
    logo_url: str | None
    website: str | None
    tier: str
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True


class MemberResponse(BaseModel):
    """Organization member response."""

    id: str
    user_id: str
    email: str
    full_name: str | None
    role: str
    team: str | None
    department: str | None
    is_active: bool
    created_at: datetime


class InviteMemberRequest(BaseModel):
    """Invite member request."""

    email: EmailStr
    role: str = MemberRole.MEMBER.value
    team: str | None = None
    department: str | None = None


class UpdateMemberRequest(BaseModel):
    """Update member request."""

    role: str | None = None
    team: str | None = None
    department: str | None = None


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED, summary="Create an organization")
async def create_organization(
    request: OrganizationCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Organization:
    """Create a new organization."""
    # Check if slug is unique
    result = await db.execute(
        select(Organization).where(Organization.slug == request.slug)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=400,
            detail="Organization slug already exists"
        )

    # Create organization
    tenant_id = generate_tenant_id()
    org = Organization(
        tenant_id=tenant_id,
        name=request.name,
        slug=request.slug,
        description=request.description,
        website=request.website,
    )

    db.add(org)
    await db.flush()

    # Add creator as owner
    member = OrganizationMember(
        tenant_id=tenant_id,
        organization_id=org.id,
        user_id=current_user.id,
        role=MemberRole.OWNER.value,
        is_active=True,
        accepted_at=datetime.now(UTC),
    )
    db.add(member)

    # Set up authorization
    await grant_org_membership(current_user.id, org.id, "owner")

    await db.commit()
    await db.refresh(org)

    return org


@router.get("", response_model=list[OrganizationResponse], summary="List organizations")
async def list_organizations(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[Organization]:
    """List organizations the user is a member of."""
    result = await db.execute(
        select(Organization)
        .join(OrganizationMember)
        .where(
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active == True,
        )
        .order_by(Organization.created_at.desc())
        .offset(offset)
        .limit(limit)
    )
    return list(result.scalars().all())


@router.get("/{org_id}", response_model=OrganizationResponse, summary="Get organization details")
async def get_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Organization:
    """Get organization details."""
    # Check membership
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active == True,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    # Get organization
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    return org


@router.patch("/{org_id}", response_model=OrganizationResponse, summary="Update organization")
async def update_organization(
    org_id: str,
    request: OrganizationUpdate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Organization:
    """Update organization details."""
    # Check admin permission
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_([MemberRole.OWNER.value, MemberRole.ADMIN.value]),
            OrganizationMember.is_active == True,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized to update organization")

    # Get and update organization
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    _ALLOWED_UPDATE_FIELDS = {"name", "description", "website", "logo_url", "settings"}
    for field, value in request.model_dump(exclude_unset=True).items():
        if field not in _ALLOWED_UPDATE_FIELDS:
            continue
        setattr(org, field, value)

    await db.commit()
    await db.refresh(org)

    return org


@router.delete("/{org_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete organization")
async def delete_organization(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Delete an organization."""
    # Check owner permission
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role == MemberRole.OWNER.value,
            OrganizationMember.is_active == True,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Only owners can delete organizations")

    # Get organization
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()

    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")

    # Soft delete
    org.is_active = False
    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Member management
@router.get("/{org_id}/members", response_model=list[MemberResponse], summary="List organization members")
async def list_members(
    org_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> list[dict]:
    """List organization members."""
    # Check membership
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.is_active == True,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not a member of this organization")

    # Get members with user info
    result = await db.execute(
        select(OrganizationMember, User)
        .join(User)
        .where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.is_active == True,
        )
    )

    members = []
    for member, user in result:
        members.append({
            "id": member.id,
            "user_id": user.id,
            "email": user.email,
            "full_name": user.full_name,
            "role": member.role,
            "team": member.team,
            "department": member.department,
            "is_active": member.is_active,
            "created_at": member.created_at,
        })

    return members


@router.post("/{org_id}/members/invite", status_code=status.HTTP_201_CREATED, summary="Invite a member")
async def invite_member(
    org_id: str,
    request: InviteMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> dict[str, Any]:
    """Invite a new member to the organization."""
    import secrets

    # Check admin permission
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_([MemberRole.OWNER.value, MemberRole.ADMIN.value]),
            OrganizationMember.is_active == True,
        )
    )
    member = result.scalar_one_or_none()
    if not member:
        raise HTTPException(status_code=403, detail="Not authorized to invite members")

    # Check if already a member
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    existing_user = result.scalar_one_or_none()

    if existing_user:
        result = await db.execute(
            select(OrganizationMember).where(
                OrganizationMember.organization_id == org_id,
                OrganizationMember.user_id == existing_user.id,
            )
        )
        if result.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="User is already a member")

    # Create invite
    token = secrets.token_urlsafe(32)
    invite = OrganizationInvite(
        tenant_id=member.tenant_id,
        organization_id=org_id,
        email=request.email,
        role=request.role,
        invited_by=current_user.id,
        token=token,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    db.add(invite)
    await db.commit()

    logger.warning(
        "Invitation email delivery not configured — invite created but email not sent",
        email=request.email,
        org_id=str(org_id),
        token=token[:8] + "...",
    )

    return {
        "message": "Invitation created (email delivery not yet configured)",
        "email": request.email,
        "expires_at": invite.expires_at,
    }


@router.patch("/{org_id}/members/{member_id}", summary="Update member role")
async def update_member(
    org_id: str,
    member_id: str,
    request: UpdateMemberRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> MemberResponse:
    """Update a member's role or team."""
    # Check admin permission
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_([MemberRole.OWNER.value, MemberRole.ADMIN.value]),
            OrganizationMember.is_active == True,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized to update members")

    # Get member
    result = await db.execute(
        select(OrganizationMember, User)
        .join(User)
        .where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == org_id,
        )
    )
    row = result.first()

    if not row:
        raise HTTPException(status_code=404, detail="Member not found")

    member, user = row

    # Update fields
    if request.role:
        # Update authorization
        await revoke_org_membership(user.id, org_id, member.role)
        await grant_org_membership(user.id, org_id, request.role)
        member.role = request.role

    if request.team is not None:
        member.team = request.team
    if request.department is not None:
        member.department = request.department

    await db.commit()

    return MemberResponse(
        id=member.id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=member.role,
        team=member.team,
        department=member.department,
        is_active=member.is_active,
        created_at=member.created_at,
    )


@router.delete("/{org_id}/members/{member_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Remove organization member")
async def remove_member(
    org_id: str,
    member_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Response:
    """Remove a member from the organization."""
    # Check admin permission
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.organization_id == org_id,
            OrganizationMember.user_id == current_user.id,
            OrganizationMember.role.in_([MemberRole.OWNER.value, MemberRole.ADMIN.value]),
            OrganizationMember.is_active == True,
        )
    )
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized to remove members")

    # Get member
    result = await db.execute(
        select(OrganizationMember).where(
            OrganizationMember.id == member_id,
            OrganizationMember.organization_id == org_id,
        )
    )
    member = result.scalar_one_or_none()

    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Can't remove owner
    if member.role == MemberRole.OWNER.value:
        raise HTTPException(status_code=400, detail="Cannot remove organization owner")

    # Revoke authorization and deactivate
    await revoke_org_membership(member.user_id, org_id, member.role)
    member.is_active = False

    # Update cached member count using SQL expression to avoid race conditions
    result = await db.execute(
        select(Organization).where(Organization.id == org_id)
    )
    org = result.scalar_one_or_none()
    if org:
        org.current_member_count = Organization.current_member_count - 1

    await db.commit()

    return Response(status_code=status.HTTP_204_NO_CONTENT)


# Import timedelta for invite expiration
from datetime import timedelta

logger = structlog.get_logger()

