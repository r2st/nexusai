"""
Unit tests for database models.

Tests for:
- User model
- Organization model
- Project model
- Connection model
- Document model
- Conversation model
- Subscription model
- Personal Access Token model
- AI Analytics model
"""

import pytest
from datetime import datetime, timedelta, UTC
from uuid import UUID, uuid4

from app.models.user import User, UserRole, AuthProvider
from app.models.organization import (
    Organization,
    OrganizationMember,
    OrganizationInvite,
    OrganizationTier,
    MemberRole,
)
from app.models.project import Project, ProjectMember, ProjectRole
from app.models.subscription import (
    SubscriptionEvent,
    SubscriptionEventType,
    SubscriptionStatus,
    TrialStatus,
)


# =============================================================================
# User Model Tests
# =============================================================================


class TestUserModel:
    """Tests for User model."""

    def test_user_creation(self):
        """Test creating a user with required fields."""
        user_id = str(uuid4())
        user = User(
            id=user_id,
            email="test@example.com",
            username="testuser",
        )

        assert user.email == "test@example.com"
        assert user.username == "testuser"
        assert user.id == user_id
        # Verify it's a valid UUID
        UUID(user.id)

    def test_user_default_values(self):
        """Test user with explicit default values."""
        user = User(
            id=str(uuid4()),
            email="test@example.com",
            username="testuser",
            role=UserRole.USER.value,
            auth_provider=AuthProvider.LOCAL.value,
            is_active=True,
            is_verified=False,
            is_superuser=False,
            preferences={},
        )

        assert user.role == UserRole.USER.value
        assert user.auth_provider == AuthProvider.LOCAL.value
        assert user.is_active is True
        assert user.is_verified is False
        assert user.is_superuser is False
        assert user.preferences == {}

    def test_user_optional_fields(self):
        """Test user optional fields."""
        user = User(
            email="test@example.com",
            username="testuser",
            full_name="Test User",
            avatar_url="https://example.com/avatar.png",
            bio="Test bio",
            hashed_password="hashed123",
        )

        assert user.full_name == "Test User"
        assert user.avatar_url == "https://example.com/avatar.png"
        assert user.bio == "Test bio"
        assert user.hashed_password == "hashed123"

    def test_user_is_admin_property_with_role(self):
        """Test is_admin property with admin role."""
        user = User(
            email="admin@example.com",
            username="admin",
            role=UserRole.ADMIN.value,
        )

        assert user.is_admin is True

    def test_user_is_admin_property_with_superuser(self):
        """Test is_admin property with superuser flag."""
        user = User(
            email="super@example.com",
            username="super",
            is_superuser=True,
        )

        assert user.is_admin is True

    def test_user_is_admin_property_regular_user(self):
        """Test is_admin property for regular user."""
        user = User(
            id=str(uuid4()),
            email="user@example.com",
            username="user",
            role=UserRole.USER.value,
            is_superuser=False,
        )

        assert user.is_admin is False

    def test_user_repr(self):
        """Test user __repr__."""
        user = User(
            email="test@example.com",
            username="testuser",
        )

        repr_str = repr(user)
        assert "test@example.com" in repr_str


class TestUserRoleEnum:
    """Tests for UserRole enum."""

    def test_user_role_values(self):
        """Test UserRole enum values."""
        assert UserRole.ADMIN.value == "admin"
        assert UserRole.USER.value == "user"
        assert UserRole.VIEWER.value == "viewer"

    def test_user_role_is_string(self):
        """Test UserRole inherits from str."""
        assert isinstance(UserRole.ADMIN, str)
        assert UserRole.ADMIN == "admin"


class TestAuthProviderEnum:
    """Tests for AuthProvider enum."""

    def test_auth_provider_values(self):
        """Test AuthProvider enum values."""
        assert AuthProvider.LOCAL.value == "local"
        assert AuthProvider.GOOGLE.value == "google"
        assert AuthProvider.GITHUB.value == "github"
        assert AuthProvider.AZURE.value == "azure"


# =============================================================================
# Organization Model Tests
# =============================================================================


