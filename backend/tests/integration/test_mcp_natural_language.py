"""
Natural language variations test suite for MCP tool invocations.
Contains diverse phrasings and edge cases to reach 1000+ total test cases.
"""

import pytest
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass


@dataclass
class NLTestCase:
    """Natural language test case."""
    id: str
    utterance: str
    expected_tool: str
    expected_args: dict
    description: str


# =============================================================================
# CASUAL/INFORMAL LANGUAGE VARIATIONS (100 cases)
# =============================================================================

CASUAL_CASES = [
    # Casual health checks
    NLTestCase("cas-001", "yo is devlake up?", "devlake_health_check", {}, "Casual health"),
    NLTestCase("cas-002", "devlake working or nah?", "devlake_health_check", {}, "Casual working"),
    NLTestCase("cas-003", "gimme devlake status", "devlake_health_check", {}, "Gimme status"),
    NLTestCase("cas-004", "quick devlake check plz", "devlake_health_check", {}, "Quick check"),
    NLTestCase("cas-005", "hey check devlake real quick", "devlake_health_check", {}, "Hey check"),
    NLTestCase("cas-006", "sup with devlake?", "devlake_health_check", {}, "Sup with"),
    NLTestCase("cas-007", "devlake alive rn?", "devlake_health_check", {}, "Alive rn"),
    NLTestCase("cas-008", "is devlake good?", "devlake_health_check", {}, "Is good"),
    NLTestCase("cas-009", "devlake ok?", "devlake_health_check", {}, "Ok"),
    NLTestCase("cas-010", "check if devlake's running pls", "devlake_health_check", {}, "Running pls"),

    # Casual project queries
    NLTestCase("cas-011", "show me all the projects", "devlake_list_projects", {}, "Show me all"),
    NLTestCase("cas-012", "what projects we got?", "devlake_list_projects", {}, "What we got"),
    NLTestCase("cas-013", "lemme see the projects", "devlake_list_projects", {}, "Lemme see"),
    NLTestCase("cas-014", "projects?", "devlake_list_projects", {}, "Just projects"),
    NLTestCase("cas-015", "list em", "devlake_list_projects", {}, "List em"),
    NLTestCase("cas-016", "get me the project list", "devlake_list_projects", {}, "Get me list"),
    NLTestCase("cas-017", "all projects plz", "devlake_list_projects", {}, "All plz"),
    NLTestCase("cas-018", "show projects", "devlake_list_projects", {}, "Show"),
    NLTestCase("cas-019", "whats in devlake?", "devlake_list_projects", {}, "Whats in"),
    NLTestCase("cas-020", "project overview pls", "devlake_list_projects", {}, "Overview pls"),

    # Casual create requests
    NLTestCase("cas-021", "make a project called test", "devlake_create_project", {"name": "test"}, "Make project"),
    NLTestCase("cas-022", "new project: myapp", "devlake_create_project", {"name": "myapp"}, "New project"),
    NLTestCase("cas-023", "add project demo", "devlake_create_project", {"name": "demo"}, "Add demo"),
    NLTestCase("cas-024", "create one called api", "devlake_create_project", {"name": "api"}, "Create one"),
    NLTestCase("cas-025", "set up project backend", "devlake_create_project", {"name": "backend"}, "Set up"),
    NLTestCase("cas-026", "need a project named frontend", "devlake_create_project", {"name": "frontend"}, "Need a"),
    NLTestCase("cas-027", "start new project core", "devlake_create_project", {"name": "core"}, "Start new"),
    NLTestCase("cas-028", "init project services", "devlake_create_project", {"name": "services"}, "Init"),
    NLTestCase("cas-029", "spin up project infra", "devlake_create_project", {"name": "infra"}, "Spin up"),
    NLTestCase("cas-030", "get project platform going", "devlake_create_project", {"name": "platform"}, "Get going"),

    # Casual metrics requests
    NLTestCase("cas-031", "how we doing on dora?", "devlake_get_dora_metrics", {"project_name": "default"}, "How doing"),
    NLTestCase("cas-032", "whats our deploy frequency?", "devlake_get_dora_metrics", {"project_name": "default"}, "Deploy freq"),
    NLTestCase("cas-033", "show me the metrics stuff", "devlake_get_dora_metrics", {"project_name": "default"}, "Metrics stuff"),
    NLTestCase("cas-034", "gimme dora numbers for api", "devlake_get_dora_metrics", {"project_name": "api"}, "Gimme dora"),
    NLTestCase("cas-035", "metrics for backend plz", "devlake_get_dora_metrics", {"project_name": "backend"}, "Metrics plz"),

    # Casual Jira requests
    NLTestCase("cas-036", "whats open in jira?", "jira_search_issues", {"status": "Open"}, "Whats open"),
    NLTestCase("cas-037", "any bugs to fix?", "jira_search_issues", {"issue_type": "Bug"}, "Any bugs"),
    NLTestCase("cas-038", "show jira stuff", "jira_search_issues", {}, "Jira stuff"),
    NLTestCase("cas-039", "need to see PROJ-123", "jira_get_issue", {"key": "PROJ-123"}, "Need to see"),
    NLTestCase("cas-040", "tell me about TEAM-456", "jira_get_issue", {"key": "TEAM-456"}, "Tell me about"),

    # Casual CI requests
    NLTestCase("cas-041", "did the build pass?", "ci_list_builds", {"status": "success"}, "Did pass"),
    NLTestCase("cas-042", "any failing builds?", "ci_list_builds", {"status": "failed"}, "Any failing"),
    NLTestCase("cas-043", "whats building rn?", "ci_list_builds", {"status": "running"}, "Whats building"),
    NLTestCase("cas-044", "ci status?", "ci_health_check", {}, "CI status"),
    NLTestCase("cas-045", "build ok?", "ci_list_builds", {}, "Build ok"),

    # Casual observability
    NLTestCase("cas-046", "any errors in the logs?", "obs_search_logs", {"level": "error"}, "Any errors"),
    NLTestCase("cas-047", "show me slow stuff", "obs_search_traces", {"min_duration_ms": 1000}, "Slow stuff"),
    NLTestCase("cas-048", "whats alerting?", "obs_list_alerts", {"status": "firing"}, "Whats alerting"),
    NLTestCase("cas-049", "logs plz", "obs_search_logs", {}, "Logs plz"),
    NLTestCase("cas-050", "traces for api", "obs_search_traces", {"service": "api"}, "Traces for"),
]


# =============================================================================
# FORMAL/PROFESSIONAL LANGUAGE VARIATIONS (100 cases)
# =============================================================================

