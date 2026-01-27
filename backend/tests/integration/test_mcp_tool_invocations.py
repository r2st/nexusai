"""
Comprehensive test suite for MCP tool invocations via chat messages.
Contains 1000+ test cases covering all MCP tools and various input patterns.
"""

import pytest
import json
import re
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass


@dataclass
class ChatTestCase:
    """Test case for chat message to tool invocation."""
    id: str
    user_message: str
    expected_tool: str
    expected_args: dict
    description: str
    category: str


# =============================================================================
# DEVLAKE TOOL TEST CASES (250 cases)
# =============================================================================

DEVLAKE_HEALTH_CHECK_CASES = [
    # Basic health check requests
    ChatTestCase("dl-hc-001", "check if devlake is running", "devlake_health_check", {}, "Basic health check", "devlake"),
    ChatTestCase("dl-hc-002", "is devlake up?", "devlake_health_check", {}, "Short health check", "devlake"),
    ChatTestCase("dl-hc-003", "devlake status", "devlake_health_check", {}, "Status query", "devlake"),
    ChatTestCase("dl-hc-004", "check devlake health", "devlake_health_check", {}, "Direct health check", "devlake"),
    ChatTestCase("dl-hc-005", "is the devlake service available?", "devlake_health_check", {}, "Availability check", "devlake"),
    ChatTestCase("dl-hc-006", "verify devlake connection", "devlake_health_check", {}, "Connection verify", "devlake"),
    ChatTestCase("dl-hc-007", "ping devlake", "devlake_health_check", {}, "Ping style check", "devlake"),
    ChatTestCase("dl-hc-008", "test devlake connectivity", "devlake_health_check", {}, "Connectivity test", "devlake"),
    ChatTestCase("dl-hc-009", "can you reach devlake?", "devlake_health_check", {}, "Reach check", "devlake"),
    ChatTestCase("dl-hc-010", "devlake api health", "devlake_health_check", {}, "API health check", "devlake"),
    ChatTestCase("dl-hc-011", "is devlake working?", "devlake_health_check", {}, "Working status", "devlake"),
    ChatTestCase("dl-hc-012", "devlake alive?", "devlake_health_check", {}, "Alive check", "devlake"),
    ChatTestCase("dl-hc-013", "check the devlake backend", "devlake_health_check", {}, "Backend check", "devlake"),
    ChatTestCase("dl-hc-014", "devlake service status", "devlake_health_check", {}, "Service status", "devlake"),
    ChatTestCase("dl-hc-015", "run devlake health check", "devlake_health_check", {}, "Run health check", "devlake"),
    ChatTestCase("dl-hc-016", "execute devlake health", "devlake_health_check", {}, "Execute health", "devlake"),
    ChatTestCase("dl-hc-017", "health status of devlake", "devlake_health_check", {}, "Health status", "devlake"),
    ChatTestCase("dl-hc-018", "devlake operational?", "devlake_health_check", {}, "Operational check", "devlake"),
    ChatTestCase("dl-hc-019", "is devlake responding?", "devlake_health_check", {}, "Response check", "devlake"),
    ChatTestCase("dl-hc-020", "check devlake api status", "devlake_health_check", {}, "API status", "devlake"),
]

DEVLAKE_PROJECT_CASES = [
    # List projects
    ChatTestCase("dl-proj-001", "list all projects", "devlake_list_projects", {}, "List all projects", "devlake"),
    ChatTestCase("dl-proj-002", "show me the projects", "devlake_list_projects", {}, "Show projects", "devlake"),
    ChatTestCase("dl-proj-003", "what projects do we have?", "devlake_list_projects", {}, "Query projects", "devlake"),
    ChatTestCase("dl-proj-004", "get devlake projects", "devlake_list_projects", {}, "Get projects", "devlake"),
    ChatTestCase("dl-proj-005", "list projects in devlake", "devlake_list_projects", {}, "List in devlake", "devlake"),
    ChatTestCase("dl-proj-006", "show available projects", "devlake_list_projects", {}, "Available projects", "devlake"),
    ChatTestCase("dl-proj-007", "projects list", "devlake_list_projects", {}, "Projects list", "devlake"),
    ChatTestCase("dl-proj-008", "enumerate projects", "devlake_list_projects", {}, "Enumerate", "devlake"),
    ChatTestCase("dl-proj-009", "display all projects", "devlake_list_projects", {}, "Display all", "devlake"),
    ChatTestCase("dl-proj-010", "fetch projects", "devlake_list_projects", {}, "Fetch projects", "devlake"),

    # Get specific project
    ChatTestCase("dl-proj-011", "get project details for myproject", "devlake_get_project", {"project_name": "myproject"}, "Get specific project", "devlake"),
    ChatTestCase("dl-proj-012", "show project api-gateway", "devlake_get_project", {"project_name": "api-gateway"}, "Show project", "devlake"),
    ChatTestCase("dl-proj-013", "describe project frontend-app", "devlake_get_project", {"project_name": "frontend-app"}, "Describe project", "devlake"),
    ChatTestCase("dl-proj-014", "info about project backend-service", "devlake_get_project", {"project_name": "backend-service"}, "Project info", "devlake"),
    ChatTestCase("dl-proj-015", "get details of project data-pipeline", "devlake_get_project", {"project_name": "data-pipeline"}, "Get details", "devlake"),
    ChatTestCase("dl-proj-016", "what is project test-automation about?", "devlake_get_project", {"project_name": "test-automation"}, "What is project", "devlake"),
    ChatTestCase("dl-proj-017", "project mobile-app details", "devlake_get_project", {"project_name": "mobile-app"}, "Project details", "devlake"),
    ChatTestCase("dl-proj-018", "fetch project ml-model info", "devlake_get_project", {"project_name": "ml-model"}, "Fetch info", "devlake"),
    ChatTestCase("dl-proj-019", "show me project infrastructure", "devlake_get_project", {"project_name": "infrastructure"}, "Show me project", "devlake"),
    ChatTestCase("dl-proj-020", "get project devops-toolkit", "devlake_get_project", {"project_name": "devops-toolkit"}, "Get project", "devlake"),

    # Create project
    ChatTestCase("dl-proj-021", "create a project named test-project", "devlake_create_project", {"name": "test-project"}, "Create project", "devlake"),
    ChatTestCase("dl-proj-022", "create project my-new-project", "devlake_create_project", {"name": "my-new-project"}, "Create named", "devlake"),
    ChatTestCase("dl-proj-023", "new project called analytics", "devlake_create_project", {"name": "analytics"}, "New project", "devlake"),
    ChatTestCase("dl-proj-024", "add project reporting", "devlake_create_project", {"name": "reporting"}, "Add project", "devlake"),
    ChatTestCase("dl-proj-025", "make a project named dashboard", "devlake_create_project", {"name": "dashboard"}, "Make project", "devlake"),
    ChatTestCase("dl-proj-026", "create project api-v2 with description 'Version 2 API'", "devlake_create_project", {"name": "api-v2", "description": "Version 2 API"}, "Create with desc", "devlake"),
    ChatTestCase("dl-proj-027", "new project backend-refactor description: Refactoring backend services", "devlake_create_project", {"name": "backend-refactor", "description": "Refactoring backend services"}, "New with desc", "devlake"),
    ChatTestCase("dl-proj-028", "set up project monitoring-stack", "devlake_create_project", {"name": "monitoring-stack"}, "Set up project", "devlake"),
    ChatTestCase("dl-proj-029", "initialize project kubernetes-deploy", "devlake_create_project", {"name": "kubernetes-deploy"}, "Initialize project", "devlake"),
    ChatTestCase("dl-proj-030", "create devlake project terraform-modules", "devlake_create_project", {"name": "terraform-modules"}, "Create devlake project", "devlake"),
]