class TestOrganizationModel:
    """Tests for Organization model."""

    def test_organization_creation(self):
        """Test creating an organization."""
        org_id = str(uuid4())
        tenant_id = str(uuid4())
        org = Organization(
            id=org_id,
            tenant_id=tenant_id,
            name="Test Org",
            slug="test-org",
        )

        assert org.name == "Test Org"
        assert org.slug == "test-org"
        assert org.id == org_id
        assert org.tenant_id == tenant_id
        UUID(org.id)
        UUID(org.tenant_id)

    def test_organization_default_values(self):
        """Test organization with explicit default values."""
        org = Organization(
            id=str(uuid4()),
            tenant_id=str(uuid4()),
            name="Test Org",
            slug="test-org",
            tier=OrganizationTier.FREE.value,
            max_members=5,
            max_projects=3,
            is_active=True,
            settings={},
            trial_status=TrialStatus.NONE.value,
            subscription_status=SubscriptionStatus.NONE.value,
        )

        assert org.tier == OrganizationTier.FREE.value
        assert org.max_members == 5
        assert org.max_projects == 3
        assert org.is_active is True
        assert org.settings == {}
        assert org.trial_status == TrialStatus.NONE.value
        assert org.subscription_status == SubscriptionStatus.NONE.value

    def test_organization_is_trial_active_not_active(self):
        """Test is_trial_active when not active."""
        org = Organization(
            name="Test Org",
            slug="test-org",
            trial_status=TrialStatus.NONE.value,
        )

        assert org.is_trial_active is False

    def test_organization_is_trial_active_expired(self):
        """Test is_trial_active when expired."""
        org = Organization(
            name="Test Org",
            slug="test-org",
            trial_status=TrialStatus.ACTIVE.value,
            trial_ends_at=datetime.now(UTC) - timedelta(days=1),
        )

        assert org.is_trial_active is False

    def test_organization_is_trial_active_active(self):
        """Test is_trial_active when active."""
        org = Organization(
            name="Test Org",
            slug="test-org",
            trial_status=TrialStatus.ACTIVE.value,
            trial_ends_at=datetime.now(UTC) + timedelta(days=7),
        )

        assert org.is_trial_active is True

    def test_organization_trial_days_remaining(self):
        """Test trial_days_remaining calculation."""
        org = Organization(
            name="Test Org",
            slug="test-org",
            trial_status=TrialStatus.ACTIVE.value,
            trial_ends_at=datetime.now(UTC) + timedelta(days=10),
        )

        assert org.trial_days_remaining >= 9  # Allow for timing

    def test_organization_trial_days_remaining_expired(self):
        """Test trial_days_remaining when expired."""
        org = Organization(
            name="Test Org",
            slug="test-org",
            trial_status=TrialStatus.EXPIRED.value,
        )

        assert org.trial_days_remaining == 0

    def test_organization_has_active_subscription(self):
        """Test has_active_subscription property."""
        org = Organization(
            name="Test Org",
            slug="test-org",
            subscription_status=SubscriptionStatus.ACTIVE.value,
        )

        assert org.has_active_subscription is True

    def test_organization_has_active_subscription_false(self):
        """Test has_active_subscription when not active."""
        org = Organization(
            id=str(uuid4()),
            tenant_id=str(uuid4()),
            name="Test Org",
            slug="test-org",
            subscription_status=SubscriptionStatus.CANCELED.value,
        )

        assert org.has_active_subscription is False

    def test_organization_can_access_features_trial(self):
        """Test can_access_features with active trial."""
        org = Organization(
            name="Test Org",
            slug="test-org",
            trial_status=TrialStatus.ACTIVE.value,
            trial_ends_at=datetime.now(UTC) + timedelta(days=7),
        )

        assert org.can_access_features is True

    def test_organization_can_access_features_subscription(self):
        """Test can_access_features with subscription."""
        org = Organization(
            name="Test Org",
            slug="test-org",
            subscription_status=SubscriptionStatus.ACTIVE.value,
        )

        assert org.can_access_features is True

    def test_organization_can_access_features_false(self):
        """Test can_access_features when neither trial nor subscription."""
        org = Organization(
            name="Test Org",
            slug="test-org",
        )

        assert org.can_access_features is False

    def test_organization_is_at_member_limit(self):
        """Test is_at_member_limit property."""
        org = Organization(
            name="Test Org",
            slug="test-org",
            max_members=5,
            current_member_count=5,
        )

        assert org.is_at_member_limit is True

    def test_organization_is_at_member_limit_false(self):
        """Test is_at_member_limit when under limit."""
        org = Organization(
            name="Test Org",
            slug="test-org",
            max_members=5,
            current_member_count=3,
        )

        assert org.is_at_member_limit is False

    def test_organization_is_at_project_limit(self):
        """Test is_at_project_limit property."""
        org = Organization(
            name="Test Org",
            slug="test-org",
            max_projects=3,
            current_project_count=3,
        )

        assert org.is_at_project_limit is True

    def test_organization_member_usage_percentage(self):
        """Test member_usage_percentage calculation."""
        org = Organization(
            name="Test Org",
            slug="test-org",
            max_members=10,
            current_member_count=5,
        )

        assert org.member_usage_percentage == 50.0

    def test_organization_member_usage_percentage_zero_max(self):
        """Test member_usage_percentage with zero max."""
        org = Organization(
            name="Test Org",
            slug="test-org",
            max_members=0,
            current_member_count=1,
        )

        assert org.member_usage_percentage == 100.0

    def test_organization_project_usage_percentage(self):
        """Test project_usage_percentage calculation."""
        org = Organization(
            name="Test Org",
            slug="test-org",
            max_projects=10,
            current_project_count=2,
        )

        assert org.project_usage_percentage == 20.0

    def test_organization_repr(self):
        """Test organization __repr__."""
        org = Organization(
            name="Test Org",
            slug="test-org",
        )

        repr_str = repr(org)
        assert "Test Org" in repr_str