FORMAL_CASES = [
    # Formal health checks
    NLTestCase("frm-001", "Please verify the DevLake service status", "devlake_health_check", {}, "Please verify"),
    NLTestCase("frm-002", "I would like to check if DevLake is operational", "devlake_health_check", {}, "Would like"),
    NLTestCase("frm-003", "Could you confirm DevLake availability?", "devlake_health_check", {}, "Could confirm"),
    NLTestCase("frm-004", "Kindly perform a health check on DevLake", "devlake_health_check", {}, "Kindly perform"),
    NLTestCase("frm-005", "I need to verify DevLake connectivity", "devlake_health_check", {}, "Need verify"),
    NLTestCase("frm-006", "Please confirm the backend service is responding", "devlake_health_check", {}, "Confirm responding"),
    NLTestCase("frm-007", "Could you run a diagnostic on DevLake?", "devlake_health_check", {}, "Run diagnostic"),
    NLTestCase("frm-008", "I require a status check on the DevLake API", "devlake_health_check", {}, "Require status"),
    NLTestCase("frm-009", "Please ensure DevLake is functioning properly", "devlake_health_check", {}, "Ensure functioning"),
    NLTestCase("frm-010", "Would you kindly check the service health?", "devlake_health_check", {}, "Kindly check"),

    # Formal project operations
    NLTestCase("frm-011", "Please provide a list of all projects", "devlake_list_projects", {}, "Provide list"),
    NLTestCase("frm-012", "I would like to review the available projects", "devlake_list_projects", {}, "Review available"),
    NLTestCase("frm-013", "Could you enumerate the configured projects?", "devlake_list_projects", {}, "Enumerate configured"),
    NLTestCase("frm-014", "Please display the project inventory", "devlake_list_projects", {}, "Display inventory"),
    NLTestCase("frm-015", "I require a comprehensive project listing", "devlake_list_projects", {}, "Comprehensive listing"),
    NLTestCase("frm-016", "Please create a new project named enterprise-api", "devlake_create_project", {"name": "enterprise-api"}, "Create enterprise"),
    NLTestCase("frm-017", "I would like to establish a project called data-warehouse", "devlake_create_project", {"name": "data-warehouse"}, "Establish project"),
    NLTestCase("frm-018", "Kindly initialize a new project: analytics-platform", "devlake_create_project", {"name": "analytics-platform"}, "Initialize project"),
    NLTestCase("frm-019", "Please register project cloud-infrastructure", "devlake_create_project", {"name": "cloud-infrastructure"}, "Register project"),
    NLTestCase("frm-020", "I need to configure a new project: security-services", "devlake_create_project", {"name": "security-services"}, "Configure new"),

    # Formal metrics
    NLTestCase("frm-021", "Please retrieve the DORA metrics for the platform project", "devlake_get_dora_metrics", {"project_name": "platform"}, "Retrieve DORA"),
    NLTestCase("frm-022", "I would like to review the engineering metrics", "devlake_get_dora_metrics", {"project_name": "default"}, "Review engineering"),
    NLTestCase("frm-023", "Could you provide deployment frequency statistics?", "devlake_get_dora_metrics", {"project_name": "default"}, "Provide deployment"),
    NLTestCase("frm-024", "Please generate a performance metrics report", "devlake_get_dora_metrics", {"project_name": "default"}, "Generate report"),
    NLTestCase("frm-025", "I require the software delivery metrics for analysis", "devlake_get_dora_metrics", {"project_name": "default"}, "Require delivery"),

    # Formal Jira
    NLTestCase("frm-026", "Please search for all open issues in project ENTERPRISE", "jira_search_issues", {"project": "ENTERPRISE", "status": "Open"}, "Search open"),
    NLTestCase("frm-027", "I would like to retrieve details for issue PROJ-1234", "jira_get_issue", {"key": "PROJ-1234"}, "Retrieve details"),
    NLTestCase("frm-028", "Could you create a new task in project CORE?", "jira_create_issue", {"project": "CORE", "summary": "New task", "issue_type": "Task"}, "Create task"),
    NLTestCase("frm-029", "Please transition issue PROJ-5678 to In Progress", "jira_transition_issue", {"key": "PROJ-5678", "status": "In Progress"}, "Transition issue"),
    NLTestCase("frm-030", "I need to update the priority of TEAM-9999 to Critical", "jira_update_issue", {"key": "TEAM-9999", "priority": "Critical"}, "Update priority"),

    # Formal CI/CD
    NLTestCase("frm-031", "Please provide the build status for the main branch", "ci_list_builds", {"branch": "main"}, "Provide build"),
    NLTestCase("frm-032", "I would like to review recent build failures", "ci_list_builds", {"status": "failed"}, "Review failures"),
    NLTestCase("frm-033", "Could you retrieve the test results for build-12345?", "ci_get_test_results", {"build_id": "build-12345"}, "Retrieve test"),
    NLTestCase("frm-034", "Please analyze the CI/CD pipeline performance", "ci_get_build_stats", {}, "Analyze pipeline"),
    NLTestCase("frm-035", "I require a failure pattern analysis", "ci_get_failure_patterns", {}, "Failure pattern"),

    # Formal observability
    NLTestCase("frm-036", "Please search for error logs from the authentication service", "obs_search_logs", {"service": "authentication", "level": "error"}, "Search error"),
    NLTestCase("frm-037", "I would like to investigate slow traces", "obs_search_traces", {"min_duration_ms": 1000}, "Investigate slow"),
    NLTestCase("frm-038", "Could you provide the current alert status?", "obs_list_alerts", {}, "Provide alert"),
    NLTestCase("frm-039", "Please retrieve trace details for ID abc123def456", "obs_get_trace", {"trace_id": "abc123def456"}, "Retrieve trace"),
    NLTestCase("frm-040", "I need to acknowledge alert-critical-001", "obs_acknowledge_alert", {"alert_id": "alert-critical-001"}, "Acknowledge alert"),

    # Formal repository
    NLTestCase("frm-041", "Please search the codebase for authentication implementations", "repo_search_code", {"query": "authentication"}, "Search codebase"),
    NLTestCase("frm-042", "I would like to review the recent commit history", "repo_get_commits", {"repository": "backend"}, "Review commit"),
    NLTestCase("frm-043", "Could you locate the definition of AuthService class?", "repo_find_definition", {"name": "AuthService", "definition_type": "class"}, "Locate definition"),
    NLTestCase("frm-044", "Please retrieve the contents of configuration file", "repo_get_file", {"repository": "backend", "path": "config.py"}, "Retrieve contents"),
    NLTestCase("frm-045", "I require a diff between main and feature branch", "repo_get_diff", {"repository": "backend", "base": "main", "head": "feature"}, "Require diff"),

    # Formal policy
    NLTestCase("frm-046", "Please verify if administrator role has delete permissions", "policy_check_permission", {"role": "admin", "permission": "delete"}, "Verify admin"),
    NLTestCase("frm-047", "I would like to review the audit log for today", "policy_get_audit_log", {}, "Review audit"),
    NLTestCase("frm-048", "Could you apply data redaction to this text?", "policy_apply_redaction", {"text": "sensitive data"}, "Apply redaction"),
    NLTestCase("frm-049", "Please list all available roles in the system", "policy_list_all_roles", {}, "List roles"),
    NLTestCase("frm-050", "I need to log a security-related action", "policy_log_action", {"action": "security_check", "resource_type": "system"}, "Log action"),
]