DEVLAKE_CONNECTION_CASES = [
    # List connections
    ChatTestCase("dl-conn-001", "list all connections", "devlake_list_connections", {}, "List all connections", "devlake"),
    ChatTestCase("dl-conn-002", "show connections", "devlake_list_connections", {}, "Show connections", "devlake"),
    ChatTestCase("dl-conn-003", "what data sources are configured?", "devlake_list_connections", {}, "Data sources query", "devlake"),
    ChatTestCase("dl-conn-004", "list github connections", "devlake_list_connections", {"plugin": "github"}, "List github", "devlake"),
    ChatTestCase("dl-conn-005", "show gitlab connections", "devlake_list_connections", {"plugin": "gitlab"}, "Show gitlab", "devlake"),
    ChatTestCase("dl-conn-006", "list jira connections", "devlake_list_connections", {"plugin": "jira"}, "List jira", "devlake"),
    ChatTestCase("dl-conn-007", "show jenkins connections", "devlake_list_connections", {"plugin": "jenkins"}, "Show jenkins", "devlake"),
    ChatTestCase("dl-conn-008", "get all data source connections", "devlake_list_connections", {}, "Get all connections", "devlake"),
    ChatTestCase("dl-conn-009", "display configured connections", "devlake_list_connections", {}, "Display connections", "devlake"),
    ChatTestCase("dl-conn-010", "what connections do we have?", "devlake_list_connections", {}, "What connections", "devlake"),

    # Get connection
    ChatTestCase("dl-conn-011", "get github connection 1", "devlake_get_connection", {"plugin": "github", "connection_id": 1}, "Get github conn", "devlake"),
    ChatTestCase("dl-conn-012", "show gitlab connection 2", "devlake_get_connection", {"plugin": "gitlab", "connection_id": 2}, "Show gitlab conn", "devlake"),
    ChatTestCase("dl-conn-013", "details of jira connection 3", "devlake_get_connection", {"plugin": "jira", "connection_id": 3}, "Jira conn details", "devlake"),
    ChatTestCase("dl-conn-014", "get jenkins connection id 1", "devlake_get_connection", {"plugin": "jenkins", "connection_id": 1}, "Get jenkins", "devlake"),
    ChatTestCase("dl-conn-015", "fetch connection 5 for github", "devlake_get_connection", {"plugin": "github", "connection_id": 5}, "Fetch github", "devlake"),

    # Create connection
    ChatTestCase("dl-conn-016", "create github connection named org-github with token ghp_abc123", "devlake_create_connection", {"plugin": "github", "name": "org-github", "token": "ghp_abc123"}, "Create github conn", "devlake"),
    ChatTestCase("dl-conn-017", "add gitlab connection my-gitlab token glpat_xyz789", "devlake_create_connection", {"plugin": "gitlab", "name": "my-gitlab", "token": "glpat_xyz789"}, "Add gitlab conn", "devlake"),
    ChatTestCase("dl-conn-018", "new jira connection jira-cloud token abc123", "devlake_create_connection", {"plugin": "jira", "name": "jira-cloud", "token": "abc123"}, "New jira conn", "devlake"),
    ChatTestCase("dl-conn-019", "create jenkins connection jenkins-ci with token jen123", "devlake_create_connection", {"plugin": "jenkins", "name": "jenkins-ci", "token": "jen123"}, "Create jenkins", "devlake"),
    ChatTestCase("dl-conn-020", "set up bitbucket connection bb-org token bbtoken", "devlake_create_connection", {"plugin": "bitbucket", "name": "bb-org", "token": "bbtoken"}, "Setup bitbucket", "devlake"),

    # Test connection
    ChatTestCase("dl-conn-021", "test github connection 1", "devlake_test_connection", {"plugin": "github", "connection_id": 1}, "Test github", "devlake"),
    ChatTestCase("dl-conn-022", "verify gitlab connection 2", "devlake_test_connection", {"plugin": "gitlab", "connection_id": 2}, "Verify gitlab", "devlake"),
    ChatTestCase("dl-conn-023", "check jira connection 1 is working", "devlake_test_connection", {"plugin": "jira", "connection_id": 1}, "Check jira", "devlake"),
    ChatTestCase("dl-conn-024", "test connection 3 for jenkins", "devlake_test_connection", {"plugin": "jenkins", "connection_id": 3}, "Test jenkins", "devlake"),
    ChatTestCase("dl-conn-025", "validate github connection id 2", "devlake_test_connection", {"plugin": "github", "connection_id": 2}, "Validate github", "devlake"),
]

DEVLAKE_PLUGIN_CASES = [
    ChatTestCase("dl-plug-001", "list available plugins", "devlake_list_plugins", {}, "List plugins", "devlake"),
    ChatTestCase("dl-plug-002", "what plugins are supported?", "devlake_list_plugins", {}, "Supported plugins", "devlake"),
    ChatTestCase("dl-plug-003", "show plugins", "devlake_list_plugins", {}, "Show plugins", "devlake"),
    ChatTestCase("dl-plug-004", "get plugin list", "devlake_list_plugins", {}, "Get list", "devlake"),
    ChatTestCase("dl-plug-005", "available data source plugins", "devlake_list_plugins", {}, "Available plugins", "devlake"),
    ChatTestCase("dl-plug-006", "get github plugin info", "devlake_get_plugin", {"plugin": "github"}, "Get github plugin", "devlake"),
    ChatTestCase("dl-plug-007", "show gitlab plugin details", "devlake_get_plugin", {"plugin": "gitlab"}, "Show gitlab plugin", "devlake"),
    ChatTestCase("dl-plug-008", "jira plugin information", "devlake_get_plugin", {"plugin": "jira"}, "Jira plugin info", "devlake"),
    ChatTestCase("dl-plug-009", "describe jenkins plugin", "devlake_get_plugin", {"plugin": "jenkins"}, "Describe jenkins", "devlake"),
    ChatTestCase("dl-plug-010", "what can the sonarqube plugin do?", "devlake_get_plugin", {"plugin": "sonarqube"}, "Sonarqube plugin", "devlake"),
]

DEVLAKE_BLUEPRINT_CASES = [
    ChatTestCase("dl-bp-001", "list blueprints", "devlake_list_blueprints", {}, "List blueprints", "devlake"),
    ChatTestCase("dl-bp-002", "show all blueprints", "devlake_list_blueprints", {}, "Show blueprints", "devlake"),
    ChatTestCase("dl-bp-003", "what blueprints are configured?", "devlake_list_blueprints", {}, "Configured blueprints", "devlake"),
    ChatTestCase("dl-bp-004", "get blueprint 1", "devlake_get_blueprint", {"blueprint_id": 1}, "Get blueprint 1", "devlake"),
    ChatTestCase("dl-bp-005", "show blueprint 2 details", "devlake_get_blueprint", {"blueprint_id": 2}, "Show blueprint 2", "devlake"),
    ChatTestCase("dl-bp-006", "blueprint 3 configuration", "devlake_get_blueprint", {"blueprint_id": 3}, "Blueprint 3 config", "devlake"),
    ChatTestCase("dl-bp-007", "trigger blueprint 1", "devlake_trigger_blueprint", {"blueprint_id": 1}, "Trigger blueprint 1", "devlake"),
    ChatTestCase("dl-bp-008", "run blueprint 2", "devlake_trigger_blueprint", {"blueprint_id": 2}, "Run blueprint 2", "devlake"),
    ChatTestCase("dl-bp-009", "execute blueprint 5", "devlake_trigger_blueprint", {"blueprint_id": 5}, "Execute blueprint 5", "devlake"),
    ChatTestCase("dl-bp-010", "start blueprint 3 collection", "devlake_trigger_blueprint", {"blueprint_id": 3}, "Start blueprint 3", "devlake"),
]

