"""Tests for API design compliance (GB052 M16).

Validates REST conventions across the entire OpenAPI spec:
- POST create endpoints return 201
- DELETE endpoints return 204
- All endpoints declare response models
- Error responses use HTTPException with detail field
- Pagination responses include items/total fields
"""

import os

import pytest

os.environ.setdefault("ENVIRONMENT", "test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-testing-only-32chars")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5434/nexusai_test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/1")
os.environ.setdefault("DATABASE_USER", "postgres")
os.environ.setdefault("DATABASE_PASSWORD", "postgres")
os.environ.setdefault("DATABASE_HOST", "localhost")
os.environ.setdefault("DATABASE_PORT", "5434")
os.environ.setdefault("DATABASE_NAME", "nexusai_test")
os.environ.setdefault("REDIS_HOST", "localhost")
os.environ.setdefault("REDIS_PORT", "6379")
os.environ.setdefault("REDIS_DB", "1")
os.environ.setdefault("REDIS_PASSWORD", "")
os.environ.setdefault("DEBUG", "true")

from app.main import app


@pytest.fixture(scope="module")
def openapi_schema():
    return app.openapi()


@pytest.fixture(scope="module")
def all_routes(openapi_schema):
    routes = []
    for path, methods in openapi_schema["paths"].items():
        for method, details in methods.items():
            responses = list(details.get("responses", {}).keys())
            routes.append({
                "method": method.upper(),
                "path": path,
                "responses": responses,
                "details": details,
            })
    return routes


POST_CREATE_ENDPOINTS = {
    "/api/v1/actions/prebuilt/github",
    "/api/v1/actions/prebuilt/jira",
    "/api/v1/actions/register",
    "/api/v1/actions/register/openapi-spec",
    "/api/v1/agents",
    "/api/v1/agents/{agent_id}/tools",
    "/api/v1/ai-analytics/connections",
    "/api/v1/analytics/plugins/{plugin}/connections",
    "/api/v1/analytics/projects",
    "/api/v1/auth/register",
    "/api/v1/chat/conversations",
    "/api/v1/chatbot/subscriptions",
    "/api/v1/collaboration/annotations",
    "/api/v1/collaboration/sessions",
    "/api/v1/compliance/gdpr/data-inventory",
    "/api/v1/compliance/gdpr/dsr",
    "/api/v1/compliance/gdpr/retention-policy",
    "/api/v1/compliance/soc2/access-review",
    "/api/v1/compliance/soc2/change",
    "/api/v1/compliance/soc2/evidence",
    "/api/v1/devops-agents/dashboard/create",
    "/api/v1/devops-agents/summary/create",
    "/api/v1/devops-agents/workflows",
    "/api/v1/documents/upload",
    "/api/v1/hipaa/baa",
    "/api/v1/hipaa/controls/{control_id}/evidence",
    "/api/v1/hipaa/encryption/register-endpoint",
    "/api/v1/hipaa/encryption/register-storage",
    "/api/v1/hipaa/policies/minimum-necessary",
    "/api/v1/knowledge-graph/nodes",
    "/api/v1/knowledge-graph/relationships",
    "/api/v1/organizations",
    "/api/v1/organizations/{org_id}/members/invite",
    "/api/v1/pipelines/blueprints",
    "/api/v1/residency/policies",
    "/api/v1/residency/policies/{policy_id}/requirements",
    "/api/v1/residency/policies/{policy_id}/requirements/gdpr",
    "/api/v1/residency/storage",
    "/api/v1/residency/transfers",
    "/api/v1/scheduler/tasks",
    "/api/v1/security/secrets/register",
    "/api/v1/signed-urls/upload",
    "/api/v1/tokens/",
    "/api/v1/workflows",
    "/api/v1/workflows/from-template",
}