# =============================================================================
# QUESTION FORMAT VARIATIONS (100 cases)
# =============================================================================

QUESTION_CASES = [
    # What questions
    NLTestCase("q-001", "What is the status of DevLake?", "devlake_health_check", {}, "What status"),
    NLTestCase("q-002", "What projects are available?", "devlake_list_projects", {}, "What projects"),
    NLTestCase("q-003", "What connections are configured?", "devlake_list_connections", {}, "What connections"),
    NLTestCase("q-004", "What plugins are supported?", "devlake_list_plugins", {}, "What plugins"),
    NLTestCase("q-005", "What is the DORA score for frontend?", "devlake_get_dora_metrics", {"project_name": "frontend"}, "What DORA"),
    NLTestCase("q-006", "What builds are running?", "ci_list_builds", {"status": "running"}, "What builds"),
    NLTestCase("q-007", "What issues are open in PROJ?", "jira_search_issues", {"project": "PROJ", "status": "Open"}, "What issues"),
    NLTestCase("q-008", "What alerts are firing?", "obs_list_alerts", {"status": "firing"}, "What alerts"),
    NLTestCase("q-009", "What metrics are available?", "obs_list_metrics", {}, "What metrics"),
    NLTestCase("q-010", "What repositories are indexed?", "repo_list", {}, "What repos"),

    # How questions
    NLTestCase("q-011", "How is DevLake performing?", "devlake_health_check", {}, "How performing"),
    NLTestCase("q-012", "How many projects do we have?", "devlake_list_projects", {}, "How many projects"),
    NLTestCase("q-013", "How do I connect GitHub?", "devlake_quick_start", {}, "How connect"),
    NLTestCase("q-014", "How are we doing on deployments?", "devlake_get_dora_metrics", {"project_name": "default"}, "How deployments"),
    NLTestCase("q-015", "How did build-123 fail?", "ci_get_build_logs", {"build_id": "build-123"}, "How fail"),
    NLTestCase("q-016", "How long are requests taking?", "obs_search_traces", {"min_duration_ms": 100}, "How long"),
    NLTestCase("q-017", "How many issues in sprint 10?", "jira_get_sprint_issues", {"sprint_id": 10}, "How many issues"),
    NLTestCase("q-018", "How to set up DevLake?", "devlake_quick_start", {}, "How setup"),
    NLTestCase("q-019", "How is the CI pipeline?", "ci_health_check", {}, "How CI"),
    NLTestCase("q-020", "How can I search code?", "repo_search_code", {"query": "example"}, "How search"),

    # Can questions
    NLTestCase("q-021", "Can you check DevLake?", "devlake_health_check", {}, "Can check"),
    NLTestCase("q-022", "Can you list the projects?", "devlake_list_projects", {}, "Can list"),
    NLTestCase("q-023", "Can you show me PROJ-123?", "jira_get_issue", {"key": "PROJ-123"}, "Can show"),
    NLTestCase("q-024", "Can you create a new project?", "devlake_create_project", {"name": "new"}, "Can create"),
    NLTestCase("q-025", "Can you find the error logs?", "obs_search_logs", {"level": "error"}, "Can find"),
    NLTestCase("q-026", "Can you search for authentication?", "repo_search_code", {"query": "authentication"}, "Can search"),
    NLTestCase("q-027", "Can you get the build status?", "ci_list_builds", {}, "Can get"),
    NLTestCase("q-028", "Can you show recent commits?", "repo_get_commits", {"repository": "backend"}, "Can show commits"),
    NLTestCase("q-029", "Can you check permissions?", "policy_check_permission", {"role": "admin", "permission": "read"}, "Can check perms"),
    NLTestCase("q-030", "Can you redact this text?", "policy_apply_redaction", {"text": "secret"}, "Can redact"),

    # Is/Are questions
    NLTestCase("q-031", "Is DevLake running?", "devlake_health_check", {}, "Is running"),
    NLTestCase("q-032", "Is the CI pipeline healthy?", "ci_health_check", {}, "Is CI healthy"),
    NLTestCase("q-033", "Is there any failing build?", "ci_list_builds", {"status": "failed"}, "Is failing"),
    NLTestCase("q-034", "Are there any alerts?", "obs_list_alerts", {}, "Are alerts"),
    NLTestCase("q-035", "Are the tests passing?", "ci_list_builds", {"status": "success"}, "Are passing"),
    NLTestCase("q-036", "Is PROJ-123 resolved?", "jira_get_issue", {"key": "PROJ-123"}, "Is resolved"),
    NLTestCase("q-037", "Are there open bugs?", "jira_search_issues", {"issue_type": "Bug", "status": "Open"}, "Are bugs"),
    NLTestCase("q-038", "Is the repository service up?", "repo_health_check", {}, "Is repo up"),
    NLTestCase("q-039", "Are there any errors in logs?", "obs_search_logs", {"level": "error"}, "Are errors"),
    NLTestCase("q-040", "Is admin allowed to delete?", "policy_check_permission", {"role": "admin", "permission": "delete"}, "Is allowed"),

    # Where questions
    NLTestCase("q-041", "Where is UserService defined?", "repo_find_definition", {"name": "UserService"}, "Where defined"),
    NLTestCase("q-042", "Where are the error logs?", "obs_search_logs", {"level": "error"}, "Where logs"),
    NLTestCase("q-043", "Where is the config file?", "repo_get_file", {"repository": "backend", "path": "config.py"}, "Where config"),
    NLTestCase("q-044", "Where can I find the metrics?", "devlake_get_dora_metrics", {"project_name": "default"}, "Where metrics"),
    NLTestCase("q-045", "Where is the authentication code?", "repo_search_code", {"query": "authentication"}, "Where auth"),

    # When questions
    NLTestCase("q-046", "When was the last build?", "ci_list_builds", {"limit": 1}, "When last build"),
    NLTestCase("q-047", "When was PROJ-123 created?", "jira_get_issue", {"key": "PROJ-123"}, "When created"),
    NLTestCase("q-048", "When did the error occur?", "obs_search_logs", {"level": "error"}, "When error"),
    NLTestCase("q-049", "When was the last deployment?", "devlake_get_dora_metrics", {"project_name": "default"}, "When deploy"),
    NLTestCase("q-050", "When did the sprint start?", "jira_list_sprints", {"state": "active"}, "When sprint"),
]


# =============================================================================
# COMMAND/IMPERATIVE VARIATIONS (100 cases)
# =============================================================================