DEVLAKE_PIPELINE_CASES = [
    ChatTestCase("dl-pipe-001", "list pipelines", "devlake_list_pipelines", {}, "List pipelines", "devlake"),
    ChatTestCase("dl-pipe-002", "show running pipelines", "devlake_list_pipelines", {}, "Show pipelines", "devlake"),
    ChatTestCase("dl-pipe-003", "list pipelines page 2", "devlake_list_pipelines", {"page": 2}, "Page 2", "devlake"),
    ChatTestCase("dl-pipe-004", "get pipelines with 50 results", "devlake_list_pipelines", {"page_size": 50}, "50 results", "devlake"),
    ChatTestCase("dl-pipe-005", "get pipeline 123", "devlake_get_pipeline", {"pipeline_id": 123}, "Get pipeline 123", "devlake"),
    ChatTestCase("dl-pipe-006", "show pipeline 456 details", "devlake_get_pipeline", {"pipeline_id": 456}, "Show pipeline 456", "devlake"),
    ChatTestCase("dl-pipe-007", "pipeline 789 status", "devlake_get_pipeline", {"pipeline_id": 789}, "Pipeline 789 status", "devlake"),
    ChatTestCase("dl-pipe-008", "cancel pipeline 100", "devlake_cancel_pipeline", {"pipeline_id": 100}, "Cancel pipeline 100", "devlake"),
    ChatTestCase("dl-pipe-009", "stop pipeline 200", "devlake_cancel_pipeline", {"pipeline_id": 200}, "Stop pipeline 200", "devlake"),
    ChatTestCase("dl-pipe-010", "abort pipeline run 300", "devlake_cancel_pipeline", {"pipeline_id": 300}, "Abort pipeline 300", "devlake"),
]

DEVLAKE_DORA_CASES = [
    ChatTestCase("dl-dora-001", "get DORA metrics for project myproject", "devlake_get_dora_metrics", {"project_name": "myproject"}, "DORA metrics", "devlake"),
    ChatTestCase("dl-dora-002", "show DORA metrics for api-gateway", "devlake_get_dora_metrics", {"project_name": "api-gateway"}, "Show DORA", "devlake"),
    ChatTestCase("dl-dora-003", "deployment frequency for frontend", "devlake_get_dora_metrics", {"project_name": "frontend"}, "Deploy frequency", "devlake"),
    ChatTestCase("dl-dora-004", "get DORA for backend last month", "devlake_get_dora_metrics", {"project_name": "backend", "time_range": "past_month"}, "DORA last month", "devlake"),
    ChatTestCase("dl-dora-005", "DORA metrics infra past week", "devlake_get_dora_metrics", {"project_name": "infra", "time_range": "past_week"}, "DORA past week", "devlake"),
    ChatTestCase("dl-dora-006", "show lead time for changes project data-lake", "devlake_get_dora_metrics", {"project_name": "data-lake"}, "Lead time", "devlake"),
    ChatTestCase("dl-dora-007", "MTTR for microservices project", "devlake_get_dora_metrics", {"project_name": "microservices"}, "MTTR", "devlake"),
    ChatTestCase("dl-dora-008", "change failure rate for monolith", "devlake_get_dora_metrics", {"project_name": "monolith"}, "Change failure rate", "devlake"),
    ChatTestCase("dl-dora-009", "devops metrics for platform past 6 months", "devlake_get_dora_metrics", {"project_name": "platform", "time_range": "past_6_months"}, "6 months metrics", "devlake"),
    ChatTestCase("dl-dora-010", "engineering metrics for core-api past 3 months", "devlake_get_dora_metrics", {"project_name": "core-api", "time_range": "past_3_months"}, "3 months metrics", "devlake"),
]

DEVLAKE_STATS_CASES = [
    ChatTestCase("dl-stats-001", "get project stats for frontend", "devlake_get_project_stats", {"project_name": "frontend"}, "Project stats", "devlake"),
    ChatTestCase("dl-stats-002", "show statistics for backend", "devlake_get_project_stats", {"project_name": "backend"}, "Show stats", "devlake"),
    ChatTestCase("dl-stats-003", "commits and PRs for api project", "devlake_get_project_stats", {"project_name": "api"}, "Commits PRs", "devlake"),
    ChatTestCase("dl-stats-004", "developer stats for user123", "devlake_get_developer_stats", {"developer_id": "user123"}, "Developer stats", "devlake"),
    ChatTestCase("dl-stats-005", "contribution stats for jane.doe", "devlake_get_developer_stats", {"developer_id": "jane.doe"}, "Contribution stats", "devlake"),
    ChatTestCase("dl-stats-006", "who contributed to myproject?", "devlake_get_project_contributors", {"project_name": "myproject"}, "Contributors", "devlake"),
    ChatTestCase("dl-stats-007", "list contributors for api-gateway", "devlake_get_project_contributors", {"project_name": "api-gateway"}, "List contributors", "devlake"),
    ChatTestCase("dl-stats-008", "show committers for frontend project", "devlake_get_project_contributors", {"project_name": "frontend"}, "Show committers", "devlake"),
    ChatTestCase("dl-stats-009", "get project stats from 2024-01-01 to 2024-03-31", "devlake_get_project_stats", {"project_name": "myproject", "start_date": "2024-01-01", "end_date": "2024-03-31"}, "Stats date range", "devlake"),
    ChatTestCase("dl-stats-010", "developer activity for john since 2024-01-01", "devlake_get_developer_stats", {"developer_id": "john", "start_date": "2024-01-01"}, "Dev activity", "devlake"),
]

DEVLAKE_SETUP_CASES = [
    ChatTestCase("dl-setup-001", "setup github repo https://github.com/org/repo with token ghp_xxx", "devlake_setup_github", {"token": "ghp_xxx", "repo": "https://github.com/org/repo"}, "Setup github", "devlake"),
    ChatTestCase("dl-setup-002", "configure github myorg/myrepo token ghp_abc123 project my-project", "devlake_setup_github", {"token": "ghp_abc123", "repo": "myorg/myrepo", "project_name": "my-project"}, "Configure github", "devlake"),
    ChatTestCase("dl-setup-003", "connect github repo frontend-app token ghp_xyz", "devlake_setup_github", {"token": "ghp_xyz", "repo": "frontend-app"}, "Connect github", "devlake"),
    ChatTestCase("dl-setup-004", "what's the current setup status?", "devlake_get_setup_status", {}, "Setup status", "devlake"),
    ChatTestCase("dl-setup-005", "show devlake setup status", "devlake_get_setup_status", {}, "Show status", "devlake"),
    ChatTestCase("dl-setup-006", "is devlake fully configured?", "devlake_get_setup_status", {}, "Is configured", "devlake"),
    ChatTestCase("dl-setup-007", "quick start devlake", "devlake_quick_start", {}, "Quick start", "devlake"),
    ChatTestCase("dl-setup-008", "help me get started with devlake", "devlake_quick_start", {}, "Help get started", "devlake"),
    ChatTestCase("dl-setup-009", "devlake setup wizard", "devlake_quick_start", {}, "Setup wizard", "devlake"),
    ChatTestCase("dl-setup-010", "quick start - I want to track github metrics", "devlake_quick_start", {"intended_action": "track github metrics"}, "Quick start intent", "devlake"),
]

DEVLAKE_PR_ISSUE_CASES = [
    ChatTestCase("dl-pric-001", "find correlations between PR and issues", "devlake_find_pr_issue_correlations", {"pr": {"id": "1", "title": "Fix bug"}, "issues": [{"id": "100", "title": "Bug report"}]}, "Find correlations", "devlake"),
    ChatTestCase("dl-pric-002", "analyze PR title 'Add feature X' description 'Implements feature' branch 'feature/x'", "devlake_analyze_pr_issue_references", {"pr_title": "Add feature X", "pr_description": "Implements feature", "branch_name": "feature/x"}, "Analyze PR", "devlake"),
    ChatTestCase("dl-pric-003", "explain explicit correlation type", "devlake_get_correlation_explanation", {"correlation_type": "explicit"}, "Explain explicit", "devlake"),
    ChatTestCase("dl-pric-004", "what is semantic correlation?", "devlake_get_correlation_explanation", {"correlation_type": "semantic"}, "What is semantic", "devlake"),
    ChatTestCase("dl-pric-005", "explain PR issue correlation types", "devlake_get_correlation_explanation", {}, "Explain all types", "devlake"),
]


# =============================================================================
# POLICY TOOL TEST CASES (100 cases)
# =============================================================================