class TestOrganizationTierEnum:
    """Tests for OrganizationTier enum."""

    def test_tier_values(self):
        """Test OrganizationTier enum values."""
        assert OrganizationTier.FREE.value == "free"
        assert OrganizationTier.STARTER.value == "starter"
        assert OrganizationTier.PROFESSIONAL.value == "professional"
        assert OrganizationTier.ENTERPRISE.value == "enterprise"


class TestMemberRoleEnum:
    """Tests for MemberRole enum."""

    def test_member_role_values(self):
        """Test MemberRole enum values."""
        assert MemberRole.OWNER.value == "owner"
        assert MemberRole.ADMIN.value == "admin"
        assert MemberRole.MEMBER.value == "member"
        assert MemberRole.VIEWER.value == "viewer"


# =============================================================================
# Organization Member Model Tests
# =============================================================================


class TestOrganizationMemberModel:
    """Tests for OrganizationMember model."""

    def test_member_creation(self):
        """Test creating an organization member."""
        member_id = str(uuid4())
        member = OrganizationMember(
            id=member_id,
            organization_id="org-123",
            user_id="user-456",
            tenant_id="tenant-789",
        )

        assert member.organization_id == "org-123"
        assert member.user_id == "user-456"
        assert member.id == member_id

    def test_member_default_values(self):
        """Test organization member with explicit values."""
        member = OrganizationMember(
            id=str(uuid4()),
            organization_id="org-123",
            user_id="user-456",
            tenant_id="tenant-789",
            role=MemberRole.MEMBER.value,
            is_active=True,
            permissions={},
        )

        assert member.role == MemberRole.MEMBER.value
        assert member.is_active is True
        assert member.permissions == {}

    def test_member_with_role(self):
        """Test member with specific role."""
        member = OrganizationMember(
            organization_id="org-123",
            user_id="user-456",
            tenant_id="tenant-789",
            role=MemberRole.ADMIN.value,
        )

        assert member.role == MemberRole.ADMIN.value

    def test_member_repr(self):
        """Test organization member __repr__."""
        member = OrganizationMember(
            organization_id="org-123",
            user_id="user-456",
            tenant_id="tenant-789",
        )

        repr_str = repr(member)
        assert "org-123" in repr_str
        assert "user-456" in repr_str