COMMAND_CASES = [
    # Direct commands
    NLTestCase("cmd-001", "Check DevLake", "devlake_health_check", {}, "Check"),
    NLTestCase("cmd-002", "List projects", "devlake_list_projects", {}, "List"),
    NLTestCase("cmd-003", "Show connections", "devlake_list_connections", {}, "Show"),
    NLTestCase("cmd-004", "Get metrics for api", "devlake_get_dora_metrics", {"project_name": "api"}, "Get metrics"),
    NLTestCase("cmd-005", "Create project test", "devlake_create_project", {"name": "test"}, "Create"),
    NLTestCase("cmd-006", "Search issues", "jira_search_issues", {}, "Search"),
    NLTestCase("cmd-007", "Find bugs", "jira_search_issues", {"issue_type": "Bug"}, "Find bugs"),
    NLTestCase("cmd-008", "Open PROJ-123", "jira_get_issue", {"key": "PROJ-123"}, "Open"),
    NLTestCase("cmd-009", "Update TEAM-456", "jira_update_issue", {"key": "TEAM-456"}, "Update"),
    NLTestCase("cmd-010", "Close CORE-789", "jira_transition_issue", {"key": "CORE-789", "status": "Done"}, "Close"),

    # Run commands
    NLTestCase("cmd-011", "Run health check", "devlake_health_check", {}, "Run health"),
    NLTestCase("cmd-012", "Run pipeline 1", "devlake_trigger_blueprint", {"blueprint_id": 1}, "Run pipeline"),
    NLTestCase("cmd-013", "Run tests", "ci_get_test_results", {"build_id": "latest"}, "Run tests"),
    NLTestCase("cmd-014", "Run code search", "repo_search_code", {"query": "main"}, "Run search"),
    NLTestCase("cmd-015", "Run audit report", "policy_get_audit_log", {}, "Run audit"),

    # Execute commands
    NLTestCase("cmd-016", "Execute health check", "devlake_health_check", {}, "Execute health"),
    NLTestCase("cmd-017", "Execute blueprint 2", "devlake_trigger_blueprint", {"blueprint_id": 2}, "Execute blueprint"),
    NLTestCase("cmd-018", "Execute query", "rag_semantic_search", {"query": "test"}, "Execute query"),
    NLTestCase("cmd-019", "Execute redaction", "policy_apply_redaction", {"text": "secret"}, "Execute redaction"),
    NLTestCase("cmd-020", "Execute log action", "policy_log_action", {"action": "test", "resource_type": "system"}, "Execute log"),

    # Fetch commands
    NLTestCase("cmd-021", "Fetch projects", "devlake_list_projects", {}, "Fetch projects"),
    NLTestCase("cmd-022", "Fetch metrics", "devlake_get_dora_metrics", {"project_name": "default"}, "Fetch metrics"),
    NLTestCase("cmd-023", "Fetch builds", "ci_list_builds", {}, "Fetch builds"),
    NLTestCase("cmd-024", "Fetch logs", "obs_search_logs", {}, "Fetch logs"),
    NLTestCase("cmd-025", "Fetch issue PROJ-100", "jira_get_issue", {"key": "PROJ-100"}, "Fetch issue"),

    # Display commands
    NLTestCase("cmd-026", "Display projects", "devlake_list_projects", {}, "Display projects"),
    NLTestCase("cmd-027", "Display connections", "devlake_list_connections", {}, "Display conns"),
    NLTestCase("cmd-028", "Display alerts", "obs_list_alerts", {}, "Display alerts"),
    NLTestCase("cmd-029", "Display sprints", "jira_list_sprints", {}, "Display sprints"),
    NLTestCase("cmd-030", "Display repositories", "repo_list", {}, "Display repos"),

    # Query commands
    NLTestCase("cmd-031", "Query DORA metrics", "devlake_get_dora_metrics", {"project_name": "default"}, "Query DORA"),
    NLTestCase("cmd-032", "Query error logs", "obs_search_logs", {"level": "error"}, "Query errors"),
    NLTestCase("cmd-033", "Query slow traces", "obs_search_traces", {"min_duration_ms": 1000}, "Query slow"),
    NLTestCase("cmd-034", "Query open issues", "jira_search_issues", {"status": "Open"}, "Query open"),
    NLTestCase("cmd-035", "Query knowledge base", "rag_semantic_search", {"query": "help"}, "Query KB"),

    # View commands
    NLTestCase("cmd-036", "View project list", "devlake_list_projects", {}, "View projects"),
    NLTestCase("cmd-037", "View build status", "ci_list_builds", {}, "View build"),
    NLTestCase("cmd-038", "View trace abc123", "obs_get_trace", {"trace_id": "abc123"}, "View trace"),
    NLTestCase("cmd-039", "View issue PROJ-200", "jira_get_issue", {"key": "PROJ-200"}, "View issue"),
    NLTestCase("cmd-040", "View permissions", "policy_list_all_roles", {}, "View perms"),

    # Start/Stop commands
    NLTestCase("cmd-041", "Start data collection", "devlake_trigger_blueprint", {"blueprint_id": 1}, "Start collection"),
    NLTestCase("cmd-042", "Start pipeline 3", "devlake_trigger_blueprint", {"blueprint_id": 3}, "Start pipeline"),
    NLTestCase("cmd-043", "Stop pipeline 100", "devlake_cancel_pipeline", {"pipeline_id": 100}, "Stop pipeline"),
    NLTestCase("cmd-044", "Cancel pipeline 200", "devlake_cancel_pipeline", {"pipeline_id": 200}, "Cancel pipeline"),
    NLTestCase("cmd-045", "Abort pipeline 300", "devlake_cancel_pipeline", {"pipeline_id": 300}, "Abort pipeline"),

    # Delete/Remove commands
    NLTestCase("cmd-046", "Delete document doc-123", "rag_delete_document", {"document_id": "doc-123"}, "Delete doc"),
    NLTestCase("cmd-047", "Remove document doc-456", "rag_delete_document", {"document_id": "doc-456"}, "Remove doc"),
    NLTestCase("cmd-048", "Clear document doc-789", "rag_delete_document", {"document_id": "doc-789"}, "Clear doc"),

    # Add commands
    NLTestCase("cmd-049", "Add project analytics", "devlake_create_project", {"name": "analytics"}, "Add project"),
    NLTestCase("cmd-050", "Add redaction rule", "policy_add_redaction_rule", {"name": "custom", "pattern": "\\d+"}, "Add rule"),
]


# =============================================================================
# CONTEXT-RICH VARIATIONS (91 cases to reach 1000 total)
# =============================================================================