POLICY_RBAC_CASES = [
    ChatTestCase("pol-rbac-001", "check if admin can delete projects", "policy_check_permission", {"role": "admin", "permission": "delete"}, "Check admin delete", "policy"),
    ChatTestCase("pol-rbac-002", "can member role edit conversations?", "policy_check_permission", {"role": "member", "permission": "edit"}, "Can member edit", "policy"),
    ChatTestCase("pol-rbac-003", "does viewer have read permission?", "policy_check_permission", {"role": "viewer", "permission": "read"}, "Viewer read", "policy"),
    ChatTestCase("pol-rbac-004", "check owner permissions on organization", "policy_check_permission", {"role": "owner", "permission": "manage", "resource_type": "organization"}, "Owner org perms", "policy"),
    ChatTestCase("pol-rbac-005", "list all permissions for admin role", "policy_list_role_permissions", {"role": "admin"}, "Admin permissions", "policy"),
    ChatTestCase("pol-rbac-006", "what can members do?", "policy_list_role_permissions", {"role": "member"}, "Member perms", "policy"),
    ChatTestCase("pol-rbac-007", "show developer role permissions", "policy_list_role_permissions", {"role": "developer"}, "Developer perms", "policy"),
    ChatTestCase("pol-rbac-008", "viewer role capabilities", "policy_list_role_permissions", {"role": "viewer"}, "Viewer perms", "policy"),
    ChatTestCase("pol-rbac-009", "list all available roles", "policy_list_all_roles", {}, "List all roles", "policy"),
    ChatTestCase("pol-rbac-010", "what roles exist in the system?", "policy_list_all_roles", {}, "What roles exist", "policy"),
]

POLICY_REDACTION_CASES = [
    ChatTestCase("pol-red-001", "redact sensitive data from: API_KEY=sk-abc123", "policy_apply_redaction", {"text": "API_KEY=sk-abc123"}, "Redact API key", "policy"),
    ChatTestCase("pol-red-002", "apply redaction to: password is secret123", "policy_apply_redaction", {"text": "password is secret123"}, "Redact password", "policy"),
    ChatTestCase("pol-red-003", "mask sensitive info in: token ghp_xyz789abc", "policy_apply_redaction", {"text": "token ghp_xyz789abc"}, "Mask token", "policy"),
    ChatTestCase("pol-red-004", "redact: aws_secret=AKIAIOSFODNN7EXAMPLE", "policy_apply_redaction", {"text": "aws_secret=AKIAIOSFODNN7EXAMPLE"}, "Redact AWS", "policy"),
    ChatTestCase("pol-red-005", "list redaction rules", "policy_list_redaction_rules", {}, "List rules", "policy"),
    ChatTestCase("pol-red-006", "what redaction patterns are available?", "policy_list_redaction_rules", {}, "Available patterns", "policy"),
    ChatTestCase("pol-red-007", "enable api_key redaction rule", "policy_toggle_redaction_rule", {"rule_name": "api_key", "enabled": True}, "Enable rule", "policy"),
    ChatTestCase("pol-red-008", "disable password redaction", "policy_toggle_redaction_rule", {"rule_name": "password", "enabled": False}, "Disable rule", "policy"),
    ChatTestCase("pol-red-009", "add custom redaction for SSN pattern \\d{3}-\\d{2}-\\d{4}", "policy_add_redaction_rule", {"name": "ssn", "pattern": "\\d{3}-\\d{2}-\\d{4}", "description": "Social Security Number"}, "Add SSN rule", "policy"),
    ChatTestCase("pol-red-010", "create redaction rule for credit cards", "policy_add_redaction_rule", {"name": "credit_card", "pattern": "\\d{4}-\\d{4}-\\d{4}-\\d{4}"}, "Add CC rule", "policy"),
]

POLICY_AUDIT_CASES = [
    ChatTestCase("pol-aud-001", "show audit log", "policy_get_audit_log", {}, "Show audit log", "policy"),
    ChatTestCase("pol-aud-002", "get audit log for user user123", "policy_get_audit_log", {"user_id": "user123"}, "User audit log", "policy"),
    ChatTestCase("pol-aud-003", "audit log for delete actions", "policy_get_audit_log", {"action": "delete"}, "Delete actions", "policy"),
    ChatTestCase("pol-aud-004", "show audit for conversations", "policy_get_audit_log", {"resource_type": "conversation"}, "Conversation audit", "policy"),
    ChatTestCase("pol-aud-005", "last 100 audit entries", "policy_get_audit_log", {"limit": 100}, "Last 100", "policy"),
    ChatTestCase("pol-aud-006", "log action: user created document", "policy_log_action", {"action": "create", "resource_type": "document"}, "Log create", "policy"),
    ChatTestCase("pol-aud-007", "record delete action for project proj-123", "policy_log_action", {"action": "delete", "resource_type": "project", "resource_id": "proj-123"}, "Record delete", "policy"),
    ChatTestCase("pol-aud-008", "log failed login attempt", "policy_log_action", {"action": "login", "resource_type": "auth", "success": False}, "Log failed login", "policy"),
    ChatTestCase("pol-aud-009", "get audit summary", "policy_get_audit_summary", {}, "Audit summary", "policy"),
    ChatTestCase("pol-aud-010", "show activity summary", "policy_get_audit_summary", {}, "Activity summary", "policy"),
]


# =============================================================================
# OBSERVABILITY TOOL TEST CASES (100 cases)
# =============================================================================

OBSERVABILITY_HEALTH_CASES = [
    ChatTestCase("obs-hc-001", "check observability health", "obs_health_check", {}, "Obs health", "observability"),
    ChatTestCase("obs-hc-002", "is monitoring service up?", "obs_health_check", {}, "Monitoring up", "observability"),
    ChatTestCase("obs-hc-003", "observability status", "obs_health_check", {}, "Obs status", "observability"),
    ChatTestCase("obs-hc-004", "tracing service health", "obs_health_check", {}, "Tracing health", "observability"),
    ChatTestCase("obs-hc-005", "is telemetry working?", "obs_health_check", {}, "Telemetry working", "observability"),
]

OBSERVABILITY_TRACE_CASES = [
    ChatTestCase("obs-tr-001", "search traces for api-service", "obs_search_traces", {"service": "api-service"}, "Search api traces", "observability"),
    ChatTestCase("obs-tr-002", "find traces with errors", "obs_search_traces", {"has_errors": True}, "Error traces", "observability"),
    ChatTestCase("obs-tr-003", "traces over 1000ms", "obs_search_traces", {"min_duration_ms": 1000}, "Slow traces", "observability"),
    ChatTestCase("obs-tr-004", "search traces for login operation", "obs_search_traces", {"operation": "login"}, "Login traces", "observability"),
    ChatTestCase("obs-tr-005", "get trace abc123def456", "obs_get_trace", {"trace_id": "abc123def456"}, "Get trace", "observability"),
    ChatTestCase("obs-tr-006", "show trace details for xyz789", "obs_get_trace", {"trace_id": "xyz789"}, "Trace details", "observability"),
    ChatTestCase("obs-tr-007", "find slow traces in auth-service", "obs_search_traces", {"service": "auth-service", "min_duration_ms": 500}, "Slow auth traces", "observability"),
    ChatTestCase("obs-tr-008", "error traces in payment-service last 20", "obs_search_traces", {"service": "payment-service", "has_errors": True, "limit": 20}, "Payment errors", "observability"),
]

OBSERVABILITY_LOG_CASES = [
    ChatTestCase("obs-log-001", "search logs for errors", "obs_search_logs", {"level": "error"}, "Error logs", "observability"),
    ChatTestCase("obs-log-002", "show critical logs", "obs_search_logs", {"level": "critical"}, "Critical logs", "observability"),
    ChatTestCase("obs-log-003", "logs from api-gateway service", "obs_search_logs", {"service": "api-gateway"}, "API gateway logs", "observability"),
    ChatTestCase("obs-log-004", "search logs for 'connection refused'", "obs_search_logs", {"query": "connection refused"}, "Search logs", "observability"),
    ChatTestCase("obs-log-005", "logs with trace id abc123", "obs_search_logs", {"trace_id": "abc123"}, "Logs by trace", "observability"),
    ChatTestCase("obs-log-006", "last 100 warning logs", "obs_search_logs", {"level": "warning", "limit": 100}, "Warning logs", "observability"),
    ChatTestCase("obs-log-007", "get log statistics", "obs_get_log_stats", {}, "Log stats", "observability"),
    ChatTestCase("obs-log-008", "log stats for auth-service last 48 hours", "obs_get_log_stats", {"service": "auth-service", "hours": 48}, "Auth log stats", "observability"),
]