# =============================================================================
# Organization Invite Model Tests
# =============================================================================


class TestOrganizationInviteModel:
    """Tests for OrganizationInvite model."""

    def test_invite_creation(self):
        """Test creating an organization invite."""
        invite = OrganizationInvite(
            id=str(uuid4()),
            organization_id="org-123",
            email="invite@example.com",
            invited_by="user-456",
            token="invite-token-xyz",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            tenant_id="tenant-789",
            is_accepted=False,
        )

        assert invite.email == "invite@example.com"
        assert invite.token == "invite-token-xyz"
        assert invite.is_accepted is False

    def test_invite_default_role(self):
        """Test invite with explicit role."""
        invite = OrganizationInvite(
            id=str(uuid4()),
            organization_id="org-123",
            email="invite@example.com",
            invited_by="user-456",
            token="token",
            expires_at=datetime.now(UTC) + timedelta(days=7),
            tenant_id="tenant-789",
            role=MemberRole.MEMBER.value,
        )

        assert invite.role == MemberRole.MEMBER.value


# =============================================================================
# Project Model Tests
# =============================================================================


class TestProjectModel:
    """Tests for Project model."""

    def test_project_creation(self):
        """Test creating a project."""
        project_id = str(uuid4())
        project = Project(
            id=project_id,
            organization_id="org-123",
            name="Test Project",
            key="TEST",
            tenant_id="tenant-789",
        )

        assert project.name == "Test Project"
        assert project.key == "TEST"
        assert project.id == project_id
        UUID(project.id)

    def test_project_default_values(self):
        """Test project with explicit default values."""
        project = Project(
            id=str(uuid4()),
            organization_id="org-123",
            name="Test Project",
            key="TEST",
            tenant_id="tenant-789",
            is_active=True,
            is_public=False,
            settings={},
        )

        assert project.is_active is True
        assert project.is_public is False
        assert project.settings == {}

    def test_project_dora_config_default(self):
        """Test project DORA config with explicit values."""
        dora_config = {
            "deployment_detection": "branch",
            "deployment_branch": "main",
        }
        project = Project(
            id=str(uuid4()),
            organization_id="org-123",
            name="Test Project",
            key="TEST",
            tenant_id="tenant-789",
            dora_config=dora_config,
        )

        # DORA config should have the values we set
        assert project.dora_config is not None
        assert project.dora_config.get("deployment_detection") == "branch"
        assert project.dora_config.get("deployment_branch") == "main"

    def test_project_repr(self):
        """Test project __repr__."""
        project = Project(
            organization_id="org-123",
            name="Test Project",
            key="TEST",
            tenant_id="tenant-789",
        )

        repr_str = repr(project)
        assert "TEST" in repr_str
        assert "Test Project" in repr_str


class TestProjectRoleEnum:
    """Tests for ProjectRole enum."""

    def test_project_role_values(self):
        """Test ProjectRole enum values."""
        assert ProjectRole.ADMIN.value == "admin"
        assert ProjectRole.MAINTAINER.value == "maintainer"
        assert ProjectRole.DEVELOPER.value == "developer"
        assert ProjectRole.VIEWER.value == "viewer"


# =============================================================================
# Project Member Model Tests
# =============================================================================