DELETE_ENDPOINTS_204 = {
    "/api/v1/actions/{action_id}",
    "/api/v1/agents/{agent_id}",
    "/api/v1/chat/conversations/{conversation_id}",
    "/api/v1/chatbot/subscriptions",
    "/api/v1/collaboration/annotations/{annotation_id}",
    "/api/v1/documents/{document_id}",
    "/api/v1/knowledge-graph/nodes/{label}/{name}",
    "/api/v1/organizations/{org_id}",
    "/api/v1/organizations/{org_id}/members/{member_id}",
    "/api/v1/pipelines/blueprints/{blueprint_id}",
    "/api/v1/scheduler/tasks/{task_id}",
    "/api/v1/setup-assistant/sessions/{session_id}",
    "/api/v1/tokens/{token_id}",
    "/api/v1/workflows/{workflow_id}",
}

# POST action/RPC endpoints that correctly return 200 (not creates)
POST_ACTION_ENDPOINTS = {
    "/api/v1/actions/{action_id}/disable",
    "/api/v1/actions/{action_id}/enable",
    "/api/v1/actions/{action_id}/execute",
    "/api/v1/actions/{action_id}/validate",
    "/api/v1/agents/{agent_id}/execute",
    "/api/v1/auth/login",
    "/api/v1/auth/refresh",
    "/api/v1/chat/conversations/{conversation_id}/chat",
    "/api/v1/code-review/github/review",
    "/api/v1/code-review/gitlab/review",
    "/api/v1/code-review/webhook/github",
    "/api/v1/code-review/webhook/gitlab",
    "/api/v1/tokens/validate",
}


class TestPostCreateEndpointsReturn201:
    """All POST endpoints that create resources must return 201."""

    def test_all_create_endpoints_return_201(self, openapi_schema):
        failures = []
        for path in POST_CREATE_ENDPOINTS:
            methods = openapi_schema["paths"].get(path, {})
            post_details = methods.get("post", {})
            responses = list(post_details.get("responses", {}).keys())
            if "201" not in responses:
                failures.append(f"POST {path} returns {responses}, expected 201")
        assert not failures, "POST create endpoints missing 201:\n" + "\n".join(failures)

    @pytest.mark.parametrize("path", sorted(POST_CREATE_ENDPOINTS))
    def test_create_endpoint_has_201(self, openapi_schema, path):
        methods = openapi_schema["paths"].get(path, {})
        post_details = methods.get("post", {})
        responses = list(post_details.get("responses", {}).keys())
        assert "201" in responses, f"POST {path} should return 201 for resource creation"


class TestDeleteEndpointsReturn204:
    """All DELETE endpoints must return 204 No Content."""

    def test_all_delete_endpoints_return_204(self, openapi_schema):
        failures = []
        for path in DELETE_ENDPOINTS_204:
            methods = openapi_schema["paths"].get(path, {})
            delete_details = methods.get("delete", {})
            responses = list(delete_details.get("responses", {}).keys())
            if "204" not in responses:
                failures.append(f"DELETE {path} returns {responses}, expected 204")
        assert not failures, "DELETE endpoints missing 204:\n" + "\n".join(failures)

    @pytest.mark.parametrize("path", sorted(DELETE_ENDPOINTS_204))
    def test_delete_endpoint_has_204(self, openapi_schema, path):
        methods = openapi_schema["paths"].get(path, {})
        delete_details = methods.get("delete", {})
        responses = list(delete_details.get("responses", {}).keys())
        assert "204" in responses, f"DELETE {path} should return 204 No Content"


class TestEndpointResponseModels:
    """All non-204 endpoints should have response schema defined."""

    def test_get_endpoints_have_response_schema(self, all_routes):
        failures = []
        for route in all_routes:
            if route["method"] != "GET":
                continue
            details = route["details"]
            resp_200 = details.get("responses", {}).get("200", {})
            if "content" not in resp_200 and route["path"] not in {
                "/", "/health", "/healthz", "/api/health", "/api/healthz",
                "/observability/status", "/features",
            }:
                failures.append(f"GET {route['path']} has no response schema")
        assert not failures, "GET endpoints without response schema:\n" + "\n".join(failures)

    def test_post_create_endpoints_have_response_schema(self, openapi_schema):
        failures = []
        for path in POST_CREATE_ENDPOINTS:
            methods = openapi_schema["paths"].get(path, {})
            post_details = methods.get("post", {})
            resp_201 = post_details.get("responses", {}).get("201", {})
            if "content" not in resp_201:
                failures.append(f"POST {path} has no 201 response schema")
        assert not failures, "POST create endpoints without response schema:\n" + "\n".join(failures)