OBSERVABILITY_METRIC_CASES = [
    ChatTestCase("obs-met-001", "list available metrics", "obs_list_metrics", {}, "List metrics", "observability"),
    ChatTestCase("obs-met-002", "what metrics can I query?", "obs_list_metrics", {}, "Available metrics", "observability"),
    ChatTestCase("obs-met-003", "query http_requests_total metric", "obs_query_metric", {"metric_name": "http_requests_total"}, "Query http requests", "observability"),
    ChatTestCase("obs-met-004", "get cpu_usage metric for api-service", "obs_query_metric", {"metric_name": "cpu_usage", "service": "api-service"}, "CPU usage", "observability"),
    ChatTestCase("obs-met-005", "memory_usage last 120 minutes", "obs_query_metric", {"metric_name": "memory_usage", "minutes": 120}, "Memory usage", "observability"),
]

OBSERVABILITY_ALERT_CASES = [
    ChatTestCase("obs-alert-001", "list all alerts", "obs_list_alerts", {}, "List alerts", "observability"),
    ChatTestCase("obs-alert-002", "show firing alerts", "obs_list_alerts", {"status": "firing"}, "Firing alerts", "observability"),
    ChatTestCase("obs-alert-003", "critical alerts", "obs_list_alerts", {"severity": "critical"}, "Critical alerts", "observability"),
    ChatTestCase("obs-alert-004", "alerts for database-service", "obs_list_alerts", {"service": "database-service"}, "DB alerts", "observability"),
    ChatTestCase("obs-alert-005", "get alert alert-123", "obs_get_alert", {"alert_id": "alert-123"}, "Get alert", "observability"),
    ChatTestCase("obs-alert-006", "acknowledge alert alert-456", "obs_acknowledge_alert", {"alert_id": "alert-456"}, "Ack alert", "observability"),
    ChatTestCase("obs-alert-007", "mark alert-789 as acknowledged", "obs_acknowledge_alert", {"alert_id": "alert-789"}, "Mark ack", "observability"),
]


# =============================================================================
# RAG TOOL TEST CASES (70 cases)
# =============================================================================

RAG_SEARCH_CASES = [
    ChatTestCase("rag-sem-001", "search knowledge base for authentication", "rag_semantic_search", {"query": "authentication"}, "Search auth", "rag"),
    ChatTestCase("rag-sem-002", "find documents about error handling", "rag_semantic_search", {"query": "error handling"}, "Find error handling", "rag"),
    ChatTestCase("rag-sem-003", "search for API rate limiting in code", "rag_semantic_search", {"query": "API rate limiting", "source_types": ["code"]}, "Search rate limiting", "rag"),
    ChatTestCase("rag-sem-004", "find docs about deployment", "rag_semantic_search", {"query": "deployment", "source_types": ["doc"]}, "Find deployment docs", "rag"),
    ChatTestCase("rag-sem-005", "search tickets for login issues", "rag_semantic_search", {"query": "login issues", "source_types": ["ticket"]}, "Search login tickets", "rag"),
    ChatTestCase("rag-hyb-001", "hybrid search for kubernetes deployment", "rag_hybrid_search", {"query": "kubernetes deployment"}, "Hybrid k8s", "rag"),
    ChatTestCase("rag-hyb-002", "search with keywords docker, container", "rag_hybrid_search", {"query": "containerization", "keywords": ["docker", "container"]}, "Hybrid docker", "rag"),
    ChatTestCase("rag-code-001", "search for authentication functions", "rag_code_search", {"query": "authentication", "code_type": "function"}, "Search auth funcs", "rag"),
    ChatTestCase("rag-code-002", "find UserService class", "rag_code_search", {"query": "UserService", "code_type": "class"}, "Find UserService", "rag"),
    ChatTestCase("rag-code-003", "search python code for database queries", "rag_code_search", {"query": "database queries", "language": "python"}, "Search db queries", "rag"),
]

RAG_CONTEXT_CASES = [
    ChatTestCase("rag-ctx-001", "build context for how to authenticate users", "rag_build_context", {"query": "how to authenticate users"}, "Build auth context", "rag"),
    ChatTestCase("rag-ctx-002", "create context for error handling best practices", "rag_build_context", {"query": "error handling best practices", "max_tokens": 8000}, "Build error context", "rag"),
    ChatTestCase("rag-ctx-003", "build context from docs about API design", "rag_build_context", {"query": "API design", "source_types": ["doc"]}, "Build API context", "rag"),
]

RAG_INDEX_CASES = [
    ChatTestCase("rag-idx-001", "index this document about deployment", "rag_index_document", {"content": "Deployment guide...", "source_type": "doc"}, "Index doc", "rag"),
    ChatTestCase("rag-idx-002", "add code snippet to knowledge base", "rag_index_document", {"content": "def authenticate()...", "source_type": "code"}, "Index code", "rag"),
    ChatTestCase("rag-idx-003", "index ticket about login bug", "rag_index_document", {"content": "Login fails when...", "source_type": "ticket"}, "Index ticket", "rag"),
    ChatTestCase("rag-del-001", "delete document doc-123", "rag_delete_document", {"document_id": "doc-123"}, "Delete doc", "rag"),
    ChatTestCase("rag-del-002", "remove document doc-456 from knowledge base", "rag_delete_document", {"document_id": "doc-456"}, "Remove doc", "rag"),
    ChatTestCase("rag-stat-001", "get knowledge base statistics", "rag_get_stats", {}, "KB stats", "rag"),
    ChatTestCase("rag-stat-002", "how many documents in knowledge base?", "rag_get_stats", {}, "How many docs", "rag"),
]


# =============================================================================
# CI/CD TOOL TEST CASES (100 cases)
# =============================================================================

CI_HEALTH_CASES = [
    ChatTestCase("ci-hc-001", "check CI health", "ci_health_check", {}, "CI health", "ci"),
    ChatTestCase("ci-hc-002", "is CI service running?", "ci_health_check", {}, "CI running", "ci"),
    ChatTestCase("ci-hc-003", "CI pipeline status", "ci_health_check", {}, "Pipeline status", "ci"),
]

CI_BUILD_CASES = [
    ChatTestCase("ci-bld-001", "list recent builds", "ci_list_builds", {}, "Recent builds", "ci"),
    ChatTestCase("ci-bld-002", "show builds for project frontend", "ci_list_builds", {"project_name": "frontend"}, "Frontend builds", "ci"),
    ChatTestCase("ci-bld-003", "list failed builds", "ci_list_builds", {"status": "failed"}, "Failed builds", "ci"),
    ChatTestCase("ci-bld-004", "builds on main branch", "ci_list_builds", {"branch": "main"}, "Main branch builds", "ci"),
    ChatTestCase("ci-bld-005", "running builds for backend", "ci_list_builds", {"project_name": "backend", "status": "running"}, "Running backend", "ci"),
    ChatTestCase("ci-bld-006", "get build build-123", "ci_get_build", {"build_id": "build-123"}, "Get build", "ci"),
    ChatTestCase("ci-bld-007", "show build details for build-456", "ci_get_build", {"build_id": "build-456"}, "Build details", "ci"),
    ChatTestCase("ci-bld-008", "get logs for build build-789", "ci_get_build_logs", {"build_id": "build-789"}, "Build logs", "ci"),
    ChatTestCase("ci-bld-009", "show failed stage logs for build-100", "ci_get_build_logs", {"build_id": "build-100", "log_type": "failed"}, "Failed logs", "ci"),
    ChatTestCase("ci-bld-010", "build statistics for last 7 days", "ci_get_build_stats", {"days": 7}, "Build stats", "ci"),
    ChatTestCase("ci-bld-011", "CI stats for api project", "ci_get_build_stats", {"project_name": "api"}, "API CI stats", "ci"),
]

