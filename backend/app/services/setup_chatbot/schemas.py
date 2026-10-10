"""Schemas for Setup Chatbot Service.

Comprehensive plugin configurations for 25+ data sources with
security features and validation.
"""

import re
import secrets
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


class ActionType(str, Enum):
    """Types of actions the chatbot can perform."""

    # Navigation
    NAVIGATE = "navigate"
    SHOW_OPTIONS = "show_options"

    # Connection actions
    CREATE_CONNECTION = "create_connection"
    TEST_CONNECTION = "test_connection"
    UPDATE_CONNECTION = "update_connection"
    DELETE_CONNECTION = "delete_connection"
    LIST_CONNECTIONS = "list_connections"

    # Project actions
    CREATE_PROJECT = "create_project"
    UPDATE_PROJECT = "update_project"
    LIST_PROJECTS = "list_projects"

    # Pipeline actions
    CREATE_PIPELINE = "create_pipeline"
    TRIGGER_PIPELINE = "trigger_pipeline"
    LIST_PIPELINES = "list_pipelines"

    # Blueprint actions
    CREATE_BLUEPRINT = "create_blueprint"
    UPDATE_BLUEPRINT = "update_blueprint"

    # Scope actions
    ADD_SCOPE = "add_scope"
    LIST_SCOPES = "list_scopes"

    # Information
    SHOW_STATUS = "show_status"
    SHOW_METRICS = "show_metrics"
    SHOW_HELP = "show_help"

    # Flow control
    CONFIRM = "confirm"
    CANCEL = "cancel"
    RETRY = "retry"
    COMPLETE = "complete"


class PluginCategory(str, Enum):
    """Categories for organizing plugins."""

    SOURCE_CONTROL = "source_control"
    ISSUE_TRACKING = "issue_tracking"
    CI_CD = "ci_cd"
    CODE_QUALITY = "code_quality"
    INCIDENT_MANAGEMENT = "incident_management"
    COMMUNICATION = "communication"
    PROJECT_MANAGEMENT = "project_management"
    CLOUD_PROVIDER = "cloud_provider"
    MONITORING = "monitoring"
    SECURITY = "security"
    CUSTOM = "custom"


class PluginType(str, Enum):
    """Supported DevLake plugins - 25+ data sources."""

    # Source Control
    GITHUB = "github"
    GITLAB = "gitlab"
    BITBUCKET = "bitbucket"
    BITBUCKET_SERVER = "bitbucket_server"
    GITEE = "gitee"
    GITEA = "gitea"
    AZURE_REPOS = "azurerepos"
    AWS_CODECOMMIT = "codecommit"

    # Issue Tracking
    JIRA = "jira"
    JIRA_SERVER = "jira_server"
    LINEAR = "linear"
    ASANA = "asana"
    MONDAY = "monday"
    CLICKUP = "clickup"
    NOTION = "notion"
    TRELLO = "trello"
    YOUTRACK = "youtrack"
    SHORTCUT = "shortcut"
    TAPD = "tapd"
    ZENTAO = "zentao"
    TEAMBITION = "teambition"

    # CI/CD
    JENKINS = "jenkins"
    GITHUB_ACTIONS = "github_actions"
    GITLAB_CI = "gitlab_ci"
    AZURE_DEVOPS = "azuredevops"
    CIRCLECI = "circleci"
    TRAVIS_CI = "travisci"
    BAMBOO = "bamboo"
    TEAMCITY = "teamcity"
    DRONE = "drone"
    BUILDKITE = "buildkite"
    HARNESS = "harness"
    ARGO_CD = "argocd"
    SPINNAKER = "spinnaker"
    AWS_CODEPIPELINE = "codepipeline"
    TEKTON = "tekton"

    # Code Quality
    SONARQUBE = "sonarqube"
    SONARCLOUD = "sonarcloud"
    CODECLIMATE = "codeclimate"
    CODECOV = "codecov"
    COVERALLS = "coveralls"
    SNYK = "snyk"
    CHECKMARX = "checkmarx"
    VERACODE = "veracode"
    SEMGREP = "semgrep"

    # Incident Management
    PAGERDUTY = "pagerduty"
    OPSGENIE = "opsgenie"
    VICTOROPS = "victorops"
    STATUSPAGE = "statuspage"
    INCIDENT_IO = "incidentio"
    FIREHYDRANT = "firehydrant"
    ROOTLY = "rootly"

    # Communication
    SLACK = "slack"
    FEISHU = "feishu"
    DISCORD = "discord"
    MSTEAMS = "msteams"

    # Monitoring & Observability
    DATADOG = "datadog"
    NEWRELIC = "newrelic"
    PROMETHEUS = "prometheus"
    GRAFANA = "grafana"
    SPLUNK = "splunk"
    ELASTIC = "elastic"
    DYNATRACE = "dynatrace"
    HONEYCOMB = "honeycomb"

    # Cloud Providers
    AWS = "aws"
    AZURE = "azure"
    GCP = "gcp"
    KUBERNETES = "kubernetes"

    # Custom
    WEBHOOK = "webhook"
    REST_API = "restapi"


class AuthType(str, Enum):
    """Authentication types for plugins."""

    TOKEN = "token"
    OAUTH = "oauth"
    BASIC = "basic"
    API_KEY = "api_key"
    AWS_IAM = "aws_iam"
    SERVICE_ACCOUNT = "service_account"
    BEARER = "bearer"
    NONE = "none"


class PluginConfig(BaseModel):
    """Configuration for a plugin with comprehensive metadata."""

    plugin_type: PluginType
    display_name: str
    description: str
    icon: str = "🔌"
    category: PluginCategory = PluginCategory.CUSTOM
    required_fields: list[str]
    optional_fields: list[str] = []
    auth_type: AuthType = AuthType.TOKEN
    endpoint_required: bool = True
    scopes_supported: list[str] = []

    # Help text for fields
    field_descriptions: dict[str, str] = {}
    field_examples: dict[str, str] = {}

    # Validation patterns (regex)
    field_patterns: dict[str, str] = {}

    # Default values
    field_defaults: dict[str, str] = {}

    # Sensitive fields (will be masked)
    sensitive_fields: list[str] = ["token", "password", "secret", "api_key"]

    # Documentation URL
    docs_url: str | None = None

    # Rate limits
    default_rate_limit: int = 0  # requests per hour, 0 = unlimited

    # Health check endpoint
    health_check_path: str | None = None

    # Whether this plugin is generally available
    is_beta: bool = False
    is_enterprise: bool = False


# =============================================================================
# COMPREHENSIVE PLUGIN CONFIGURATIONS - 25+ Data Sources
# =============================================================================