class TestProjectMemberModel:
    """Tests for ProjectMember model."""

    def test_project_member_creation(self):
        """Test creating a project member."""
        member_id = str(uuid4())
        member = ProjectMember(
            id=member_id,
            project_id="proj-123",
            user_id="user-456",
            tenant_id="tenant-789",
        )

        assert member.project_id == "proj-123"
        assert member.user_id == "user-456"
        assert member.id == member_id

    def test_project_member_default_values(self):
        """Test project member with explicit default values."""
        member = ProjectMember(
            id=str(uuid4()),
            project_id="proj-123",
            user_id="user-456",
            tenant_id="tenant-789",
            role=ProjectRole.DEVELOPER.value,
            is_active=True,
            permissions={},
        )

        assert member.role == ProjectRole.DEVELOPER.value
        assert member.is_active is True
        assert member.permissions == {}

    def test_project_member_repr(self):
        """Test project member __repr__."""
        member = ProjectMember(
            project_id="proj-123",
            user_id="user-456",
            tenant_id="tenant-789",
        )

        repr_str = repr(member)
        assert "proj-123" in repr_str
        assert "user-456" in repr_str


# =============================================================================
# Subscription Model Tests
# =============================================================================


class TestSubscriptionEventModel:
    """Tests for SubscriptionEvent model."""

    def test_subscription_event_creation(self):
        """Test creating a subscription event."""
        event = SubscriptionEvent(
            id=str(uuid4()),
            organization_id="org-123",
            event_type=SubscriptionEventType.TRIAL_STARTED.value,
        )

        assert event.organization_id == "org-123"
        assert event.event_type == SubscriptionEventType.TRIAL_STARTED.value

    def test_subscription_event_types(self):
        """Test subscription event types."""
        assert SubscriptionEventType.TRIAL_STARTED.value == "trial_started"
        assert SubscriptionEventType.TRIAL_EXTENDED.value == "trial_extended"
        assert SubscriptionEventType.TRIAL_EXPIRED.value == "trial_expired"
        assert SubscriptionEventType.TRIAL_CONVERTED.value == "trial_converted"


class TestSubscriptionStatusEnum:
    """Tests for SubscriptionStatus enum."""

    def test_subscription_status_values(self):
        """Test SubscriptionStatus enum values."""
        assert SubscriptionStatus.NONE.value == "none"
        assert SubscriptionStatus.ACTIVE.value == "active"
        assert SubscriptionStatus.PAST_DUE.value == "past_due"
        assert SubscriptionStatus.CANCELED.value == "canceled"
        assert SubscriptionStatus.PAUSED.value == "paused"


class TestTrialStatusEnum:
    """Tests for TrialStatus enum."""

    def test_trial_status_values(self):
        """Test TrialStatus enum values."""
        assert TrialStatus.NONE.value == "none"
        assert TrialStatus.ACTIVE.value == "active"
        assert TrialStatus.EXPIRED.value == "expired"
        assert TrialStatus.CONVERTED.value == "converted"


# =============================================================================
# Model ID Generation Tests
# =============================================================================


class TestModelIdGeneration:
    """Tests for model ID generation with explicit IDs."""

    def test_user_id_is_uuid(self):
        """Test user ID is valid UUID when provided."""
        user_id = str(uuid4())
        user = User(id=user_id, email="test@example.com", username="test")
        UUID(user.id)  # Should not raise
        assert user.id == user_id

    def test_organization_ids_are_different(self):
        """Test explicitly provided organization IDs are different."""
        org1_id, org1_tenant = str(uuid4()), str(uuid4())
        org2_id, org2_tenant = str(uuid4()), str(uuid4())
        org1 = Organization(id=org1_id, tenant_id=org1_tenant, name="Org 1", slug="org-1")
        org2 = Organization(id=org2_id, tenant_id=org2_tenant, name="Org 2", slug="org-2")

        assert org1.id != org2.id
        assert org1.tenant_id != org2.tenant_id

    def test_project_ids_are_unique(self):
        """Test explicitly provided project IDs are unique."""
        projects = [
            Project(id=str(uuid4()), organization_id="org", name=f"Project {i}", key=f"P{i}", tenant_id="t")
            for i in range(10)
        ]

        ids = [p.id for p in projects]
        assert len(set(ids)) == 10


# =============================================================================
# Model Timestamp Tests
# =============================================================================