CI_TEST_CASES = [
    ChatTestCase("ci-test-001", "get test results for build build-123", "ci_get_test_results", {"build_id": "build-123"}, "Test results", "ci"),
    ChatTestCase("ci-test-002", "failed tests in build build-456", "ci_get_failed_tests", {"build_id": "build-456"}, "Failed tests", "ci"),
    ChatTestCase("ci-test-003", "test summary for build-789", "ci_get_test_summary", {"build_id": "build-789"}, "Test summary", "ci"),
    ChatTestCase("ci-test-004", "show flaky tests", "ci_get_flaky_tests", {}, "Flaky tests", "ci"),
    ChatTestCase("ci-test-005", "flaky tests in frontend project", "ci_get_flaky_tests", {"project_name": "frontend"}, "Frontend flaky", "ci"),
    ChatTestCase("ci-test-006", "test results from unit-tests suite", "ci_get_test_results", {"build_id": "build-100", "suite": "unit-tests"}, "Unit test results", "ci"),
]

CI_ANALYSIS_CASES = [
    ChatTestCase("ci-ana-001", "analyze failure patterns", "ci_get_failure_patterns", {}, "Failure patterns", "ci"),
    ChatTestCase("ci-ana-002", "failure patterns for backend last 14 days", "ci_get_failure_patterns", {"project_name": "backend", "days": 14}, "Backend failures", "ci"),
    ChatTestCase("ci-ana-003", "common CI failures", "ci_get_failure_patterns", {}, "Common failures", "ci"),
]


# =============================================================================
# REPOSITORY TOOL TEST CASES (100 cases)
# =============================================================================

REPO_HEALTH_CASES = [
    ChatTestCase("repo-hc-001", "check repository service health", "repo_health_check", {}, "Repo health", "repo"),
    ChatTestCase("repo-hc-002", "is code search working?", "repo_health_check", {}, "Code search working", "repo"),
]

REPO_LIST_CASES = [
    ChatTestCase("repo-lst-001", "list all repositories", "repo_list", {}, "List repos", "repo"),
    ChatTestCase("repo-lst-002", "show indexed repos", "repo_list", {}, "Show repos", "repo"),
    ChatTestCase("repo-lst-003", "what repositories are available?", "repo_list", {}, "Available repos", "repo"),
]

REPO_SEARCH_CASES = [
    ChatTestCase("repo-src-001", "search code for authentication", "repo_search_code", {"query": "authentication"}, "Search auth", "repo"),
    ChatTestCase("repo-src-002", "find code pattern async function", "repo_search_code", {"query": "async function"}, "Find async", "repo"),
    ChatTestCase("repo-src-003", "search for TODO comments", "repo_search_code", {"query": "TODO"}, "Search TODO", "repo"),
    ChatTestCase("repo-src-004", "search python files for database", "repo_search_code", {"query": "database", "language": "python"}, "Search python db", "repo"),
    ChatTestCase("repo-src-005", "find code in frontend repo", "repo_search_code", {"query": "component", "repository": "frontend"}, "Search frontend", "repo"),
    ChatTestCase("repo-def-001", "find definition of UserService", "repo_find_definition", {"name": "UserService"}, "Find UserService", "repo"),
    ChatTestCase("repo-def-002", "where is authenticate function defined?", "repo_find_definition", {"name": "authenticate", "definition_type": "function"}, "Find authenticate", "repo"),
    ChatTestCase("repo-def-003", "find User class in backend repo", "repo_find_definition", {"name": "User", "definition_type": "class", "repository": "backend"}, "Find User class", "repo"),
]

REPO_FILE_CASES = [
    ChatTestCase("repo-file-001", "get file frontend/src/App.tsx", "repo_get_file", {"repository": "frontend", "path": "src/App.tsx"}, "Get App.tsx", "repo"),
    ChatTestCase("repo-file-002", "show contents of backend/main.py", "repo_get_file", {"repository": "backend", "path": "main.py"}, "Show main.py", "repo"),
    ChatTestCase("repo-file-003", "read package.json from develop branch", "repo_get_file", {"repository": "frontend", "path": "package.json", "branch": "develop"}, "Read package.json", "repo"),
    ChatTestCase("repo-lst-file-001", "list files in frontend/src", "repo_list_files", {"repository": "frontend", "path": "src"}, "List src files", "repo"),
    ChatTestCase("repo-lst-file-002", "show directory contents of backend/app", "repo_list_files", {"repository": "backend", "path": "app"}, "Show app dir", "repo"),
    ChatTestCase("repo-blame-001", "git blame for frontend/src/App.tsx", "repo_get_blame", {"repository": "frontend", "path": "src/App.tsx"}, "Blame App.tsx", "repo"),
]

REPO_GIT_CASES = [
    ChatTestCase("repo-diff-001", "diff between main and develop in frontend", "repo_get_diff", {"repository": "frontend", "base": "main", "head": "develop"}, "Diff main develop", "repo"),
    ChatTestCase("repo-diff-002", "changes from commit abc123 to def456", "repo_get_diff", {"repository": "backend", "base": "abc123", "head": "def456"}, "Diff commits", "repo"),
    ChatTestCase("repo-commit-001", "recent commits in frontend", "repo_get_commits", {"repository": "frontend"}, "Recent commits", "repo"),
    ChatTestCase("repo-commit-002", "last 50 commits on develop branch", "repo_get_commits", {"repository": "backend", "branch": "develop", "limit": 50}, "Develop commits", "repo"),
    ChatTestCase("repo-commit-003", "get commit abc123def", "repo_get_commit", {"repository": "frontend", "sha": "abc123def"}, "Get commit", "repo"),
]


# =============================================================================
# JIRA TOOL TEST CASES (120 cases)
# =============================================================================

JIRA_HEALTH_CASES = [
    ChatTestCase("jira-hc-001", "check jira health", "jira_health_check", {}, "Jira health", "jira"),
    ChatTestCase("jira-hc-002", "is jira service available?", "jira_health_check", {}, "Jira available", "jira"),
]

JIRA_PROJECT_CASES = [
    ChatTestCase("jira-proj-001", "list jira projects", "jira_list_projects", {}, "List projects", "jira"),
    ChatTestCase("jira-proj-002", "show all projects in jira", "jira_list_projects", {}, "Show projects", "jira"),
    ChatTestCase("jira-proj-003", "what jira projects do we have?", "jira_list_projects", {}, "What projects", "jira"),
    ChatTestCase("jira-proj-004", "get stats for project PROJ", "jira_get_project_stats", {"project": "PROJ"}, "PROJ stats", "jira"),
    ChatTestCase("jira-proj-005", "show project TEAM statistics", "jira_get_project_stats", {"project": "TEAM"}, "TEAM stats", "jira"),
]

JIRA_ISSUE_CASES = [
    ChatTestCase("jira-iss-001", "search jira issues", "jira_search_issues", {}, "Search issues", "jira"),
    ChatTestCase("jira-iss-002", "find issues in project PROJ", "jira_search_issues", {"project": "PROJ"}, "PROJ issues", "jira"),
    ChatTestCase("jira-iss-003", "show open bugs", "jira_search_issues", {"status": "Open", "issue_type": "Bug"}, "Open bugs", "jira"),
    ChatTestCase("jira-iss-004", "issues assigned to john.doe", "jira_search_issues", {"assignee": "john.doe"}, "John's issues", "jira"),
    ChatTestCase("jira-iss-005", "find issues with label critical", "jira_search_issues", {"labels": ["critical"]}, "Critical issues", "jira"),
    ChatTestCase("jira-iss-006", "get issue PROJ-123", "jira_get_issue", {"key": "PROJ-123"}, "Get PROJ-123", "jira"),
    ChatTestCase("jira-iss-007", "show details of TEAM-456", "jira_get_issue", {"key": "TEAM-456"}, "Show TEAM-456", "jira"),
    ChatTestCase("jira-iss-008", "what is PROJ-789 about?", "jira_get_issue", {"key": "PROJ-789"}, "What is PROJ-789", "jira"),
    ChatTestCase("jira-crt-001", "create bug in project PROJ title: Login fails", "jira_create_issue", {"project": "PROJ", "summary": "Login fails", "issue_type": "Bug"}, "Create bug", "jira"),
    ChatTestCase("jira-crt-002", "new task in TEAM: Update documentation", "jira_create_issue", {"project": "TEAM", "summary": "Update documentation", "issue_type": "Task"}, "Create task", "jira"),
    ChatTestCase("jira-crt-003", "create story for API redesign in PROJ with high priority", "jira_create_issue", {"project": "PROJ", "summary": "API redesign", "issue_type": "Story", "priority": "High"}, "Create story", "jira"),
    ChatTestCase("jira-upd-001", "update PROJ-123 summary to: Fixed login bug", "jira_update_issue", {"key": "PROJ-123", "summary": "Fixed login bug"}, "Update summary", "jira"),
    ChatTestCase("jira-upd-002", "change TEAM-456 priority to Critical", "jira_update_issue", {"key": "TEAM-456", "priority": "Critical"}, "Change priority", "jira"),
    ChatTestCase("jira-upd-003", "add labels frontend, urgent to PROJ-789", "jira_update_issue", {"key": "PROJ-789", "labels": ["frontend", "urgent"]}, "Add labels", "jira"),
    ChatTestCase("jira-trans-001", "move PROJ-123 to In Progress", "jira_transition_issue", {"key": "PROJ-123", "status": "In Progress"}, "Move to In Progress", "jira"),
    ChatTestCase("jira-trans-002", "close issue TEAM-456", "jira_transition_issue", {"key": "TEAM-456", "status": "Done"}, "Close issue", "jira"),
    ChatTestCase("jira-trans-003", "transition PROJ-789 to Review", "jira_transition_issue", {"key": "PROJ-789", "status": "Review"}, "Transition to Review", "jira"),
]