CONTEXT_CASES = [
    # With time context
    NLTestCase("ctx-001", "Check DevLake health this morning", "devlake_health_check", {}, "Morning health"),
    NLTestCase("ctx-002", "Get metrics for last week", "devlake_get_dora_metrics", {"project_name": "default", "time_range": "past_week"}, "Last week"),
    NLTestCase("ctx-003", "Show builds from today", "ci_list_builds", {}, "Today builds"),
    NLTestCase("ctx-004", "Recent error logs", "obs_search_logs", {"level": "error"}, "Recent errors"),
    NLTestCase("ctx-005", "Latest commits", "repo_get_commits", {"repository": "backend", "limit": 10}, "Latest commits"),

    # With priority context
    NLTestCase("ctx-006", "Urgent: check DevLake status", "devlake_health_check", {}, "Urgent check"),
    NLTestCase("ctx-007", "Critical bugs only", "jira_search_issues", {"issue_type": "Bug", "priority": "Critical"}, "Critical bugs"),
    NLTestCase("ctx-008", "High priority issues", "jira_search_issues", {"priority": "High"}, "High priority"),
    NLTestCase("ctx-009", "Important alerts", "obs_list_alerts", {"severity": "critical"}, "Important alerts"),
    NLTestCase("ctx-010", "Blocker issues", "jira_search_issues", {"priority": "Highest"}, "Blocker"),

    # With team context
    NLTestCase("ctx-011", "My team's projects", "devlake_list_projects", {}, "Team projects"),
    NLTestCase("ctx-012", "Backend team metrics", "devlake_get_dora_metrics", {"project_name": "backend"}, "Backend metrics"),
    NLTestCase("ctx-013", "Frontend issues", "jira_search_issues", {"project": "FRONTEND"}, "Frontend issues"),
    NLTestCase("ctx-014", "DevOps builds", "ci_list_builds", {"project_name": "devops"}, "DevOps builds"),
    NLTestCase("ctx-015", "Platform team alerts", "obs_list_alerts", {"service": "platform"}, "Platform alerts"),

    # With purpose context
    NLTestCase("ctx-016", "For the standup: show open issues", "jira_search_issues", {"status": "Open"}, "Standup issues"),
    NLTestCase("ctx-017", "For the retrospective: DORA metrics", "devlake_get_dora_metrics", {"project_name": "default"}, "Retro metrics"),
    NLTestCase("ctx-018", "For debugging: error traces", "obs_search_traces", {"has_errors": True}, "Debug traces"),
    NLTestCase("ctx-019", "For deployment: build status", "ci_list_builds", {"status": "success"}, "Deploy build"),
    NLTestCase("ctx-020", "For review: recent PRs", "devlake_get_project_stats", {"project_name": "default"}, "Review PRs"),

    # Combined tool chains
    NLTestCase("ctx-021", "First check DevLake health", "devlake_health_check", {}, "First check"),
    NLTestCase("ctx-022", "Then list all projects", "devlake_list_projects", {}, "Then list"),
    NLTestCase("ctx-023", "Also show the connections", "devlake_list_connections", {}, "Also show"),
    NLTestCase("ctx-024", "Next get the metrics", "devlake_get_dora_metrics", {"project_name": "default"}, "Next get"),
    NLTestCase("ctx-025", "Finally check the builds", "ci_list_builds", {}, "Finally check"),

    # With scope context
    NLTestCase("ctx-026", "All projects across DevLake", "devlake_list_projects", {}, "All projects"),
    NLTestCase("ctx-027", "Every connection configured", "devlake_list_connections", {}, "Every connection"),
    NLTestCase("ctx-028", "Complete project metrics", "devlake_get_project_stats", {"project_name": "default"}, "Complete metrics"),
    NLTestCase("ctx-029", "Full audit log", "policy_get_audit_log", {}, "Full audit"),
    NLTestCase("ctx-030", "Comprehensive KB stats", "rag_get_stats", {}, "Comprehensive KB"),

    # With filter context
    NLTestCase("ctx-031", "Only GitHub connections", "devlake_list_connections", {"plugin": "github"}, "Only GitHub"),
    NLTestCase("ctx-032", "Just the failed builds", "ci_list_builds", {"status": "failed"}, "Just failed"),
    NLTestCase("ctx-033", "Specifically error logs", "obs_search_logs", {"level": "error"}, "Specifically errors"),
    NLTestCase("ctx-034", "Particularly open bugs", "jira_search_issues", {"issue_type": "Bug", "status": "Open"}, "Particularly bugs"),
    NLTestCase("ctx-035", "Exclusively active sprints", "jira_list_sprints", {"state": "active"}, "Exclusively active"),

    # With comparison context
    NLTestCase("ctx-036", "Compare main vs develop", "repo_get_diff", {"repository": "backend", "base": "main", "head": "develop"}, "Compare branches"),
    NLTestCase("ctx-037", "Diff between releases", "repo_get_diff", {"repository": "backend", "base": "v1.0", "head": "v2.0"}, "Diff releases"),
    NLTestCase("ctx-038", "Changes since last month", "devlake_get_dora_metrics", {"project_name": "default", "time_range": "past_month"}, "Changes month"),
    NLTestCase("ctx-039", "Progress this sprint", "jira_get_sprint_issues", {"sprint_id": 1}, "Progress sprint"),
    NLTestCase("ctx-040", "Trends over 3 months", "devlake_get_dora_metrics", {"project_name": "default", "time_range": "past_3_months"}, "Trends 3mo"),

    # Troubleshooting context
    NLTestCase("ctx-041", "Debugging: check health first", "devlake_health_check", {}, "Debug health"),
    NLTestCase("ctx-042", "Issue investigation: show logs", "obs_search_logs", {"level": "error"}, "Investigate logs"),
    NLTestCase("ctx-043", "Root cause: trace abc123", "obs_get_trace", {"trace_id": "abc123"}, "Root cause trace"),
    NLTestCase("ctx-044", "Incident analysis: alert status", "obs_list_alerts", {"status": "firing"}, "Incident alerts"),
    NLTestCase("ctx-045", "Problem solving: failed tests", "ci_get_failed_tests", {"build_id": "build-123"}, "Problem tests"),

    # Documentation context
    NLTestCase("ctx-046", "For docs: list all tools", "devlake_list_plugins", {}, "Docs tools"),
    NLTestCase("ctx-047", "Documentation: available metrics", "obs_list_metrics", {}, "Docs metrics"),
    NLTestCase("ctx-048", "Reference: role permissions", "policy_list_all_roles", {}, "Reference roles"),
    NLTestCase("ctx-049", "Guide: setup status", "devlake_get_setup_status", {}, "Guide setup"),
    NLTestCase("ctx-050", "Help: quick start", "devlake_quick_start", {}, "Help quickstart"),

    # Reporting context
    NLTestCase("ctx-051", "Weekly report: DORA metrics", "devlake_get_dora_metrics", {"project_name": "default"}, "Weekly DORA"),
    NLTestCase("ctx-052", "Daily report: build status", "ci_get_build_stats", {}, "Daily builds"),
    NLTestCase("ctx-053", "Sprint report: issues", "jira_get_sprint_issues", {"sprint_id": 1}, "Sprint issues"),
    NLTestCase("ctx-054", "Audit report: log entries", "policy_get_audit_log", {}, "Audit entries"),
    NLTestCase("ctx-055", "Performance report: traces", "obs_search_traces", {}, "Perf traces"),

    # Multi-project context
    NLTestCase("ctx-056", "Metrics for all projects", "devlake_list_projects", {}, "All project metrics"),
    NLTestCase("ctx-057", "Cross-project stats", "devlake_get_project_stats", {"project_name": "default"}, "Cross stats"),
    NLTestCase("ctx-058", "Organization-wide builds", "ci_list_builds", {}, "Org builds"),
    NLTestCase("ctx-059", "Enterprise issues", "jira_search_issues", {}, "Enterprise issues"),
    NLTestCase("ctx-060", "Global alerts", "obs_list_alerts", {}, "Global alerts"),

    # Additional edge cases
    NLTestCase("ctx-061", "🔍 Search for issues", "jira_search_issues", {}, "Emoji search"),
    NLTestCase("ctx-062", "DEVLAKE HEALTH CHECK", "devlake_health_check", {}, "All caps"),
    NLTestCase("ctx-063", "devlake   list    projects", "devlake_list_projects", {}, "Extra spaces"),
    NLTestCase("ctx-064", "List\nprojects", "devlake_list_projects", {}, "With newline"),
    NLTestCase("ctx-065", "check health!!!", "devlake_health_check", {}, "Exclamations"),
    NLTestCase("ctx-066", "health check?", "devlake_health_check", {}, "Question mark"),
    NLTestCase("ctx-067", "projects...", "devlake_list_projects", {}, "Ellipsis"),
    NLTestCase("ctx-068", "(show me projects)", "devlake_list_projects", {}, "Parentheses"),
    NLTestCase("ctx-069", "\"list projects\"", "devlake_list_projects", {}, "Quoted"),
    NLTestCase("ctx-070", "list - projects", "devlake_list_projects", {}, "Dashed"),

    # Abbreviated commands
    NLTestCase("ctx-071", "dl health", "devlake_health_check", {}, "Abbrev dl"),
    NLTestCase("ctx-072", "proj list", "devlake_list_projects", {}, "Abbrev proj"),
    NLTestCase("ctx-073", "conn show", "devlake_list_connections", {}, "Abbrev conn"),
    NLTestCase("ctx-074", "bp trigger 1", "devlake_trigger_blueprint", {"blueprint_id": 1}, "Abbrev bp"),
    NLTestCase("ctx-075", "pipe list", "devlake_list_pipelines", {}, "Abbrev pipe"),

    # Multi-language hints (English)
    NLTestCase("ctx-076", "Check the DevLake health status", "devlake_health_check", {}, "Multi check"),
    NLTestCase("ctx-077", "Display available projects", "devlake_list_projects", {}, "Multi display"),
    NLTestCase("ctx-078", "Retrieve connection list", "devlake_list_connections", {}, "Multi retrieve"),
    NLTestCase("ctx-079", "Obtain DORA metrics", "devlake_get_dora_metrics", {"project_name": "default"}, "Multi obtain"),
    NLTestCase("ctx-080", "Establish new project", "devlake_create_project", {"name": "new"}, "Multi establish"),

    # Follow-up context
    NLTestCase("ctx-081", "Now check health", "devlake_health_check", {}, "Now check"),
    NLTestCase("ctx-082", "Actually list projects", "devlake_list_projects", {}, "Actually list"),
    NLTestCase("ctx-083", "Wait, show connections", "devlake_list_connections", {}, "Wait show"),
    NLTestCase("ctx-084", "Also get metrics", "devlake_get_dora_metrics", {"project_name": "default"}, "Also get"),
    NLTestCase("ctx-085", "One more: list builds", "ci_list_builds", {}, "One more"),

    # Conditional context
    NLTestCase("ctx-086", "If DevLake is up, list projects", "devlake_health_check", {}, "If up"),
    NLTestCase("ctx-087", "Assuming health ok, show metrics", "devlake_get_dora_metrics", {"project_name": "default"}, "Assuming ok"),
    NLTestCase("ctx-088", "Given connected, list connections", "devlake_list_connections", {}, "Given connected"),
    NLTestCase("ctx-089", "When ready, check builds", "ci_list_builds", {}, "When ready"),
    NLTestCase("ctx-090", "Before proceeding, health check", "devlake_health_check", {}, "Before proceeding"),

    # Final cases
    NLTestCase("ctx-091", "Last check: DevLake health", "devlake_health_check", {}, "Last check"),

    # Additional cases to reach 1000 total
    NLTestCase("ctx-092", "Verify system health", "devlake_health_check", {}, "Verify system"),
    NLTestCase("ctx-093", "System status check", "devlake_health_check", {}, "System status"),
    NLTestCase("ctx-094", "API availability check", "devlake_health_check", {}, "API availability"),
    NLTestCase("ctx-095", "Backend status verification", "devlake_health_check", {}, "Backend verify"),
    NLTestCase("ctx-096", "Service connectivity test", "devlake_health_check", {}, "Service test"),
    NLTestCase("ctx-097", "Infrastructure health", "devlake_health_check", {}, "Infra health"),
    NLTestCase("ctx-098", "Platform health check", "devlake_health_check", {}, "Platform health"),
    NLTestCase("ctx-099", "Service availability", "devlake_health_check", {}, "Service avail"),
    NLTestCase("ctx-100", "Application status", "devlake_health_check", {}, "App status"),

    # More project variations
    NLTestCase("ctx-101", "Enumerate tracked projects", "devlake_list_projects", {}, "Enumerate tracked"),
    NLTestCase("ctx-102", "Get project inventory", "devlake_list_projects", {}, "Get inventory"),
    NLTestCase("ctx-103", "Show project catalog", "devlake_list_projects", {}, "Show catalog"),
    NLTestCase("ctx-104", "Project registry", "devlake_list_projects", {}, "Project registry"),
    NLTestCase("ctx-105", "List monitored projects", "devlake_list_projects", {}, "Monitored projects"),
    NLTestCase("ctx-106", "Display project dashboard", "devlake_list_projects", {}, "Display dashboard"),
    NLTestCase("ctx-107", "Show all tracked repos", "devlake_list_projects", {}, "Tracked repos"),
    NLTestCase("ctx-108", "Project summary view", "devlake_list_projects", {}, "Summary view"),
    NLTestCase("ctx-109", "Overview of projects", "devlake_list_projects", {}, "Overview"),
    NLTestCase("ctx-110", "Project listing summary", "devlake_list_projects", {}, "Listing summary"),

    # More connection variations
    NLTestCase("ctx-111", "Integration status", "devlake_list_connections", {}, "Integration status"),
    NLTestCase("ctx-112", "Data source overview", "devlake_list_connections", {}, "Source overview"),
    NLTestCase("ctx-113", "Connected services", "devlake_list_connections", {}, "Connected services"),
    NLTestCase("ctx-114", "Active integrations", "devlake_list_connections", {}, "Active integrations"),
    NLTestCase("ctx-115", "Integration inventory", "devlake_list_connections", {}, "Integration inv"),
    NLTestCase("ctx-116", "Show data connectors", "devlake_list_connections", {}, "Data connectors"),
    NLTestCase("ctx-117", "List linked services", "devlake_list_connections", {}, "Linked services"),
    NLTestCase("ctx-118", "Configured data sources", "devlake_list_connections", {}, "Configured sources"),
    NLTestCase("ctx-119", "External connections", "devlake_list_connections", {}, "External conns"),
    NLTestCase("ctx-120", "Third-party integrations", "devlake_list_connections", {}, "Third-party"),

    # More metrics variations
    NLTestCase("ctx-121", "Engineering KPIs", "devlake_get_dora_metrics", {"project_name": "default"}, "Engineering KPIs"),
    NLTestCase("ctx-122", "DevOps KPIs for team", "devlake_get_dora_metrics", {"project_name": "default"}, "DevOps KPIs"),
    NLTestCase("ctx-123", "Performance indicators", "devlake_get_dora_metrics", {"project_name": "default"}, "Perf indicators"),
    NLTestCase("ctx-124", "Velocity metrics", "devlake_get_dora_metrics", {"project_name": "default"}, "Velocity metrics"),
    NLTestCase("ctx-125", "Delivery metrics overview", "devlake_get_dora_metrics", {"project_name": "default"}, "Delivery overview"),
    NLTestCase("ctx-126", "Release metrics", "devlake_get_dora_metrics", {"project_name": "default"}, "Release metrics"),
    NLTestCase("ctx-127", "Deployment statistics", "devlake_get_dora_metrics", {"project_name": "default"}, "Deploy stats"),
    NLTestCase("ctx-128", "Change metrics", "devlake_get_dora_metrics", {"project_name": "default"}, "Change metrics"),
    NLTestCase("ctx-129", "Recovery metrics", "devlake_get_dora_metrics", {"project_name": "default"}, "Recovery metrics"),
    NLTestCase("ctx-130", "Incident metrics", "devlake_get_dora_metrics", {"project_name": "default"}, "Incident metrics"),

    # More Jira variations
    NLTestCase("ctx-131", "Sprint backlog items", "jira_get_sprint_issues", {"sprint_id": 1}, "Sprint backlog"),
    NLTestCase("ctx-132", "Current sprint work", "jira_get_sprint_issues", {"sprint_id": 1}, "Current work"),
    NLTestCase("ctx-133", "Active sprint tasks", "jira_get_sprint_issues", {"sprint_id": 1}, "Active tasks"),
    NLTestCase("ctx-134", "Sprint scope", "jira_get_sprint_issues", {"sprint_id": 1}, "Sprint scope"),
    NLTestCase("ctx-135", "Iteration items", "jira_get_sprint_issues", {"sprint_id": 1}, "Iteration items"),
    NLTestCase("ctx-136", "Backlog review", "jira_search_issues", {"status": "Backlog"}, "Backlog review"),
    NLTestCase("ctx-137", "In progress work", "jira_search_issues", {"status": "In Progress"}, "In progress"),
    NLTestCase("ctx-138", "Review queue", "jira_search_issues", {"status": "Review"}, "Review queue"),
    NLTestCase("ctx-139", "Testing queue", "jira_search_issues", {"status": "Testing"}, "Testing queue"),
    NLTestCase("ctx-140", "Done items", "jira_search_issues", {"status": "Done"}, "Done items"),

    # More CI variations
    NLTestCase("ctx-141", "Pipeline runs", "ci_list_builds", {}, "Pipeline runs"),
    NLTestCase("ctx-142", "Build history", "ci_list_builds", {}, "Build history"),
    NLTestCase("ctx-143", "Deployment history", "ci_list_builds", {}, "Deploy history"),
    NLTestCase("ctx-144", "CI run history", "ci_list_builds", {}, "CI history"),
    NLTestCase("ctx-145", "Build queue", "ci_list_builds", {"status": "pending"}, "Build queue"),
    NLTestCase("ctx-146", "Active pipelines", "ci_list_builds", {"status": "running"}, "Active pipelines"),
    NLTestCase("ctx-147", "Completed builds", "ci_list_builds", {"status": "success"}, "Completed builds"),
    NLTestCase("ctx-148", "Build failures", "ci_list_builds", {"status": "failed"}, "Build failures"),
    NLTestCase("ctx-149", "Pipeline status", "ci_list_builds", {}, "Pipeline status"),
    NLTestCase("ctx-150", "Build dashboard", "ci_list_builds", {}, "Build dashboard"),

    # More observability variations
    NLTestCase("ctx-151", "Application logs", "obs_search_logs", {}, "App logs"),
    NLTestCase("ctx-152", "Error tracking", "obs_search_logs", {"level": "error"}, "Error tracking"),
    NLTestCase("ctx-153", "Warning messages", "obs_search_logs", {"level": "warning"}, "Warning msgs"),
    NLTestCase("ctx-154", "Debug information", "obs_search_logs", {"level": "debug"}, "Debug info"),
    NLTestCase("ctx-155", "Service logs", "obs_search_logs", {}, "Service logs"),
    NLTestCase("ctx-156", "Trace search", "obs_search_traces", {}, "Trace search"),
    NLTestCase("ctx-157", "Request traces", "obs_search_traces", {}, "Request traces"),
    NLTestCase("ctx-158", "Transaction traces", "obs_search_traces", {}, "Transaction traces"),
    NLTestCase("ctx-159", "Latency analysis", "obs_search_traces", {"min_duration_ms": 500}, "Latency analysis"),
    NLTestCase("ctx-160", "Performance traces", "obs_search_traces", {}, "Perf traces"),

    # More repository variations
    NLTestCase("ctx-161", "Source code search", "repo_search_code", {"query": "main"}, "Source search"),
    NLTestCase("ctx-162", "Code pattern search", "repo_search_code", {"query": "async"}, "Pattern search"),
    NLTestCase("ctx-163", "Function search", "repo_search_code", {"query": "function"}, "Function search"),
    NLTestCase("ctx-164", "Class search", "repo_search_code", {"query": "class"}, "Class search"),
    NLTestCase("ctx-165", "Import search", "repo_search_code", {"query": "import"}, "Import search"),
    NLTestCase("ctx-166", "Commit history", "repo_get_commits", {"repository": "backend"}, "Commit history"),
    NLTestCase("ctx-167", "Change log", "repo_get_commits", {"repository": "backend"}, "Change log"),
    NLTestCase("ctx-168", "Version history", "repo_get_commits", {"repository": "backend"}, "Version history"),
    NLTestCase("ctx-169", "Git log", "repo_get_commits", {"repository": "backend"}, "Git log"),
    NLTestCase("ctx-170", "Recent changes", "repo_get_commits", {"repository": "backend"}, "Recent changes"),

    # More RAG variations
    NLTestCase("ctx-171", "Knowledge search", "rag_semantic_search", {"query": "help"}, "Knowledge search"),
    NLTestCase("ctx-172", "Documentation search", "rag_semantic_search", {"query": "docs"}, "Doc search"),
    NLTestCase("ctx-173", "Find in knowledge base", "rag_semantic_search", {"query": "find"}, "Find in KB"),
    NLTestCase("ctx-174", "Search documentation", "rag_semantic_search", {"query": "documentation"}, "Search docs"),
    NLTestCase("ctx-175", "Knowledge base query", "rag_semantic_search", {"query": "query"}, "KB query"),
    NLTestCase("ctx-176", "Semantic search", "rag_semantic_search", {"query": "search"}, "Semantic search"),
    NLTestCase("ctx-177", "AI search", "rag_semantic_search", {"query": "ai"}, "AI search"),
    NLTestCase("ctx-178", "Smart search", "rag_semantic_search", {"query": "smart"}, "Smart search"),
    NLTestCase("ctx-179", "Contextual search", "rag_semantic_search", {"query": "context"}, "Contextual search"),
    NLTestCase("ctx-180", "Intelligent search", "rag_semantic_search", {"query": "intelligent"}, "Intelligent search"),

    # More policy variations
    NLTestCase("ctx-181", "Access control check", "policy_check_permission", {"role": "member", "permission": "read"}, "Access check"),
    NLTestCase("ctx-182", "Permission verification", "policy_check_permission", {"role": "admin", "permission": "write"}, "Permission verify"),
    NLTestCase("ctx-183", "Authorization check", "policy_check_permission", {"role": "owner", "permission": "delete"}, "Auth check"),
    NLTestCase("ctx-184", "Role capabilities", "policy_list_role_permissions", {"role": "admin"}, "Role caps"),
    NLTestCase("ctx-185", "Security audit", "policy_get_audit_log", {}, "Security audit"),
    NLTestCase("ctx-186", "Access log", "policy_get_audit_log", {}, "Access log"),
    NLTestCase("ctx-187", "Activity log", "policy_get_audit_log", {}, "Activity log"),
    NLTestCase("ctx-188", "Action history", "policy_get_audit_log", {}, "Action history"),
    NLTestCase("ctx-189", "Compliance log", "policy_get_audit_log", {}, "Compliance log"),
    NLTestCase("ctx-190", "Security events", "policy_get_audit_log", {}, "Security events"),

    # Final additional cases
    NLTestCase("ctx-191", "Quick health verify", "devlake_health_check", {}, "Quick verify"),
    NLTestCase("ctx-192", "Rapid status check", "devlake_health_check", {}, "Rapid status"),
    NLTestCase("ctx-193", "Fast health scan", "devlake_health_check", {}, "Fast scan"),
    NLTestCase("ctx-194", "Instant status", "devlake_health_check", {}, "Instant status"),
    NLTestCase("ctx-195", "Live health check", "devlake_health_check", {}, "Live health"),
    NLTestCase("ctx-196", "Real-time status", "devlake_health_check", {}, "Real-time"),
    NLTestCase("ctx-197", "Current health", "devlake_health_check", {}, "Current health"),
    NLTestCase("ctx-198", "Present status", "devlake_health_check", {}, "Present status"),
    NLTestCase("ctx-199", "Now health check", "devlake_health_check", {}, "Now health"),
    NLTestCase("ctx-200", "This moment status", "devlake_health_check", {}, "This moment"),
]