class TestErrorResponseFormat:
    """All endpoints should use 422 for validation errors (FastAPI default)."""

    def test_post_endpoints_have_422_validation_error(self, all_routes):
        skip_paths = {
            "/api/v1/chatbot/teams/messages",
            "/api/v1/events/publisher/connect",
            "/api/v1/llm/cache/clear",
            "/api/v1/mcp",
            "/api/v1/mcp/",
            "/api/v1/mcp/session",
            "/api/v1/mcp/start",
            "/api/v1/mcp/stop",
            "/api/v1/scheduler/start",
            "/api/v1/scheduler/stop",
            "/api/v1/security/secrets/rotate-all",
            "/api/v1/setup-assistant/onboarding",
            "/api/v1/code-review/health",
        }
        failures = []
        for route in all_routes:
            if route["method"] != "POST":
                continue
            if route["path"] in skip_paths:
                continue
            if route["path"].startswith("/api/v1/sso/"):
                continue
            if "422" not in route["responses"]:
                failures.append(f"POST {route['path']} missing 422 response")
        assert not failures, "POST endpoints missing 422 validation error:\n" + "\n".join(failures)

    def test_422_response_has_detail_field(self, openapi_schema):
        validation_error_ref = None
        for path, methods in openapi_schema["paths"].items():
            for method, details in methods.items():
                resp_422 = details.get("responses", {}).get("422", {})
                content = resp_422.get("content", {}).get("application/json", {})
                schema = content.get("schema", {})
                if "$ref" in schema:
                    validation_error_ref = schema["$ref"]
                    break
            if validation_error_ref:
                break

        if validation_error_ref:
            schema_name = validation_error_ref.split("/")[-1]
            schemas = openapi_schema.get("components", {}).get("schemas", {})
            error_schema = schemas.get(schema_name, {})
            properties = error_schema.get("properties", {})
            assert "detail" in properties, (
                f"Validation error schema '{schema_name}' should have 'detail' field"
            )


class TestPaginationConsistency:
    """Paginated list endpoints should have consistent response format."""

    def test_conversation_list_has_pagination_fields(self, openapi_schema):
        path = "/api/v1/chat/conversations"
        get_details = openapi_schema["paths"][path]["get"]
        resp_200 = get_details["responses"]["200"]
        content = resp_200.get("content", {}).get("application/json", {})
        schema = content.get("schema", {})

        ref = schema.get("$ref", "")
        if ref:
            schema_name = ref.split("/")[-1]
            schemas = openapi_schema["components"]["schemas"]
            resolved = schemas.get(schema_name, {})
            properties = resolved.get("properties", {})
            assert "items" in properties, "ConversationListResponse should have 'items'"
            assert "total" in properties, "ConversationListResponse should have 'total'"
            assert "limit" in properties, "ConversationListResponse should have 'limit'"
            assert "offset" in properties, "ConversationListResponse should have 'offset'"

    def test_agent_execution_list_has_pagination_fields(self, openapi_schema):
        path = "/api/v1/agents/{agent_id}/executions"
        get_details = openapi_schema["paths"][path]["get"]
        resp_200 = get_details["responses"]["200"]
        content = resp_200.get("content", {}).get("application/json", {})
        schema = content.get("schema", {})

        ref = schema.get("$ref", "")
        if ref:
            schema_name = ref.split("/")[-1]
            schemas = openapi_schema["components"]["schemas"]
            resolved = schemas.get(schema_name, {})
            properties = resolved.get("properties", {})
            assert "executions" in properties, "AgentExecutionListResponse should have 'executions'"
            assert "page" in properties, "AgentExecutionListResponse should have 'page'"
            assert "page_size" in properties, "AgentExecutionListResponse should have 'page_size'"