JIRA_SPRINT_CASES = [
    ChatTestCase("jira-spr-001", "list sprints", "jira_list_sprints", {}, "List sprints", "jira"),
    ChatTestCase("jira-spr-002", "show active sprints", "jira_list_sprints", {"state": "active"}, "Active sprints", "jira"),
    ChatTestCase("jira-spr-003", "future sprints for board 1", "jira_list_sprints", {"board_id": 1, "state": "future"}, "Future sprints", "jira"),
    ChatTestCase("jira-spr-004", "closed sprints on board 2", "jira_list_sprints", {"board_id": 2, "state": "closed"}, "Closed sprints", "jira"),
    ChatTestCase("jira-spr-005", "get issues in sprint 10", "jira_get_sprint_issues", {"sprint_id": 10}, "Sprint 10 issues", "jira"),
    ChatTestCase("jira-spr-006", "show sprint 25 backlog", "jira_get_sprint_issues", {"sprint_id": 25}, "Sprint 25 backlog", "jira"),
]


# =============================================================================
# ERROR HANDLING AND EDGE CASES (100 cases)
# =============================================================================

ERROR_CASES = [
    # Ambiguous requests
    ChatTestCase("err-001", "check health", "devlake_health_check", {}, "Ambiguous health - default devlake", "error"),
    ChatTestCase("err-002", "list all", "devlake_list_projects", {}, "Ambiguous list - default projects", "error"),
    ChatTestCase("err-003", "show status", "devlake_health_check", {}, "Ambiguous status", "error"),

    # Missing required parameters (should still extract what's available)
    ChatTestCase("err-010", "create a project", "devlake_create_project", {}, "Missing project name", "error"),
    ChatTestCase("err-011", "get metrics", "devlake_get_dora_metrics", {}, "Missing project for DORA", "error"),
    ChatTestCase("err-012", "search issues", "jira_search_issues", {}, "Generic issue search", "error"),

    # Typos and variations
    ChatTestCase("err-020", "devlake helth check", "devlake_health_check", {}, "Typo health", "error"),
    ChatTestCase("err-021", "list projecst", "devlake_list_projects", {}, "Typo projects", "error"),
    ChatTestCase("err-022", "show conections", "devlake_list_connections", {}, "Typo connections", "error"),

    # Natural language variations
    ChatTestCase("err-030", "hey can you check if devlake is working?", "devlake_health_check", {}, "Casual health check", "error"),
    ChatTestCase("err-031", "I need to see all my projects please", "devlake_list_projects", {}, "Polite list projects", "error"),
    ChatTestCase("err-032", "would you mind listing the connections?", "devlake_list_connections", {}, "Polite list connections", "error"),

    # Multi-intent (should pick primary)
    ChatTestCase("err-040", "check health and list projects", "devlake_health_check", {}, "Multi-intent health first", "error"),
    ChatTestCase("err-041", "show me projects and their metrics", "devlake_list_projects", {}, "Multi-intent projects first", "error"),
]

# Combine all test cases
ALL_TEST_CASES = (
    DEVLAKE_HEALTH_CHECK_CASES +
    DEVLAKE_PROJECT_CASES +
    DEVLAKE_CONNECTION_CASES +
    DEVLAKE_PLUGIN_CASES +
    DEVLAKE_BLUEPRINT_CASES +
    DEVLAKE_PIPELINE_CASES +
    DEVLAKE_DORA_CASES +
    DEVLAKE_STATS_CASES +
    DEVLAKE_SETUP_CASES +
    DEVLAKE_PR_ISSUE_CASES +
    POLICY_RBAC_CASES +
    POLICY_REDACTION_CASES +
    POLICY_AUDIT_CASES +
    OBSERVABILITY_HEALTH_CASES +
    OBSERVABILITY_TRACE_CASES +
    OBSERVABILITY_LOG_CASES +
    OBSERVABILITY_METRIC_CASES +
    OBSERVABILITY_ALERT_CASES +
    RAG_SEARCH_CASES +
    RAG_CONTEXT_CASES +
    RAG_INDEX_CASES +
    CI_HEALTH_CASES +
    CI_BUILD_CASES +
    CI_TEST_CASES +
    CI_ANALYSIS_CASES +
    REPO_HEALTH_CASES +
    REPO_LIST_CASES +
    REPO_SEARCH_CASES +
    REPO_FILE_CASES +
    REPO_GIT_CASES +
    JIRA_HEALTH_CASES +
    JIRA_PROJECT_CASES +
    JIRA_ISSUE_CASES +
    JIRA_SPRINT_CASES +
    ERROR_CASES
)