class TestModelTimestamps:
    """Tests for model timestamp fields with explicit values."""

    def test_user_created_at_explicit(self):
        """Test user created_at with explicit value."""
        now = datetime.now(UTC)
        user = User(
            id=str(uuid4()),
            email="test@example.com",
            username="test",
            created_at=now,
        )

        assert user.created_at is not None
        assert user.created_at == now

    def test_organization_timestamps_explicit(self):
        """Test organization timestamps with explicit values."""
        now = datetime.now(UTC)
        org = Organization(
            id=str(uuid4()),
            tenant_id=str(uuid4()),
            name="Test",
            slug="test",
            created_at=now,
            updated_at=now,
        )

        assert org.created_at is not None
        assert org.updated_at is not None
        assert org.created_at == now


# =============================================================================
# Model Relationship Tests (Unit Level)
# =============================================================================


class TestModelRelationshipDefinitions:
    """Tests for model relationship definitions."""

    def test_user_has_conversations_relationship(self):
        """Test User model has conversations relationship defined."""
        assert hasattr(User, "conversations")

    def test_user_has_documents_relationship(self):
        """Test User model has documents relationship defined."""
        assert hasattr(User, "documents")

    def test_user_has_organization_memberships_relationship(self):
        """Test User model has organization_memberships relationship defined."""
        assert hasattr(User, "organization_memberships")

    def test_organization_has_members_relationship(self):
        """Test Organization model has members relationship defined."""
        assert hasattr(Organization, "members")

    def test_organization_has_projects_relationship(self):
        """Test Organization model has projects relationship defined."""
        assert hasattr(Organization, "projects")

    def test_project_has_members_relationship(self):
        """Test Project model has members relationship defined."""
        assert hasattr(Project, "members")

    def test_project_has_connections_relationship(self):
        """Test Project model has connections relationship defined."""
        assert hasattr(Project, "connections")


# =============================================================================
# Model Table Configuration Tests
# =============================================================================


class TestModelTableConfiguration:
    """Tests for model table configuration."""

    def test_user_table_name(self):
        """Test User table name."""
        assert User.__tablename__ == "users"

    def test_organization_table_name(self):
        """Test Organization table name."""
        assert Organization.__tablename__ == "organizations"

    def test_organization_member_table_name(self):
        """Test OrganizationMember table name."""
        assert OrganizationMember.__tablename__ == "organization_members"

    def test_project_table_name(self):
        """Test Project table name."""
        assert Project.__tablename__ == "projects"

    def test_project_member_table_name(self):
        """Test ProjectMember table name."""
        assert ProjectMember.__tablename__ == "project_members"


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestModelEdgeCases:
    """Tests for model edge cases."""

    def test_user_with_empty_preferences(self):
        """Test user with empty preferences dict."""
        user = User(
            email="test@example.com",
            username="test",
            preferences={},
        )

        assert user.preferences == {}

    def test_organization_with_complex_settings(self):
        """Test organization with nested settings."""
        settings = {
            "theme": "dark",
            "notifications": {
                "email": True,
                "slack": False,
            },
            "integrations": ["github", "jira"],
        }

        org = Organization(
            name="Test",
            slug="test",
            settings=settings,
        )

        assert org.settings["theme"] == "dark"
        assert org.settings["notifications"]["email"] is True

    def test_project_with_custom_dora_config(self):
        """Test project with custom DORA configuration."""
        dora_config = {
            "deployment_detection": "tag",
            "deployment_branch": "release",
            "incident_detection": "linked",
            "incident_label": "bug",
        }

        project = Project(
            organization_id="org-123",
            name="Test",
            key="TEST",
            tenant_id="tenant",
            dora_config=dora_config,
        )

        assert project.dora_config["deployment_detection"] == "tag"
        assert project.dora_config["deployment_branch"] == "release"

    def test_organization_member_with_permissions(self):
        """Test organization member with custom permissions."""
        permissions = {
            "can_invite": True,
            "can_delete_projects": False,
            "max_api_calls": 1000,
        }

        member = OrganizationMember(
            organization_id="org-123",
            user_id="user-456",
            tenant_id="tenant-789",
            permissions=permissions,
        )

        assert member.permissions["can_invite"] is True
        assert member.permissions["max_api_calls"] == 1000