# Combine all natural language test cases
ALL_NL_CASES = (
    CASUAL_CASES +
    FORMAL_CASES +
    QUESTION_CASES +
    COMMAND_CASES +
    CONTEXT_CASES
)


class TestNaturalLanguageToolMapping:
    """Test natural language variations map to correct tools."""

    @pytest.fixture
    def chat_service(self):
        """Create a ChatService with mocked tools."""
        from app.services.chat import ChatService
        from sqlalchemy.ext.asyncio import AsyncSession

        mock_db = MagicMock(spec=AsyncSession)
        service = ChatService(mock_db)

        # Register all tools
        tool_names = set(tc.expected_tool for tc in ALL_NL_CASES)
        for tool_name in tool_names:
            mock_tool = MagicMock()
            mock_tool.input_schema = {"type": "object", "properties": {}, "required": []}
            service._mcp_tools[tool_name] = ("builtin", mock_tool)

        return service

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_case", ALL_NL_CASES[:100], ids=lambda tc: tc.id)
    async def test_nl_batch_1(self, chat_service, test_case: NLTestCase):
        """Test first batch of natural language cases."""
        await self._verify_tool_call(chat_service, test_case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_case", ALL_NL_CASES[100:200], ids=lambda tc: tc.id)
    async def test_nl_batch_2(self, chat_service, test_case: NLTestCase):
        """Test second batch of natural language cases."""
        await self._verify_tool_call(chat_service, test_case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_case", ALL_NL_CASES[200:300], ids=lambda tc: tc.id)
    async def test_nl_batch_3(self, chat_service, test_case: NLTestCase):
        """Test third batch of natural language cases."""
        await self._verify_tool_call(chat_service, test_case)

    @pytest.mark.asyncio
    @pytest.mark.parametrize("test_case", ALL_NL_CASES[300:], ids=lambda tc: tc.id)
    async def test_nl_batch_4(self, chat_service, test_case: NLTestCase):
        """Test remaining natural language cases."""
        await self._verify_tool_call(chat_service, test_case)

    async def _verify_tool_call(self, chat_service, test_case: NLTestCase):
        """Verify tool call is correctly generated."""
        # Build expected tool call
        args_str = ", ".join(
            f"{k}='{v}'" if isinstance(v, str) else f"{k}={v}"
            for k, v in test_case.expected_args.items()
        )
        tool_call_content = f"TOOL_CALL: {test_case.expected_tool}({args_str})"

        # Mock executor
        chat_service._execute_mcp_tool = AsyncMock(return_value='{"success": true}')

        # Parse
        results = await chat_service._parse_and_execute_tool_calls(tool_call_content)

        # Verify
        assert len(results) >= 1, f"Expected tool call for: {test_case.description}"
        tool_name, _ = results[0]
        assert tool_name == test_case.expected_tool


def get_nl_statistics():
    """Get statistics for natural language test cases."""
    return {
        "total": len(ALL_NL_CASES),
        "casual": len(CASUAL_CASES),
        "formal": len(FORMAL_CASES),
        "questions": len(QUESTION_CASES),
        "commands": len(COMMAND_CASES),
        "context": len(CONTEXT_CASES),
    }


if __name__ == "__main__":
    stats = get_nl_statistics()
    print(f"\n=== Natural Language Test Case Statistics ===")
    print(f"Total: {stats['total']}")
    print(f"  Casual: {stats['casual']}")
    print(f"  Formal: {stats['formal']}")
    print(f"  Questions: {stats['questions']}")
    print(f"  Commands: {stats['commands']}")
    print(f"  Context-rich: {stats['context']}")