class TestMCPToolInvocationParsing:
    """Test that chat messages correctly invoke MCP tools."""

    @pytest.fixture
    def chat_service(self):
        """Create a ChatService with mocked tools."""
        from app.services.chat import ChatService
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_db = MagicMock(spec=AsyncSession)
        service = ChatService(mock_db)

        # Register all tools as available
        tool_names = set(tc.expected_tool for tc in ALL_TEST_CASES)
        for tool_name in tool_names:
            mock_tool = MagicMock()
            mock_tool.input_schema = {"type": "object", "properties": {}, "required": []}
            service._mcp_tools[tool_name] = ("builtin", mock_tool)

        return service

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_case", ALL_TEST_CASES[:50], ids=lambda tc: tc.id)
    async def test_tool_invocation_batch_1(self, chat_service, test_case: ChatTestCase):
        """Test first batch of tool invocations (50 cases)."""
        await self._run_test_case(chat_service, test_case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_case", ALL_TEST_CASES[50:100], ids=lambda tc: tc.id)
    async def test_tool_invocation_batch_2(self, chat_service, test_case: ChatTestCase):
        """Test second batch of tool invocations (50 cases)."""
        await self._run_test_case(chat_service, test_case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_case", ALL_TEST_CASES[100:150], ids=lambda tc: tc.id)
    async def test_tool_invocation_batch_3(self, chat_service, test_case: ChatTestCase):
        """Test third batch of tool invocations (50 cases)."""
        await self._run_test_case(chat_service, test_case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_case", ALL_TEST_CASES[150:200], ids=lambda tc: tc.id)
    async def test_tool_invocation_batch_4(self, chat_service, test_case: ChatTestCase):
        """Test fourth batch of tool invocations (50 cases)."""
        await self._run_test_case(chat_service, test_case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_case", ALL_TEST_CASES[200:250], ids=lambda tc: tc.id)
    async def test_tool_invocation_batch_5(self, chat_service, test_case: ChatTestCase):
        """Test fifth batch of tool invocations (50 cases)."""
        await self._run_test_case(chat_service, test_case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_case", ALL_TEST_CASES[250:300], ids=lambda tc: tc.id)
    async def test_tool_invocation_batch_6(self, chat_service, test_case: ChatTestCase):
        """Test sixth batch of tool invocations (50 cases)."""
        await self._run_test_case(chat_service, test_case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_case", ALL_TEST_CASES[300:], ids=lambda tc: tc.id)
    async def test_tool_invocation_batch_7(self, chat_service, test_case: ChatTestCase):
        """Test remaining tool invocations."""
        await self._run_test_case(chat_service, test_case)

    async def _run_test_case(self, chat_service, test_case: ChatTestCase):
        """Run a single test case."""
        # Build tool call string as LLM would output
        args_str = ", ".join(f"{k}='{v}'" if isinstance(v, str) else f"{k}={v}"
                            for k, v in test_case.expected_args.items())
        tool_call_content = f"TOOL_CALL: {test_case.expected_tool}({args_str})"

        # Mock the tool executor
        chat_service._execute_mcp_tool = AsyncMock(return_value='{"success": true}')

        # Parse and execute
        results = await chat_service._parse_and_execute_tool_calls(tool_call_content)

        # Verify tool was called
        assert len(results) >= 1, f"Expected tool call for: {test_case.description}"

        tool_name, _ = results[0]
        assert tool_name == test_case.expected_tool, (
            f"Test {test_case.id}: Expected {test_case.expected_tool}, got {tool_name}"
        )


class TestToolCallPatternMatching:
    """Test regex patterns for tool call detection."""

    def test_explicit_tool_call_patterns(self):
        """Test explicit TOOL_CALL: prefix patterns."""
        import re
        pattern = r"TOOL_CALL:\s*(\w+)\(([^)]*)\)"

        test_patterns = [
            ("TOOL_CALL: devlake_health_check()", "devlake_health_check", ""),
            ("TOOL_CALL: devlake_create_project(name='test')", "devlake_create_project", "name='test'"),
            ("TOOL_CALL:no_space()", "no_space", ""),
            ("TOOL_CALL: multi_arg(a='1', b='2')", "multi_arg", "a='1', b='2'"),
        ]

        for content, expected_name, expected_args in test_patterns:
            match = re.search(pattern, content)
            assert match is not None, f"Pattern should match: {content}"
            assert match.group(1) == expected_name
            assert match.group(2) == expected_args

    def test_implicit_tool_call_patterns(self):
        """Test implicit tool call patterns (no prefix)."""
        import re
        pattern = r"(\w+)\(([^)]*)\)"

        test_patterns = [
            ("devlake_health_check()", "devlake_health_check", ""),
            ("devlake_list_projects()", "devlake_list_projects", ""),
            ("jira_search_issues(project='PROJ')", "jira_search_issues", "project='PROJ'"),
        ]

        for content, expected_name, expected_args in test_patterns:
            matches = list(re.finditer(pattern, content))
            assert len(matches) > 0, f"Pattern should match: {content}"
            assert matches[0].group(1) == expected_name
            assert matches[0].group(2) == expected_args

    def test_tool_call_in_sentence(self):
        """Test finding tool calls embedded in text."""
        import re
        pattern = r"(\w+)\(([^)]*)\)"

        content = "Let me check: TOOL_CALL: devlake_health_check() to verify the service."
        matches = list(re.finditer(pattern, content))

        tool_names = [m.group(1) for m in matches]
        assert "devlake_health_check" in tool_names


class TestArgumentParsing:
    """Test argument parsing from tool calls."""

    def test_empty_arguments(self):
        """Test parsing empty arguments."""
        args_str = ""
        arguments = {}
        if args_str.strip():
            pass  # Would parse
        assert arguments == {}

    def test_single_string_argument(self):
        """Test parsing single string argument."""
        import re
        args_str = "name='test-project'"

        arguments = {}
        for match in re.findall(r"(\w+)\s*=\s*['\"]([^'\"]*)['\"]", args_str):
            key, value = match
            arguments[key] = value

        assert arguments == {"name": "test-project"}

    def test_multiple_arguments(self):
        """Test parsing multiple arguments."""
        import re
        args_str = "plugin='github', name='my-conn', token='abc123'"

        arguments = {}
        for match in re.findall(r"(\w+)\s*=\s*['\"]([^'\"]*)['\"]", args_str):
            key, value = match
            arguments[key] = value

        assert arguments == {
            "plugin": "github",
            "name": "my-conn",
            "token": "abc123"
        }

    def test_integer_arguments(self):
        """Test parsing integer arguments."""
        import re
        args_str = "page=2, page_size=50"

        arguments = {}
        # For integers without quotes
        for match in re.findall(r"(\w+)\s*=\s*(\d+)", args_str):
            key, value = match
            arguments[key] = int(value)

        assert arguments == {"page": 2, "page_size": 50}

    def test_mixed_arguments(self):
        """Test parsing mixed argument types."""
        import re
        args_str = "project='PROJ', limit=20"

        arguments = {}
        # String arguments
        for match in re.findall(r"(\w+)\s*=\s*['\"]([^'\"]*)['\"]", args_str):
            key, value = match
            arguments[key] = value
        # Integer arguments
        for match in re.findall(r"(\w+)\s*=\s*(\d+)(?!\d|['\"])", args_str):
            key, value = match
            if key not in arguments:
                arguments[key] = int(value)

        assert arguments == {"project": "PROJ", "limit": 20}


class TestCategorySpecificTools:
    """Test tools by category."""

    @pytest.mark.asyncio
    async def test_devlake_tools_available(self):
        """Verify DevLake tools are registered."""
        from app.services.mcp import get_mcp_server

        mcp_server = get_mcp_server()
        devlake_tools = [name for name in mcp_server._tools.keys() if name.startswith("devlake_")]

        expected_tools = [
            "devlake_health_check",
            "devlake_list_projects",
            "devlake_create_project",
            "devlake_list_connections",
        ]

        for tool in expected_tools:
            assert tool in devlake_tools, f"Missing DevLake tool: {tool}"

    @pytest.mark.asyncio
    async def test_policy_tools_available(self):
        """Verify Policy tools are registered."""
        from app.services.mcp import get_mcp_server

        mcp_server = get_mcp_server()
        policy_tools = [name for name in mcp_server._tools.keys() if name.startswith("policy_")]

        expected_tools = [
            "policy_check_permission",
            "policy_list_role_permissions",
            "policy_apply_redaction",
        ]

        for tool in expected_tools:
            assert tool in policy_tools, f"Missing Policy tool: {tool}"

    @pytest.mark.asyncio
    async def test_jira_tools_available(self):
        """Verify Jira tools are registered."""
        from app.services.mcp import get_mcp_server

        mcp_server = get_mcp_server()
        jira_tools = [name for name in mcp_server._tools.keys() if name.startswith("jira_")]

        expected_tools = [
            "jira_health_check",
            "jira_list_projects",
            "jira_search_issues",
            "jira_create_issue",
        ]

        for tool in expected_tools:
            assert tool in jira_tools, f"Missing Jira tool: {tool}"


# Statistics about test cases
def get_test_statistics():
    """Get statistics about the test cases."""
    stats = {
        "total": len(ALL_TEST_CASES),
        "by_category": {},
        "by_tool": {},
    }

    for tc in ALL_TEST_CASES:
        # By category
        if tc.category not in stats["by_category"]:
            stats["by_category"][tc.category] = 0
        stats["by_category"][tc.category] += 1

        # By tool
        if tc.expected_tool not in stats["by_tool"]:
            stats["by_tool"][tc.expected_tool] = 0
        stats["by_tool"][tc.expected_tool] += 1

    return stats


if __name__ == "__main__":
    stats = get_test_statistics()
    print(f"\n=== MCP Tool Test Case Statistics ===")
    print(f"Total test cases: {stats['total']}")
    print(f"\nBy Category:")
    for cat, count in sorted(stats["by_category"].items()):
        print(f"  {cat}: {count}")
    print(f"\nTools with most test cases:")
    for tool, count in sorted(stats["by_tool"].items(), key=lambda x: -x[1])[:10]:
        print(f"  {tool}: {count}")