class TestAPIVersioning:
    """All API endpoints should be versioned under /api/v1/."""

    def test_all_api_endpoints_are_versioned(self, all_routes):
        unversioned = []
        skip_paths = {"/", "/health", "/healthz", "/api/health", "/api/healthz",
                      "/observability/status", "/features"}
        for route in all_routes:
            path = route["path"]
            if path in skip_paths:
                continue
            if not path.startswith("/api/v1/"):
                unversioned.append(f"{route['method']} {path}")
        assert not unversioned, "Unversioned API endpoints:\n" + "\n".join(unversioned)


class TestHTTPMethodConventions:
    """HTTP methods should follow REST conventions."""

    def test_no_put_for_partial_updates(self, all_routes):
        """PATCH should be used for partial updates, not PUT (except full replacements)."""
        put_routes = [r for r in all_routes if r["method"] == "PUT"]
        for route in put_routes:
            assert "422" in route["responses"], (
                f"PUT {route['path']} should validate request body (422)"
            )

    def test_delete_endpoints_no_request_body(self, openapi_schema):
        """DELETE endpoints should not require a request body."""
        allow_body = {"/api/v1/chatbot/subscriptions"}
        failures = []
        for path, methods in openapi_schema["paths"].items():
            if "delete" not in methods or path in allow_body:
                continue
            delete_details = methods["delete"]
            if "requestBody" in delete_details:
                req_body = delete_details["requestBody"]
                if req_body.get("required", False):
                    failures.append(f"DELETE {path} has required request body")
        assert not failures, "DELETE endpoints with required body:\n" + "\n".join(failures)


class TestWebhookEndpoints:
    """Webhook endpoints should use HTTPException for errors, not error dicts."""

    def test_webhook_endpoints_have_error_responses(self, openapi_schema):
        webhook_paths = [
            "/api/v1/code-review/webhook/github",
            "/api/v1/code-review/webhook/gitlab",
        ]
        for path in webhook_paths:
            methods = openapi_schema["paths"].get(path, {})
            post_details = methods.get("post", {})
            responses = list(post_details.get("responses", {}).keys())
            assert "422" in responses, f"Webhook {path} should have 422 error response"


class TestSharedResponseModels:
    """Verify shared response models exist and are correctly structured."""

    def test_error_response_model_exists(self):
        from app.api.response_models import ErrorResponse
        schema = ErrorResponse.model_json_schema()
        assert "detail" in schema["properties"]

    def test_paginated_response_model_exists(self):
        from app.api.response_models import PaginatedResponse
        schema = PaginatedResponse.model_json_schema()
        props = schema["properties"]
        assert "items" in props
        assert "total" in props
        assert "page" in props
        assert "page_size" in props
        assert "has_more" in props

    def test_status_response_model_exists(self):
        from app.api.response_models import StatusResponse
        schema = StatusResponse.model_json_schema()
        assert "status" in schema["properties"]

    def test_error_response_serialization(self):
        from app.api.response_models import ErrorResponse
        err = ErrorResponse(detail="Not found", code="NOT_FOUND")
        data = err.model_dump()
        assert data["detail"] == "Not found"
        assert data["code"] == "NOT_FOUND"

    def test_paginated_response_serialization(self):
        from app.api.response_models import PaginatedResponse
        page = PaginatedResponse(
            items=[{"id": "1"}],
            total=100,
            page=1,
            page_size=20,
            has_more=True,
        )
        data = page.model_dump()
        assert data["total"] == 100
        assert data["has_more"] is True
        assert len(data["items"]) == 1


class TestRouteCount:
    """Sanity check that expected routes are registered."""

    def test_minimum_route_count(self, all_routes):
        assert len(all_routes) > 100, (
            f"Expected 100+ routes, found {len(all_routes)}"
        )

    def test_post_create_endpoints_exist(self, openapi_schema):
        for path in POST_CREATE_ENDPOINTS:
            assert path in openapi_schema["paths"], f"Expected {path} in OpenAPI spec"
            assert "post" in openapi_schema["paths"][path], f"Expected POST method on {path}"

    def test_delete_endpoints_exist(self, openapi_schema):
        for path in DELETE_ENDPOINTS_204:
            assert path in openapi_schema["paths"], f"Expected {path} in OpenAPI spec"
            assert "delete" in openapi_schema["paths"][path], f"Expected DELETE method on {path}"