PLUGIN_CONFIGS: dict[str, PluginConfig] = {
    # =========================================================================
    # SOURCE CONTROL
    # =========================================================================
    "github": PluginConfig(
        plugin_type=PluginType.GITHUB,
        display_name="GitHub",
        description="Connect to GitHub repositories for commits, PRs, issues, and GitHub Actions",
        icon="🐙",
        category=PluginCategory.SOURCE_CONTROL,
        required_fields=["token"],
        optional_fields=["endpoint", "proxy", "rate_limit"],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["repo", "organization"],
        field_descriptions={
            "token": "Personal access token with repo, read:org, and workflow permissions",
            "endpoint": "API endpoint (for GitHub Enterprise Server)",
            "proxy": "HTTP proxy URL if needed",
            "rate_limit": "Custom rate limit (requests/hour)",
        },
        field_examples={
            "token": "ghp_example_token",
            "endpoint": "https://github.mycompany.com/api/v3",
            "proxy": "http://proxy.company.com:8080",
        },
        field_patterns={
            "token": r"^gh[ps]_[A-Za-z0-9_]{36,}$|^github_pat_[A-Za-z0-9_]{22,}$",
        },
        field_defaults={
            "endpoint": "https://api.github.com",
        },
        docs_url="https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token",
        default_rate_limit=5000,
        health_check_path="/rate_limit",
    ),
    "gitlab": PluginConfig(
        plugin_type=PluginType.GITLAB,
        display_name="GitLab",
        description="Connect to GitLab for repositories, merge requests, issues, and CI/CD pipelines",
        icon="🦊",
        category=PluginCategory.SOURCE_CONTROL,
        required_fields=["token", "endpoint"],
        optional_fields=["proxy"],
        auth_type=AuthType.TOKEN,
        scopes_supported=["project", "group"],
        field_descriptions={
            "token": "Personal access token with api, read_api, and read_repository scopes",
            "endpoint": "GitLab API endpoint URL",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "token": "glpat-xxxxxxxxxxxxxxxxxxxx",
            "endpoint": "https://gitlab.com/api/v4",
        },
        field_patterns={
            "token": r"^glpat-[A-Za-z0-9_-]{20,}$",
        },
        docs_url="https://docs.gitlab.com/ee/user/profile/personal_access_tokens.html",
        default_rate_limit=2000,
        health_check_path="/version",
    ),
    "bitbucket": PluginConfig(
        plugin_type=PluginType.BITBUCKET,
        display_name="Bitbucket Cloud",
        description="Connect to Bitbucket Cloud for repositories, pull requests, and pipelines",
        icon="🪣",
        category=PluginCategory.SOURCE_CONTROL,
        required_fields=["username", "app_password"],
        optional_fields=["workspace", "proxy"],
        auth_type=AuthType.BASIC,
        endpoint_required=False,
        scopes_supported=["repository", "workspace"],
        field_descriptions={
            "username": "Bitbucket username or email",
            "app_password": "App password (create in Personal Settings > App passwords)",
            "workspace": "Default workspace to use",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "username": "your-username",
            "app_password": "ATBBxxxxxxxxxxxxxxxx",
            "workspace": "myworkspace",
        },
        sensitive_fields=["app_password"],
        docs_url="https://support.atlassian.com/bitbucket-cloud/docs/app-passwords/",
        default_rate_limit=1000,
    ),
    "bitbucket_server": PluginConfig(
        plugin_type=PluginType.BITBUCKET_SERVER,
        display_name="Bitbucket Server/DC",
        description="Connect to Bitbucket Server or Data Center for repositories and pull requests",
        icon="🏢",
        category=PluginCategory.SOURCE_CONTROL,
        required_fields=["endpoint", "token"],
        optional_fields=["proxy"],
        auth_type=AuthType.TOKEN,
        scopes_supported=["repository", "project"],
        field_descriptions={
            "endpoint": "Bitbucket Server URL",
            "token": "HTTP access token",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "endpoint": "https://bitbucket.company.com",
            "token": "MDxxxxxxxxxxxxxx",
        },
        docs_url="https://confluence.atlassian.com/bitbucketserver/personal-access-tokens-939515499.html",
    ),
    "gitee": PluginConfig(
        plugin_type=PluginType.GITEE,
        display_name="Gitee",
        description="Connect to Gitee (码云) for repositories, pull requests, and issues",
        icon="🇨🇳",
        category=PluginCategory.SOURCE_CONTROL,
        required_fields=["token"],
        optional_fields=["proxy"],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["repo", "organization"],
        field_descriptions={
            "token": "Personal access token with projects and pull_requests scopes",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        },
        field_defaults={
            "endpoint": "https://gitee.com/api/v5",
        },
        docs_url="https://gitee.com/profile/personal_access_tokens",
    ),
    "gitea": PluginConfig(
        plugin_type=PluginType.GITEA,
        display_name="Gitea",
        description="Connect to Gitea for self-hosted Git repositories",
        icon="☕",
        category=PluginCategory.SOURCE_CONTROL,
        required_fields=["endpoint", "token"],
        optional_fields=["proxy"],
        auth_type=AuthType.TOKEN,
        scopes_supported=["repo", "organization"],
        field_descriptions={
            "endpoint": "Gitea server URL",
            "token": "Access token with read:org and repo scopes",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "endpoint": "https://gitea.company.com",
            "token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        },
        docs_url="https://docs.gitea.io/en-us/api-usage/",
    ),
    "azure_repos": PluginConfig(
        plugin_type=PluginType.AZURE_REPOS,
        display_name="Azure Repos",
        description="Connect to Azure Repos for Git repositories and pull requests",
        icon="📘",
        category=PluginCategory.SOURCE_CONTROL,
        required_fields=["organization", "token"],
        optional_fields=["project", "proxy"],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["repository", "project"],
        field_descriptions={
            "organization": "Azure DevOps organization name",
            "token": "Personal access token with Code (Read) scope",
            "project": "Default project name",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "organization": "myorg",
            "token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "project": "MyProject",
        },
        docs_url="https://docs.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate",
    ),

    # =========================================================================
    # ISSUE TRACKING
    # =========================================================================
    "jira": PluginConfig(
        plugin_type=PluginType.JIRA,
        display_name="Jira Cloud",
        description="Connect to Jira Cloud for issues, sprints, boards, and project tracking",
        icon="📋",
        category=PluginCategory.ISSUE_TRACKING,
        required_fields=["endpoint", "email", "token"],
        optional_fields=["proxy"],
        auth_type=AuthType.BASIC,
        scopes_supported=["project", "board"],
        field_descriptions={
            "endpoint": "Jira Cloud instance URL (yoursite.atlassian.net)",
            "email": "Your Atlassian account email",
            "token": "API token (create at id.atlassian.com/manage-profile/security/api-tokens)",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "endpoint": "https://yourcompany.atlassian.net",
            "email": "user@company.com",
            "token": "ATATT3xFfGF0xxxxxxxxxxxx",
        },
        field_patterns={
            "endpoint": r"^https://[a-zA-Z0-9-]+\.atlassian\.net/?$",
            "email": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
        },
        docs_url="https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/",
        default_rate_limit=100,
    ),
    "jira_server": PluginConfig(
        plugin_type=PluginType.JIRA_SERVER,
        display_name="Jira Server/DC",
        description="Connect to Jira Server or Data Center for on-premise Jira instances",
        icon="🏢",
        category=PluginCategory.ISSUE_TRACKING,
        required_fields=["endpoint", "username", "password"],
        optional_fields=["proxy"],
        auth_type=AuthType.BASIC,
        scopes_supported=["project", "board"],
        field_descriptions={
            "endpoint": "Jira Server URL",
            "username": "Jira username",
            "password": "Jira password or personal access token",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "endpoint": "https://jira.company.com",
            "username": "admin",
        },
        sensitive_fields=["password"],
    ),
    "linear": PluginConfig(
        plugin_type=PluginType.LINEAR,
        display_name="Linear",
        description="Connect to Linear for modern issue tracking and project management",
        icon="📐",
        category=PluginCategory.ISSUE_TRACKING,
        required_fields=["api_key"],
        optional_fields=[],
        auth_type=AuthType.API_KEY,
        endpoint_required=False,
        scopes_supported=["team", "project"],
        field_descriptions={
            "api_key": "Linear API key (create in Settings > API)",
        },
        field_examples={
            "api_key": "lin_api_xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        },
        field_patterns={
            "api_key": r"^lin_api_[A-Za-z0-9]{32,}$",
        },
        field_defaults={
            "endpoint": "https://api.linear.app/graphql",
        },
        docs_url="https://developers.linear.app/docs/graphql/working-with-the-graphql-api",
        is_beta=True,
    ),
    "asana": PluginConfig(
        plugin_type=PluginType.ASANA,
        display_name="Asana",
        description="Connect to Asana for tasks, projects, and workspaces",
        icon="🎯",
        category=PluginCategory.ISSUE_TRACKING,
        required_fields=["token"],
        optional_fields=["workspace"],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["workspace", "project"],
        field_descriptions={
            "token": "Personal access token (create in My Settings > Apps > Personal access tokens)",
            "workspace": "Default workspace GID",
        },
        field_examples={
            "token": "1/1234567890123456:xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "workspace": "1234567890123456",
        },
        docs_url="https://developers.asana.com/docs/personal-access-token",
        is_beta=True,
    ),
    "trello": PluginConfig(
        plugin_type=PluginType.TRELLO,
        display_name="Trello",
        description="Connect to Trello for boards, lists, and cards",
        icon="📌",
        category=PluginCategory.ISSUE_TRACKING,
        required_fields=["api_key", "token"],
        optional_fields=[],
        auth_type=AuthType.API_KEY,
        endpoint_required=False,
        scopes_supported=["board", "organization"],
        field_descriptions={
            "api_key": "Trello API key (get at trello.com/app-key)",
            "token": "Trello token (authorize at trello.com/app-key)",
        },
        field_examples={
            "api_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        },
        docs_url="https://developer.atlassian.com/cloud/trello/guides/rest-api/api-introduction/",
    ),
    "clickup": PluginConfig(
        plugin_type=PluginType.CLICKUP,
        display_name="ClickUp",
        description="Connect to ClickUp for tasks, spaces, and time tracking",
        icon="✅",
        category=PluginCategory.ISSUE_TRACKING,
        required_fields=["token"],
        optional_fields=["team_id"],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["team", "space", "folder"],
        field_descriptions={
            "token": "Personal API token (Settings > Apps > API Token)",
            "team_id": "Default team ID",
        },
        field_examples={
            "token": "pk_xxxxxxxx_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "team_id": "1234567",
        },
        docs_url="https://clickup.com/api",
        is_beta=True,
    ),
    "monday": PluginConfig(
        plugin_type=PluginType.MONDAY,
        display_name="Monday.com",
        description="Connect to Monday.com for work management and boards",
        icon="📊",
        category=PluginCategory.PROJECT_MANAGEMENT,
        required_fields=["token"],
        optional_fields=[],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["board", "workspace"],
        field_descriptions={
            "token": "API token (Admin > Integrations > API)",
        },
        field_examples={
            "token": "eyJhbGciOiJIUzI1NiJ9.xxxxxxxxxxxx",
        },
        docs_url="https://developer.monday.com/apps/docs/manage",
        is_beta=True,
    ),
    "youtrack": PluginConfig(
        plugin_type=PluginType.YOUTRACK,
        display_name="YouTrack",
        description="Connect to JetBrains YouTrack for issue tracking",
        icon="🎫",
        category=PluginCategory.ISSUE_TRACKING,
        required_fields=["endpoint", "token"],
        optional_fields=["proxy"],
        auth_type=AuthType.TOKEN,
        scopes_supported=["project"],
        field_descriptions={
            "endpoint": "YouTrack server URL",
            "token": "Permanent token (Profile > Authentication > Tokens)",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "endpoint": "https://youtrack.company.com",
            "token": "perm:xxxxxxxxxxxxxxxx",
        },
        docs_url="https://www.jetbrains.com/help/youtrack/devportal/Manage-Permanent-Tokens.html",
        is_beta=True,
    ),
    "shortcut": PluginConfig(
        plugin_type=PluginType.SHORTCUT,
        display_name="Shortcut (Clubhouse)",
        description="Connect to Shortcut for collaborative project management",
        icon="🏃",
        category=PluginCategory.ISSUE_TRACKING,
        required_fields=["token"],
        optional_fields=[],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["workspace", "project"],
        field_descriptions={
            "token": "API token (Settings > API Tokens)",
        },
        field_examples={
            "token": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        },
        docs_url="https://developer.shortcut.com/api/rest/v3",
        is_beta=True,
    ),
    "tapd": PluginConfig(
        plugin_type=PluginType.TAPD,
        display_name="TAPD",
        description="Connect to Tencent TAPD for agile project management (腾讯敏捷协作)",
        icon="🐧",
        category=PluginCategory.ISSUE_TRACKING,
        required_fields=["api_user", "api_password"],
        optional_fields=["company_id"],
        auth_type=AuthType.BASIC,
        endpoint_required=False,
        scopes_supported=["workspace", "project"],
        field_descriptions={
            "api_user": "TAPD API User",
            "api_password": "TAPD API Password",
            "company_id": "Company ID",
        },
        sensitive_fields=["api_password"],
        docs_url="https://www.tapd.cn/help/view#1120003271001002313",
    ),
    "zentao": PluginConfig(
        plugin_type=PluginType.ZENTAO,
        display_name="ZenTao",
        description="Connect to ZenTao (禅道) for project management",
        icon="🧘",
        category=PluginCategory.ISSUE_TRACKING,
        required_fields=["endpoint", "username", "password"],
        optional_fields=["proxy"],
        auth_type=AuthType.BASIC,
        scopes_supported=["product", "project"],
        field_descriptions={
            "endpoint": "ZenTao server URL",
            "username": "ZenTao username",
            "password": "ZenTao password",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "endpoint": "https://zentao.company.com",
        },
        sensitive_fields=["password"],
    ),

    # =========================================================================
    # CI/CD
    # =========================================================================
    "jenkins": PluginConfig(
        plugin_type=PluginType.JENKINS,
        display_name="Jenkins",
        description="Connect to Jenkins for build jobs, pipelines, and deployment data",
        icon="🔧",
        category=PluginCategory.CI_CD,
        required_fields=["endpoint", "username", "token"],
        optional_fields=["proxy"],
        auth_type=AuthType.BASIC,
        scopes_supported=["job", "folder", "multibranch"],
        field_descriptions={
            "endpoint": "Jenkins server URL",
            "username": "Jenkins username",
            "token": "API token (User > Configure > API Token)",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "endpoint": "https://jenkins.company.com",
            "username": "admin",
            "token": "11xxxxxxxxxxxxxxxxxxxxxxxxxx",
        },
        docs_url="https://www.jenkins.io/doc/book/system-administration/authenticating-scripted-clients/",
        health_check_path="/api/json",
    ),
    "github_actions": PluginConfig(
        plugin_type=PluginType.GITHUB_ACTIONS,
        display_name="GitHub Actions",
        description="Connect to GitHub Actions for workflow runs and CI/CD data",
        icon="⚡",
        category=PluginCategory.CI_CD,
        required_fields=["token"],
        optional_fields=["endpoint", "proxy"],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["repo", "organization"],
        field_descriptions={
            "token": "GitHub token with workflow scope",
            "endpoint": "API endpoint (for GitHub Enterprise)",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "token": "ghp_example_token",
        },
        field_patterns={
            "token": r"^gh[ps]_[A-Za-z0-9_]{36,}$|^github_pat_[A-Za-z0-9_]{22,}$",
        },
        docs_url="https://docs.github.com/en/actions",
    ),
    "gitlab_ci": PluginConfig(
        plugin_type=PluginType.GITLAB_CI,
        display_name="GitLab CI/CD",
        description="Connect to GitLab CI/CD for pipeline jobs and deployments",
        icon="🔶",
        category=PluginCategory.CI_CD,
        required_fields=["token", "endpoint"],
        optional_fields=["proxy"],
        auth_type=AuthType.TOKEN,
        scopes_supported=["project", "group"],
        field_descriptions={
            "token": "Personal access token with read_api scope",
            "endpoint": "GitLab API endpoint URL",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "token": "glpat-xxxxxxxxxxxxxxxxxxxx",
            "endpoint": "https://gitlab.com/api/v4",
        },
        docs_url="https://docs.gitlab.com/ee/ci/",
    ),
    "azuredevops": PluginConfig(
        plugin_type=PluginType.AZURE_DEVOPS,
        display_name="Azure DevOps",
        description="Connect to Azure DevOps for repos, boards, pipelines, and artifacts",
        icon="☁️",
        category=PluginCategory.CI_CD,
        required_fields=["organization", "token"],
        optional_fields=["project", "proxy"],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["project", "repository", "pipeline"],
        field_descriptions={
            "organization": "Azure DevOps organization name",
            "token": "Personal access token (full access or custom scopes)",
            "project": "Default project name",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "organization": "myorg",
            "token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "project": "MyProject",
        },
        docs_url="https://docs.microsoft.com/en-us/azure/devops/organizations/accounts/use-personal-access-tokens-to-authenticate",
        default_rate_limit=200,
    ),
    "circleci": PluginConfig(
        plugin_type=PluginType.CIRCLECI,
        display_name="CircleCI",
        description="Connect to CircleCI for build pipelines and workflows",
        icon="⭕",
        category=PluginCategory.CI_CD,
        required_fields=["token"],
        optional_fields=["organization"],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["project", "workflow"],
        field_descriptions={
            "token": "Personal API token (User Settings > Personal API Tokens)",
            "organization": "Organization slug (e.g., github/myorg)",
        },
        field_examples={
            "token": "CCIPAT_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "organization": "github/myorg",
        },
        field_defaults={
            "endpoint": "https://circleci.com/api/v2",
        },
        docs_url="https://circleci.com/docs/api-intro/",
    ),
    "travis_ci": PluginConfig(
        plugin_type=PluginType.TRAVIS_CI,
        display_name="Travis CI",
        description="Connect to Travis CI for build data",
        icon="🏗️",
        category=PluginCategory.CI_CD,
        required_fields=["token"],
        optional_fields=["endpoint"],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["repository"],
        field_descriptions={
            "token": "API token (Settings > Settings)",
            "endpoint": "API endpoint (travis-ci.com or travis-ci.org)",
        },
        field_examples={
            "token": "xxxxxxxxxxxxxxxxxxxxxxx",
        },
        field_defaults={
            "endpoint": "https://api.travis-ci.com",
        },
        docs_url="https://docs.travis-ci.com/user/developer/",
    ),
    "bamboo": PluginConfig(
        plugin_type=PluginType.BAMBOO,
        display_name="Bamboo",
        description="Connect to Atlassian Bamboo for build and deployment data",
        icon="🎋",
        category=PluginCategory.CI_CD,
        required_fields=["endpoint", "token"],
        optional_fields=["proxy"],
        auth_type=AuthType.TOKEN,
        scopes_supported=["project", "plan"],
        field_descriptions={
            "endpoint": "Bamboo server URL",
            "token": "Personal access token",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "endpoint": "https://bamboo.company.com",
            "token": "xxxxxxxxxxxxxxxxxxxx",
        },
        docs_url="https://confluence.atlassian.com/bamboo/bamboo-rest-apis-289276893.html",
    ),
    "teamcity": PluginConfig(
        plugin_type=PluginType.TEAMCITY,
        display_name="TeamCity",
        description="Connect to JetBrains TeamCity for builds and deployments",
        icon="🏢",
        category=PluginCategory.CI_CD,
        required_fields=["endpoint", "token"],
        optional_fields=["proxy"],
        auth_type=AuthType.TOKEN,
        scopes_supported=["project", "build_config"],
        field_descriptions={
            "endpoint": "TeamCity server URL",
            "token": "Access token (Profile > Access Tokens)",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "endpoint": "https://teamcity.company.com",
            "token": "eyJ0eXAiOiJKV1QiLCJhbGciOiJS...",
        },
        docs_url="https://www.jetbrains.com/help/teamcity/rest/teamcity-rest-api-documentation.html",
        is_beta=True,
    ),
    "drone": PluginConfig(
        plugin_type=PluginType.DRONE,
        display_name="Drone CI",
        description="Connect to Drone CI for container-native CI/CD",
        icon="🚁",
        category=PluginCategory.CI_CD,
        required_fields=["endpoint", "token"],
        optional_fields=["proxy"],
        auth_type=AuthType.TOKEN,
        scopes_supported=["repo"],
        field_descriptions={
            "endpoint": "Drone server URL",
            "token": "Personal token (Account Settings)",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "endpoint": "https://drone.company.com",
            "token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        },
        docs_url="https://docs.drone.io/api/overview/",
        is_beta=True,
    ),
    "buildkite": PluginConfig(
        plugin_type=PluginType.BUILDKITE,
        display_name="Buildkite",
        description="Connect to Buildkite for hybrid CI/CD pipelines",
        icon="🏃",
        category=PluginCategory.CI_CD,
        required_fields=["token", "organization"],
        optional_fields=[],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["pipeline"],
        field_descriptions={
            "token": "API Access Token (Personal Settings > API Access Tokens)",
            "organization": "Organization slug",
        },
        field_examples={
            "token": "bkua_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "organization": "my-org",
        },
        docs_url="https://buildkite.com/docs/apis/rest-api",
        is_beta=True,
    ),
    "argocd": PluginConfig(
        plugin_type=PluginType.ARGO_CD,
        display_name="Argo CD",
        description="Connect to Argo CD for GitOps deployments",
        icon="🐙",
        category=PluginCategory.CI_CD,
        required_fields=["endpoint", "token"],
        optional_fields=["proxy", "insecure"],
        auth_type=AuthType.TOKEN,
        scopes_supported=["application", "project"],
        field_descriptions={
            "endpoint": "Argo CD server URL",
            "token": "API token (Settings > Accounts > Generate New)",
            "proxy": "HTTP proxy URL if needed",
            "insecure": "Skip TLS verification (not recommended)",
        },
        field_examples={
            "endpoint": "https://argocd.company.com",
            "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
        },
        docs_url="https://argo-cd.readthedocs.io/en/stable/developer-guide/api-docs/",
        is_beta=True,
    ),

    # =========================================================================
    # CODE QUALITY & SECURITY
    # =========================================================================
    "sonarqube": PluginConfig(
        plugin_type=PluginType.SONARQUBE,
        display_name="SonarQube",
        description="Connect to SonarQube for code quality and security analysis",
        icon="🔍",
        category=PluginCategory.CODE_QUALITY,
        required_fields=["endpoint", "token"],
        optional_fields=["proxy"],
        auth_type=AuthType.TOKEN,
        scopes_supported=["project"],
        field_descriptions={
            "endpoint": "SonarQube server URL",
            "token": "User token (My Account > Security > Tokens)",
            "proxy": "HTTP proxy URL if needed",
        },
        field_examples={
            "endpoint": "https://sonarqube.company.com",
            "token": "sqp_xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        },
        field_patterns={
            "token": r"^(sqp_|squ_)?[a-f0-9]{40}$",
        },
        docs_url="https://docs.sonarqube.org/latest/user-guide/user-token/",
        health_check_path="/api/system/status",
    ),
    "sonarcloud": PluginConfig(
        plugin_type=PluginType.SONARCLOUD,
        display_name="SonarCloud",
        description="Connect to SonarCloud for cloud-based code analysis",
        icon="☁️",
        category=PluginCategory.CODE_QUALITY,
        required_fields=["token", "organization"],
        optional_fields=[],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["project"],
        field_descriptions={
            "token": "User token (My Account > Security)",
            "organization": "Organization key",
        },
        field_examples={
            "token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "organization": "my-org",
        },
        field_defaults={
            "endpoint": "https://sonarcloud.io/api",
        },
        docs_url="https://docs.sonarcloud.io/advanced-setup/user-token/",
    ),
    "codecov": PluginConfig(
        plugin_type=PluginType.CODECOV,
        display_name="Codecov",
        description="Connect to Codecov for code coverage reports",
        icon="📊",
        category=PluginCategory.CODE_QUALITY,
        required_fields=["token"],
        optional_fields=["owner"],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["repo"],
        field_descriptions={
            "token": "Global token or repository token",
            "owner": "Organization/user name",
        },
        field_examples={
            "token": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "owner": "myorg",
        },
        docs_url="https://docs.codecov.com/reference/overview",
        is_beta=True,
    ),
    "snyk": PluginConfig(
        plugin_type=PluginType.SNYK,
        display_name="Snyk",
        description="Connect to Snyk for vulnerability scanning and security",
        icon="🛡️",
        category=PluginCategory.SECURITY,
        required_fields=["token", "organization"],
        optional_fields=[],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["organization", "project"],
        field_descriptions={
            "token": "API token (Account Settings > API Token)",
            "organization": "Organization ID or slug",
        },
        field_examples={
            "token": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "organization": "org-id-here",
        },
        field_defaults={
            "endpoint": "https://api.snyk.io/v1",
        },
        docs_url="https://docs.snyk.io/snyk-api-info",
        is_beta=True,
    ),
    "codeclimate": PluginConfig(
        plugin_type=PluginType.CODECLIMATE,
        display_name="Code Climate",
        description="Connect to Code Climate for code quality and maintainability",
        icon="🌡️",
        category=PluginCategory.CODE_QUALITY,
        required_fields=["token"],
        optional_fields=["organization"],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["repo"],
        field_descriptions={
            "token": "Personal access token",
            "organization": "Organization name",
        },
        field_examples={
            "token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        },
        docs_url="https://developer.codeclimate.com/",
        is_beta=True,
    ),

    # =========================================================================
    # INCIDENT MANAGEMENT
    # =========================================================================
    "pagerduty": PluginConfig(
        plugin_type=PluginType.PAGERDUTY,
        display_name="PagerDuty",
        description="Connect to PagerDuty for incidents, on-call schedules, and MTTR",
        icon="🚨",
        category=PluginCategory.INCIDENT_MANAGEMENT,
        required_fields=["token"],
        optional_fields=[],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["service", "team"],
        field_descriptions={
            "token": "REST API Key (Integrations > API Access Keys)",
        },
        field_examples={
            "token": "u+xxxxxxxxxxxxxxxxxxxx",
        },
        field_patterns={
            "token": r"^u\+[A-Za-z0-9_-]{20,}$",
        },
        field_defaults={
            "endpoint": "https://api.pagerduty.com",
        },
        docs_url="https://developer.pagerduty.com/api-reference/",
        default_rate_limit=960,
    ),
    "opsgenie": PluginConfig(
        plugin_type=PluginType.OPSGENIE,
        display_name="Opsgenie",
        description="Connect to Opsgenie for alerts and incident management",
        icon="🔔",
        category=PluginCategory.INCIDENT_MANAGEMENT,
        required_fields=["token"],
        optional_fields=["endpoint"],
        auth_type=AuthType.API_KEY,
        endpoint_required=False,
        scopes_supported=["team", "service"],
        field_descriptions={
            "token": "API key (Settings > Integrations > API)",
            "endpoint": "API endpoint (US or EU)",
        },
        field_examples={
            "token": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        },
        field_defaults={
            "endpoint": "https://api.opsgenie.com/v2",
        },
        docs_url="https://docs.opsgenie.com/docs/api-overview",
    ),
    "statuspage": PluginConfig(
        plugin_type=PluginType.STATUSPAGE,
        display_name="Statuspage",
        description="Connect to Atlassian Statuspage for incident communication",
        icon="📢",
        category=PluginCategory.INCIDENT_MANAGEMENT,
        required_fields=["token", "page_id"],
        optional_fields=[],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["page", "component"],
        field_descriptions={
            "token": "API key (Manage Page > API)",
            "page_id": "Page ID",
        },
        field_examples={
            "token": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "page_id": "xxxxxxxxxx",
        },
        field_defaults={
            "endpoint": "https://api.statuspage.io/v1",
        },
        docs_url="https://developer.statuspage.io/",
        is_beta=True,
    ),
    "firehydrant": PluginConfig(
        plugin_type=PluginType.FIREHYDRANT,
        display_name="FireHydrant",
        description="Connect to FireHydrant for incident management and reliability",
        icon="🔥",
        category=PluginCategory.INCIDENT_MANAGEMENT,
        required_fields=["token"],
        optional_fields=[],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["service", "team"],
        field_descriptions={
            "token": "API token (Settings > API Tokens)",
        },
        field_examples={
            "token": "fh_xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        },
        field_defaults={
            "endpoint": "https://api.firehydrant.io/v1",
        },
        docs_url="https://firehydrant.com/docs/api/",
        is_beta=True,
    ),
    "rootly": PluginConfig(
        plugin_type=PluginType.ROOTLY,
        display_name="Rootly",
        description="Connect to Rootly for incident response automation",
        icon="🌱",
        category=PluginCategory.INCIDENT_MANAGEMENT,
        required_fields=["token"],
        optional_fields=[],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["team", "service"],
        field_descriptions={
            "token": "API key (Settings > API Keys)",
        },
        field_examples={
            "token": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        },
        field_defaults={
            "endpoint": "https://api.rootly.com/v1",
        },
        docs_url="https://rootly.com/docs/api",
        is_beta=True,
    ),

    # =========================================================================
    # COMMUNICATION
    # =========================================================================
    "slack": PluginConfig(
        plugin_type=PluginType.SLACK,
        display_name="Slack",
        description="Connect to Slack for team communication metrics",
        icon="💬",
        category=PluginCategory.COMMUNICATION,
        required_fields=["token"],
        optional_fields=["team_id"],
        auth_type=AuthType.TOKEN,
        endpoint_required=False,
        scopes_supported=["channel", "workspace"],
        field_descriptions={
            "token": "Bot User OAuth Token (xoxb-...)",
            "team_id": "Workspace/Team ID",
        },
        field_examples={
            "token": "xoxb-example-token",
            "team_id": "T12345678",
        },
        field_patterns={
            "token": r"^xoxb-[0-9]+-[0-9]+-[A-Za-z0-9]+$",
        },
        docs_url="https://api.slack.com/authentication/token-types#bot",
        is_beta=True,
    ),
    "feishu": PluginConfig(
        plugin_type=PluginType.FEISHU,
        display_name="Feishu/Lark",
        description="Connect to Feishu (飞书) or Lark for communication and collaboration",
        icon="🐦",
        category=PluginCategory.COMMUNICATION,
        required_fields=["app_id", "app_secret"],
        optional_fields=["endpoint"],
        auth_type=AuthType.API_KEY,
        endpoint_required=False,
        scopes_supported=["chat", "department"],
        field_descriptions={
            "app_id": "App ID from developer console",
            "app_secret": "App Secret from developer console",
            "endpoint": "API endpoint (feishu.cn or larksuite.com)",
        },
        field_examples={
            "app_id": "cli_xxxxxxxxxxxxxxxxxx",
            "app_secret": "xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        },
        field_defaults={
            "endpoint": "https://open.feishu.cn/open-apis",
        },
        sensitive_fields=["app_secret"],
        docs_url="https://open.feishu.cn/document/",
    ),
    "msteams": PluginConfig(
        plugin_type=PluginType.MSTEAMS,
        display_name="Microsoft Teams",
        description="Connect to Microsoft Teams for collaboration metrics",
        icon="👥",
        category=PluginCategory.COMMUNICATION,
        required_fields=["tenant_id", "client_id", "client_secret"],
        optional_fields=[],
        auth_type=AuthType.OAUTH,
        endpoint_required=False,
        scopes_supported=["team", "channel"],
        field_descriptions={
            "tenant_id": "Azure AD Tenant ID",
            "client_id": "App Registration Client ID",
            "client_secret": "App Registration Client Secret",
        },
        field_examples={
            "tenant_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
            "client_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        },
        sensitive_fields=["client_secret"],
        docs_url="https://docs.microsoft.com/en-us/graph/api/overview",
        is_beta=True,
        is_enterprise=True,
    ),

    # =========================================================================
    # MONITORING & OBSERVABILITY
    # =========================================================================
    "datadog": PluginConfig(
        plugin_type=PluginType.DATADOG,
        display_name="Datadog",
        description="Connect to Datadog for monitoring and observability metrics",
        icon="🐕",
        category=PluginCategory.MONITORING,
        required_fields=["api_key", "app_key"],
        optional_fields=["site"],
        auth_type=AuthType.API_KEY,
        endpoint_required=False,
        scopes_supported=["monitor", "dashboard"],
        field_descriptions={
            "api_key": "Datadog API Key",
            "app_key": "Datadog Application Key",
            "site": "Datadog site (us1, eu1, us3, us5, etc.)",
        },
        field_examples={
            "api_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "app_key": "xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
            "site": "us1",
        },
        sensitive_fields=["api_key", "app_key"],
        field_defaults={
            "site": "us1",
        },
        docs_url="https://docs.datadoghq.com/api/",
        is_beta=True,
    ),
    "newrelic": PluginConfig(
        plugin_type=PluginType.NEWRELIC,
        display_name="New Relic",
        description="Connect to New Relic for APM and observability",
        icon="📈",
        category=PluginCategory.MONITORING,
        required_fields=["api_key", "account_id"],
        optional_fields=["region"],
        auth_type=AuthType.API_KEY,
        endpoint_required=False,
        scopes_supported=["application", "service"],
        field_descriptions={
            "api_key": "User API Key (not Ingest key)",
            "account_id": "New Relic Account ID",
            "region": "Data center region (US or EU)",
        },
        field_examples={
            "api_key": "NRAK-XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX",
            "account_id": "1234567",
            "region": "US",
        },
        field_patterns={
            "api_key": r"^NRAK-[A-Z0-9]{32,}$",
        },
        docs_url="https://docs.newrelic.com/docs/apis/rest-api-v2/",
        is_beta=True,
    ),
    "prometheus": PluginConfig(
        plugin_type=PluginType.PROMETHEUS,
        display_name="Prometheus",
        description="Connect to Prometheus for metrics collection",
        icon="🔥",
        category=PluginCategory.MONITORING,
        required_fields=["endpoint"],
        optional_fields=["username", "password", "bearer_token"],
        auth_type=AuthType.BASIC,
        scopes_supported=["metric"],
        field_descriptions={
            "endpoint": "Prometheus server URL",
            "username": "Basic auth username (optional)",
            "password": "Basic auth password (optional)",
            "bearer_token": "Bearer token for authentication",
        },
        field_examples={
            "endpoint": "https://prometheus.company.com",
        },
        sensitive_fields=["password", "bearer_token"],
        health_check_path="/-/healthy",
        is_beta=True,
    ),
    "grafana": PluginConfig(
        plugin_type=PluginType.GRAFANA,
        display_name="Grafana",
        description="Connect to Grafana for dashboard and annotation data",
        icon="📊",
        category=PluginCategory.MONITORING,
        required_fields=["endpoint", "token"],
        optional_fields=["org_id"],
        auth_type=AuthType.TOKEN,
        scopes_supported=["dashboard", "folder"],
        field_descriptions={
            "endpoint": "Grafana server URL",
            "token": "Service Account token or API key",
            "org_id": "Organization ID (for multi-org)",
        },
        field_examples={
            "endpoint": "https://grafana.company.com",
            "token": "glsa_xxxxxxxxxxxxxxxxxxxxxxxxxxxx",
        },
        docs_url="https://grafana.com/docs/grafana/latest/developers/http_api/",
        health_check_path="/api/health",
        is_beta=True,
    ),

    # =========================================================================
    # CLOUD PROVIDERS
    # =========================================================================
    "aws": PluginConfig(
        plugin_type=PluginType.AWS,
        display_name="Amazon Web Services",
        description="Connect to AWS for cloud resource and deployment metrics",
        icon="☁️",
        category=PluginCategory.CLOUD_PROVIDER,
        required_fields=["access_key_id", "secret_access_key"],
        optional_fields=["region", "role_arn"],
        auth_type=AuthType.AWS_IAM,
        endpoint_required=False,
        scopes_supported=["region", "service"],
        field_descriptions={
            "access_key_id": "AWS Access Key ID",
            "secret_access_key": "AWS Secret Access Key",
            "region": "Default AWS region",
            "role_arn": "IAM Role ARN to assume (optional)",
        },
        field_examples={
            "access_key_id": "AKIAIOSFODNN7EXAMPLE",
            "secret_access_key": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
            "region": "us-east-1",
        },
        field_patterns={
            "access_key_id": r"^AKIA[A-Z0-9]{16}$",
        },
        sensitive_fields=["secret_access_key"],
        docs_url="https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_access-keys.html",
        is_beta=True,
        is_enterprise=True,
    ),
    "kubernetes": PluginConfig(
        plugin_type=PluginType.KUBERNETES,
        display_name="Kubernetes",
        description="Connect to Kubernetes clusters for deployment and resource metrics",
        icon="☸️",
        category=PluginCategory.CLOUD_PROVIDER,
        required_fields=["endpoint", "token"],
        optional_fields=["ca_cert", "namespace", "insecure"],
        auth_type=AuthType.TOKEN,
        scopes_supported=["namespace", "deployment"],
        field_descriptions={
            "endpoint": "Kubernetes API server URL",
            "token": "Service account token or kubeconfig token",
            "ca_cert": "CA certificate (base64 encoded)",
            "namespace": "Default namespace",
            "insecure": "Skip TLS verification (not recommended)",
        },
        field_examples={
            "endpoint": "https://kubernetes.company.com:6443",
            "namespace": "default",
        },
        docs_url="https://kubernetes.io/docs/reference/generated/kubernetes-api/v1.27/",
        is_beta=True,
        is_enterprise=True,
    ),

    # =========================================================================
    # CUSTOM / WEBHOOK
    # =========================================================================
    "webhook": PluginConfig(
        plugin_type=PluginType.WEBHOOK,
        display_name="Custom Webhook",
        description="Configure incoming webhooks for custom data sources",
        icon="🔗",
        category=PluginCategory.CUSTOM,
        required_fields=["name"],
        optional_fields=["secret", "allowed_ips"],
        auth_type=AuthType.NONE,
        endpoint_required=False,
        scopes_supported=[],
        field_descriptions={
            "name": "Webhook name (used in URL)",
            "secret": "Shared secret for signature verification",
            "allowed_ips": "Comma-separated list of allowed IP addresses",
        },
        field_examples={
            "name": "my-custom-source",
            "secret": "my-webhook-secret",
            "allowed_ips": "192.168.1.0/24,10.0.0.1",
        },
        sensitive_fields=["secret"],
        docs_url="https://devlake.apache.org/docs/Plugins/webhook/",
    ),
    "restapi": PluginConfig(
        plugin_type=PluginType.REST_API,
        display_name="REST API",
        description="Connect to any REST API with custom configuration",
        icon="🌐",
        category=PluginCategory.CUSTOM,
        required_fields=["endpoint", "name"],
        optional_fields=["auth_header", "auth_value", "headers"],
        auth_type=AuthType.BEARER,
        scopes_supported=[],
        field_descriptions={
            "endpoint": "Base API URL",
            "name": "Connection name",
            "auth_header": "Authentication header name",
            "auth_value": "Authentication header value",
            "headers": "Additional headers (JSON object)",
        },
        field_examples={
            "endpoint": "https://api.example.com/v1",
            "name": "custom-api",
            "auth_header": "Authorization",
            "auth_value": "Bearer xxx",
        },
        sensitive_fields=["auth_value"],
        is_beta=True,
    ),
}


# =============================================================================
# SECURITY MODELS
# =============================================================================

class SensitiveString(str):
    """String that masks its value when displayed."""

    def __repr__(self) -> str:
        if len(self) <= 8:
            return "'****'"
        return f"'{self[:4]}...{self[-4:]}'"

    def __str__(self) -> str:
        return super().__str__()

    @classmethod
    def mask(cls, value: str) -> str:
        """Return masked version of value."""
        if not value:
            return ""
        if len(value) <= 8:
            return "****"
        return f"{value[:4]}{'*' * (len(value) - 8)}{value[-4:]}"


class ConnectionConfig(BaseModel):
    """Configuration for creating a connection with validation."""

    plugin: str
    name: str
    endpoint: str | None = None
    token: str | None = None
    username: str | None = None
    email: str | None = None
    password: str | None = None
    organization: str | None = None
    proxy: str | None = None
    api_key: str | None = None
    app_password: str | None = None
    app_id: str | None = None
    app_secret: str | None = None
    access_key_id: str | None = None
    secret_access_key: str | None = None
    client_id: str | None = None
    client_secret: str | None = None
    tenant_id: str | None = None

    # Additional fields as key-value pairs
    extra_config: dict[str, Any] = {}

    @field_validator('name')
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Validate connection name."""
        if not v or len(v.strip()) < 2:
            raise ValueError("Name must be at least 2 characters")
        if len(v) > 100:
            raise ValueError("Name must be less than 100 characters")
        # Sanitize name
        return v.strip()

    @field_validator('endpoint')
    @classmethod
    def validate_endpoint(cls, v: str | None) -> str | None:
        """Validate endpoint URL."""
        if v is None:
            return None
        if not v.startswith(('http://', 'https://')):
            raise ValueError("Endpoint must be a valid HTTP(S) URL")
        # Strip trailing slash
        return v.rstrip('/')

    @field_validator('email')
    @classmethod
    def validate_email(cls, v: str | None) -> str | None:
        """Validate email format."""
        if v is None:
            return None
        email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_pattern, v):
            raise ValueError("Invalid email format")
        return v.lower()

    def get_masked_config(self) -> dict[str, Any]:
        """Return config with sensitive fields masked."""
        result = self.model_dump()
        sensitive = ['token', 'password', 'api_key', 'app_password', 'app_secret',
                     'secret_access_key', 'client_secret']
        for field in sensitive:
            if result.get(field):
                result[field] = SensitiveString.mask(result[field])
        return result


class SetupAction(BaseModel):
    """An action to be performed by the chatbot."""

    action_type: ActionType
    label: str
    description: str | None = None
    data: dict[str, Any] = {}
    requires_confirmation: bool = False
    is_destructive: bool = False


class QuickReply(BaseModel):
    """Quick reply option for user to select."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    label: str
    value: str
    icon: str | None = None
    description: str | None = None
    action: SetupAction | None = None


class ChatMessage(BaseModel):
    """A message in the setup conversation."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    role: str  # "user", "assistant", "system"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

    # Rich content
    quick_replies: list[QuickReply] = []
    actions: list[SetupAction] = []

    # Metadata
    metadata: dict[str, Any] = {}

    # Progress indicators
    step_number: int | None = None
    total_steps: int | None = None
    progress_percent: float | None = None

    # Typing indicator
    is_typing: bool = False

    # Error state
    is_error: bool = False
    error_code: str | None = None


class ChatResponse(BaseModel):
    """Response from the chatbot."""

    message: ChatMessage
    session_id: str

    # Flow state
    current_step: str | None = None
    can_go_back: bool = False
    is_complete: bool = False

    # Collected data so far
    collected_data: dict[str, Any] = {}

    # Validation errors
    errors: list[str] = []
    warnings: list[str] = []

    # Suggestions for next actions
    suggestions: list[str] = []


class AuditLogEntry(BaseModel):
    """Audit log entry for security tracking."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    session_id: str
    user_id: str
    tenant_id: str
    action: str
    resource_type: str | None = None
    resource_id: str | None = None
    ip_address: str | None = None
    user_agent: str | None = None
    success: bool = True
    error_message: str | None = None
    metadata: dict[str, Any] = {}


class RateLimitInfo(BaseModel):
    """Rate limiting information."""

    requests_remaining: int
    requests_limit: int
    reset_at: datetime
    retry_after_seconds: int | None = None


class SetupSession(BaseModel):
    """A setup conversation session with security features."""

    id: str = Field(default_factory=lambda: str(uuid4()))
    tenant_id: str
    user_id: str

    # Current flow
    flow_type: str | None = None
    current_step: str | None = None

    # Collected data (sensitive data should be encrypted)
    data: dict[str, Any] = {}

    # History
    messages: list[ChatMessage] = []

    # State
    started_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: datetime | None = None
    is_active: bool = True

    # Context
    context: dict[str, Any] = {}

    # Security
    ip_address: str | None = None
    user_agent: str | None = None
    csrf_token: str = Field(default_factory=lambda: secrets.token_urlsafe(32))
    request_count: int = 0
    last_request_at: datetime | None = None

    # Rate limiting
    rate_limit: RateLimitInfo | None = None

    def increment_request_count(self) -> None:
        """Increment request count and update timestamp."""
        self.request_count += 1
        self.last_request_at = datetime.utcnow()

    def is_rate_limited(self, max_requests_per_minute: int = 60) -> bool:
        """Check if session is rate limited."""
        if not self.last_request_at:
            return False
        elapsed = (datetime.utcnow() - self.last_request_at).total_seconds()
        if elapsed > 60:
            self.request_count = 0
            return False
        return self.request_count >= max_requests_per_minute


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_plugin_by_category(category: PluginCategory) -> list[PluginConfig]:
    """Get all plugins in a category."""
    return [
        config for config in PLUGIN_CONFIGS.values()
        if config.category == category
    ]


def get_available_plugins(include_beta: bool = False, include_enterprise: bool = False) -> list[PluginConfig]:
    """Get list of available plugins based on feature flags."""
    return [
        config for config in PLUGIN_CONFIGS.values()
        if (not config.is_beta or include_beta) and
           (not config.is_enterprise or include_enterprise)
    ]


def validate_plugin_credentials(plugin: str, credentials: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate credentials for a plugin.

    Returns:
        Tuple of (is_valid, list of error messages)
    """
    config = PLUGIN_CONFIGS.get(plugin)
    if not config:
        return False, [f"Unknown plugin: {plugin}"]

    errors = []

    # Check required fields
    for field in config.required_fields:
        if not credentials.get(field):
            desc = config.field_descriptions.get(field, field)
            errors.append(f"Missing required field: {desc}")

    # Validate field patterns
    for field, pattern in config.field_patterns.items():
        value = credentials.get(field)
        if value and not re.match(pattern, value):
            desc = config.field_descriptions.get(field, field)
            example = config.field_examples.get(field, "")
            error_msg = f"Invalid format for {desc}"
            if example:
                error_msg += f" (example: {example})"
            errors.append(error_msg)

    return len(errors) == 0, errors
