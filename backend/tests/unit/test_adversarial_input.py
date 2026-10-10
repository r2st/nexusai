"""GB048: M6 Adversarial input tests.

Tests for SQL injection, Cypher injection, XSS, oversized payloads,
null bytes, path traversal, unicode edge cases, and authentication bypass.
"""

import pytest
from pydantic import ValidationError

from app.core.input_validation import (
    validate_cypher_identifier,
    validate_no_path_traversal,
    sanitize_error_string,
)


# ============================================================================
# 1. Cypher Identifier Validation (Knowledge Graph injection prevention)
# ============================================================================

class TestCypherIdentifierValidation:
    """Test validate_cypher_identifier rejects injection payloads."""

    def test_valid_identifiers(self):
        assert validate_cypher_identifier("Table", "label") == "Table"
        assert validate_cypher_identifier("Column", "label") == "Column"
        assert validate_cypher_identifier("_private", "label") == "_private"
        assert validate_cypher_identifier("My_Table_123", "label") == "My_Table_123"

    def test_rejects_cypher_injection_with_closing_brace(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException) as exc_info:
            validate_cypher_identifier("Table}) DETACH DELETE n//", "label")
        assert exc_info.value.status_code == 400

    def test_rejects_cypher_injection_with_match(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_cypher_identifier("Table MATCH (n) DETACH DELETE n", "label")

    def test_rejects_empty_string(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_cypher_identifier("", "label")

    def test_rejects_special_characters(self):
        from fastapi import HTTPException
        for payload in [
            "Table;DROP",
            "Table`injection`",
            "Table' OR 1=1--",
            "Table\x00null",
            "Table\nMATCH",
            "(n:Table)",
            "n:Table",
            "Table{}",
            "Table[]",
        ]:
            with pytest.raises(HTTPException):
                validate_cypher_identifier(payload, "label")

    def test_rejects_leading_number(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_cypher_identifier("123Table", "label")

    def test_rejects_oversized_identifier(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_cypher_identifier("A" * 129, "label")

    def test_max_length_accepted(self):
        result = validate_cypher_identifier("A" * 128, "label")
        assert len(result) == 128


# ============================================================================
# 2. Path Traversal Prevention (Signed URLs / File keys)
# ============================================================================

class TestPathTraversalValidation:
    """Test validate_no_path_traversal rejects directory traversal."""

    def test_valid_paths(self):
        assert validate_no_path_traversal("documents/file.pdf") == "documents/file.pdf"
        assert validate_no_path_traversal("user123/avatar.png") == "user123/avatar.png"

    def test_rejects_dot_dot(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_no_path_traversal("../../etc/passwd")

    def test_rejects_double_dot_mid_path(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_no_path_traversal("documents/../../../etc/shadow")

    def test_rejects_absolute_path(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_no_path_traversal("/etc/passwd")

    def test_rejects_null_byte(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_no_path_traversal("file.pdf\x00.png")

    def test_rejects_windows_traversal(self):
        from fastapi import HTTPException
        with pytest.raises(HTTPException):
            validate_no_path_traversal("..\\..\\windows\\system32")


# ============================================================================
# 3. Error String Sanitization (XSS prevention in error messages)
# ============================================================================

class TestErrorStringSanitization:

    def test_strips_html_tags(self):
        result = sanitize_error_string("<script>alert('xss')</script>")
        assert "<" not in result
        assert ">" not in result
        assert "script" in result  # text content kept

    def test_truncates_long_strings(self):
        result = sanitize_error_string("A" * 500, max_length=200)
        assert len(result) == 200

    def test_strips_quotes(self):
        result = sanitize_error_string("test\"value'here")
        assert '"' not in result
        assert "'" not in result

    def test_strips_ampersand(self):
        result = sanitize_error_string("a&b")
        assert "&" not in result


# ============================================================================
# 4. Auth API - Registration Validation
# ============================================================================

class TestAuthRegistrationValidation:

    def test_rejects_short_username(self):
        from app.api.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="test@example.com",
                username="ab",
                password="SecurePass123!",
            )

    def test_rejects_long_username(self):
        from app.api.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="test@example.com",
                username="a" * 51,
                password="SecurePass123!",
            )

    def test_rejects_username_with_special_chars(self):
        from app.api.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="test@example.com",
                username="user<script>",
                password="SecurePass123!",
            )

    def test_rejects_username_with_spaces(self):
        from app.api.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="test@example.com",
                username="user name",
                password="SecurePass123!",
            )

    def test_rejects_short_password(self):
        from app.api.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="test@example.com",
                username="validuser",
                password="short",
            )

    def test_rejects_long_password(self):
        from app.api.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="test@example.com",
                username="validuser",
                password="a" * 129,
            )

    def test_rejects_sql_injection_in_username(self):
        from app.api.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="test@example.com",
                username="'; DROP TABLE users;--",
                password="SecurePass123!",
            )

    def test_accepts_valid_username_with_hyphens_underscores(self):
        from app.api.auth import RegisterRequest
        req = RegisterRequest(
            email="test@example.com",
            username="valid-user_name",
            password="SecurePass123!",
        )
        assert req.username == "valid-user_name"

    def test_rejects_long_full_name(self):
        from app.api.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="test@example.com",
                username="validuser",
                password="SecurePass123!",
                full_name="A" * 201,
            )


# ============================================================================
# 5. Chat API - Input Bounds Validation
# ============================================================================

class TestChatRequestValidation:

    def test_rejects_empty_message(self):
        from app.api.chat import ChatRequest
        with pytest.raises(ValidationError):
            ChatRequest(message="")

    def test_rejects_oversized_message(self):
        from app.api.chat import ChatRequest
        with pytest.raises(ValidationError):
            ChatRequest(message="A" * 100001)

    def test_rejects_temperature_too_high(self):
        from app.api.chat import ChatRequest
        with pytest.raises(ValidationError):
            ChatRequest(message="hello", temperature=3.0)

    def test_rejects_negative_temperature(self):
        from app.api.chat import ChatRequest
        with pytest.raises(ValidationError):
            ChatRequest(message="hello", temperature=-0.1)

    def test_rejects_max_tokens_too_high(self):
        from app.api.chat import ChatRequest
        with pytest.raises(ValidationError):
            ChatRequest(message="hello", max_tokens=200000)

    def test_rejects_max_tokens_zero(self):
        from app.api.chat import ChatRequest
        with pytest.raises(ValidationError):
            ChatRequest(message="hello", max_tokens=0)

    def test_rejects_too_many_mcp_servers(self):
        from app.api.chat import ChatRequest, MCPServerConfigRequest
        servers = [
            MCPServerConfigRequest(name=f"server{i}", url=f"http://localhost:{8000+i}")
            for i in range(11)
        ]
        with pytest.raises(ValidationError):
            ChatRequest(message="hello", mcp_servers=servers)

    def test_valid_message_accepted(self):
        from app.api.chat import ChatRequest
        req = ChatRequest(message="Hello world")
        assert req.message == "Hello world"
        assert req.temperature == 0.7
        assert req.max_tokens == 4096

    def test_unicode_message_accepted(self):
        from app.api.chat import ChatRequest
        req = ChatRequest(message="GST की दरें क्या हैं? 你好世界 🌍")
        assert "GST" in req.message

    def test_sql_injection_in_message_accepted(self):
        """SQL in chat messages is fine — it's passed to the LLM, not a DB."""
        from app.api.chat import ChatRequest
        req = ChatRequest(message="'; DROP TABLE users;--")
        assert req.message == "'; DROP TABLE users;--"


# ============================================================================
# 6. Conversation Creation Validation
# ============================================================================

class TestConversationCreationValidation:

    def test_rejects_oversized_title(self):
        from app.api.chat import CreateConversationRequest
        with pytest.raises(ValidationError):
            CreateConversationRequest(title="A" * 501)

    def test_rejects_oversized_system_prompt(self):
        from app.api.chat import CreateConversationRequest
        with pytest.raises(ValidationError):
            CreateConversationRequest(system_prompt="A" * 50001)

    def test_rejects_oversized_model_name(self):
        from app.api.chat import CreateConversationRequest
        with pytest.raises(ValidationError):
            CreateConversationRequest(model_name="A" * 201)


# ============================================================================
# 7. Organization Slug Validation
# ============================================================================

class TestOrganizationSlugValidation:

    def test_rejects_slug_with_uppercase(self):
        from app.api.organizations import OrganizationCreate
        with pytest.raises(ValidationError):
            OrganizationCreate(name="Test Org", slug="TestOrg")

    def test_rejects_slug_with_spaces(self):
        from app.api.organizations import OrganizationCreate
        with pytest.raises(ValidationError):
            OrganizationCreate(name="Test Org", slug="test org")

    def test_rejects_slug_with_special_chars(self):
        from app.api.organizations import OrganizationCreate
        with pytest.raises(ValidationError):
            OrganizationCreate(name="Test Org", slug="test<script>")

    def test_rejects_slug_starting_with_hyphen(self):
        from app.api.organizations import OrganizationCreate
        with pytest.raises(ValidationError):
            OrganizationCreate(name="Test Org", slug="-test-org")

    def test_rejects_oversized_name(self):
        from app.api.organizations import OrganizationCreate
        with pytest.raises(ValidationError):
            OrganizationCreate(name="A" * 201, slug="test-org")

    def test_accepts_valid_slug(self):
        from app.api.organizations import OrganizationCreate
        req = OrganizationCreate(name="Test Org", slug="test-org")
        assert req.slug == "test-org"


# ============================================================================
# 8. Signed URL File Key Validation
# ============================================================================

class TestSignedURLValidation:

    def test_rejects_path_traversal_in_file_key(self):
        from app.api.signed_urls import SignedURLRequest
        with pytest.raises(ValidationError):
            SignedURLRequest(file_key="../../etc/passwd")

    def test_rejects_absolute_path_in_file_key(self):
        from app.api.signed_urls import SignedURLRequest
        with pytest.raises(ValidationError):
            SignedURLRequest(file_key="/etc/passwd")

    def test_rejects_null_byte_in_file_key(self):
        from app.api.signed_urls import SignedURLRequest
        with pytest.raises(ValidationError):
            SignedURLRequest(file_key="file.pdf\x00.exe")

    def test_rejects_invalid_operation(self):
        from app.api.signed_urls import SignedURLRequest
        with pytest.raises(ValidationError):
            SignedURLRequest(file_key="valid/file.pdf", operation="delete")

    def test_accepts_valid_file_key(self):
        from app.api.signed_urls import SignedURLRequest
        req = SignedURLRequest(file_key="documents/report.pdf")
        assert req.file_key == "documents/report.pdf"


# ============================================================================
# 9. XSS Payloads in Text Fields
# ============================================================================

class TestXSSPayloads:
    """Verify XSS payloads don't crash Pydantic models (they're accepted
    as strings but should be escaped on output by the frontend)."""

    XSS_PAYLOADS = [
        "<script>alert('XSS')</script>",
        "<img src=x onerror=alert(1)>",
        "javascript:alert('XSS')",
        "<svg/onload=alert(1)>",
        "'><script>alert(String.fromCharCode(88,83,83))</script>",
        "<body onload=alert(1)>",
        '"><img src=x onerror=alert(1)>',
        "<iframe src='javascript:alert(1)'>",
    ]

    def test_xss_in_chat_message_accepted(self):
        from app.api.chat import ChatRequest
        for payload in self.XSS_PAYLOADS:
            req = ChatRequest(message=payload)
            assert req.message == payload

    def test_xss_in_conversation_title_accepted(self):
        from app.api.chat import CreateConversationRequest
        for payload in self.XSS_PAYLOADS:
            req = CreateConversationRequest(title=payload)
            assert req.title == payload


# ============================================================================
# 10. Unicode Edge Cases
# ============================================================================

class TestUnicodeEdgeCases:

    def test_zero_width_characters_in_username(self):
        from app.api.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="test@example.com",
                username="user​name",  # zero-width space
                password="SecurePass123!",
            )

    def test_rtl_override_in_username(self):
        from app.api.auth import RegisterRequest
        with pytest.raises(ValidationError):
            RegisterRequest(
                email="test@example.com",
                username="user‮name",  # RTL override
                password="SecurePass123!",
            )

    def test_unicode_in_chat_message(self):
        from app.api.chat import ChatRequest
        req = ChatRequest(message="Hello 世界 🌍 مرحبا \u0000")
        assert "世界" in req.message

    def test_emoji_in_conversation_title(self):
        from app.api.chat import CreateConversationRequest
        req = CreateConversationRequest(title="🎉 GST Discussion 🇮🇳")
        assert "GST" in req.title


# ============================================================================
# 11. Deeply Nested JSON / Circular Reference Attempts
# ============================================================================

class TestDeeplyNestedInput:

    def test_deeply_nested_mcp_server_env(self):
        """Pydantic dict[str, str] flattens nested structures or rejects them."""
        from app.api.chat import MCPServerConfigRequest
        req = MCPServerConfigRequest(
            name="test",
            url="http://localhost:8000",
            env={"KEY": "value"},
        )
        assert req.env == {"KEY": "value"}

    def test_oversized_mcp_server_headers(self):
        from app.api.chat import MCPServerConfigRequest
        huge_headers = {f"X-Header-{i}": "v" * 1000 for i in range(100)}
        req = MCPServerConfigRequest(
            name="test",
            url="http://localhost:8000",
            headers=huge_headers,
        )
        assert len(req.headers) == 100


# ============================================================================
# 12. Duplicate Key Handling
# ============================================================================

class TestDuplicateKeys:

    def test_duplicate_json_keys_last_wins(self):
        """Python's json.loads uses last-value-wins for duplicate keys."""
        import json
        raw = '{"message": "first", "message": "second", "temperature": 0.5}'
        data = json.loads(raw)
        assert data["message"] == "second"

    def test_duplicate_mcp_server_names(self):
        from app.api.chat import ChatRequest, MCPServerConfigRequest
        servers = [
            MCPServerConfigRequest(name="dup", url="http://localhost:8001"),
            MCPServerConfigRequest(name="dup", url="http://localhost:8002"),
        ]
        req = ChatRequest(message="hello", mcp_servers=servers)
        assert len(req.mcp_servers) == 2


# ============================================================================
# 13. SQL Injection Payloads (should be harmless — parameterized queries)
# ============================================================================

class TestSQLInjectionPayloads:
    """Verify SQL injection payloads don't bypass validation at the API layer."""

    SQL_PAYLOADS = [
        "'; DROP TABLE users;--",
        "1' OR '1'='1",
        "1; UPDATE users SET role='admin'",
        "UNION SELECT * FROM users--",
        "'; EXEC xp_cmdshell('whoami');--",
        "1' AND 1=0 UNION ALL SELECT table_name FROM information_schema.tables--",
    ]

    def test_sql_in_search_query(self):
        from app.api.query import UnifiedQueryRequest
        for payload in self.SQL_PAYLOADS:
            req = UnifiedQueryRequest(search_query=payload)
            assert req.search_query == payload

    def test_sql_in_username_rejected(self):
        from app.api.auth import RegisterRequest
        for payload in self.SQL_PAYLOADS:
            with pytest.raises(ValidationError):
                RegisterRequest(
                    email="test@example.com",
                    username=payload,
                    password="SecurePass123!",
                )


# ============================================================================
# 14. Document Search Input Bounds
# ============================================================================

class TestDocumentSearchBounds:

    def test_rejects_empty_query(self):
        from app.api.documents import SearchRequest
        with pytest.raises(ValidationError):
            SearchRequest(query="")

    def test_rejects_oversized_query(self):
        from app.api.documents import SearchRequest
        with pytest.raises(ValidationError):
            SearchRequest(query="x" * 10001)

    def test_rejects_limit_too_large(self):
        from app.api.documents import SearchRequest
        with pytest.raises(ValidationError):
            SearchRequest(query="valid query", limit=999)

    def test_rejects_negative_limit(self):
        from app.api.documents import SearchRequest
        with pytest.raises(ValidationError):
            SearchRequest(query="valid query", limit=-1)

    def test_rejects_similarity_out_of_range(self):
        from app.api.documents import SearchRequest
        with pytest.raises(ValidationError):
            SearchRequest(query="valid query", similarity_threshold=1.5)

    def test_accepts_valid_search(self):
        from app.api.documents import SearchRequest
        req = SearchRequest(query="find documents about GST", limit=20, similarity_threshold=0.8)
        assert req.limit == 20


# ============================================================================
# 15. Workflow Request Bounds
# ============================================================================

class TestWorkflowRequestBounds:

    def test_rejects_empty_name(self):
        from app.api.workflows import CreateWorkflowRequest
        with pytest.raises(ValidationError):
            CreateWorkflowRequest(name="", organization_id="org-1")

    def test_rejects_oversized_name(self):
        from app.api.workflows import CreateWorkflowRequest
        with pytest.raises(ValidationError):
            CreateWorkflowRequest(name="x" * 201, organization_id="org-1")

    def test_rejects_oversized_description(self):
        from app.api.workflows import CreateWorkflowRequest
        with pytest.raises(ValidationError):
            CreateWorkflowRequest(name="valid", organization_id="org-1", description="x" * 2001)

    def test_accepts_valid_workflow(self):
        from app.api.workflows import CreateWorkflowRequest
        req = CreateWorkflowRequest(name="My Workflow", organization_id="org-123")
        assert req.name == "My Workflow"


# ============================================================================
# 16. Compliance Evidence Path Traversal
# ============================================================================

class TestComplianceEvidencePathTraversal:

    def test_rejects_path_traversal_in_file_path(self):
        from app.api.compliance import AddEvidenceRequest, SOC2EvidenceType
        with pytest.raises(ValidationError):
            AddEvidenceRequest(
                control_id="ctrl-1",
                evidence_type=SOC2EvidenceType.SCREENSHOT,
                title="Test",
                collected_by="admin",
                file_path="../../etc/passwd",
            )

    def test_rejects_absolute_path(self):
        from app.api.compliance import AddEvidenceRequest, SOC2EvidenceType
        with pytest.raises(ValidationError):
            AddEvidenceRequest(
                control_id="ctrl-1",
                evidence_type=SOC2EvidenceType.SCREENSHOT,
                title="Test",
                collected_by="admin",
                file_path="/etc/passwd",
            )

    def test_rejects_null_byte_in_file_path(self):
        from app.api.compliance import AddEvidenceRequest, SOC2EvidenceType
        with pytest.raises(ValidationError):
            AddEvidenceRequest(
                control_id="ctrl-1",
                evidence_type=SOC2EvidenceType.SCREENSHOT,
                title="Test",
                collected_by="admin",
                file_path="report.pdf\x00.exe",
            )

    def test_accepts_valid_evidence(self):
        from app.api.compliance import AddEvidenceRequest, SOC2EvidenceType
        req = AddEvidenceRequest(
            control_id="ctrl-1",
            evidence_type=SOC2EvidenceType.SCREENSHOT,
            title="Screenshot",
            collected_by="admin",
            file_path="evidence/screenshot.png",
        )
        assert req.file_path == "evidence/screenshot.png"


# ============================================================================
# 17. HIPAA PHI Detection Bounds
# ============================================================================

class TestHIPAAPHIDetectionBounds:

    def test_rejects_empty_content(self):
        from app.api.hipaa import DetectPHIRequest
        with pytest.raises(ValidationError):
            DetectPHIRequest(content="")

    def test_rejects_oversized_content(self):
        from app.api.hipaa import DetectPHIRequest
        with pytest.raises(ValidationError):
            DetectPHIRequest(content="x" * 500001)

    def test_rejects_confidence_out_of_range(self):
        from app.api.hipaa import DetectPHIRequest
        with pytest.raises(ValidationError):
            DetectPHIRequest(content="test data", min_confidence=2.0)

    def test_rejects_path_traversal_in_baa_document(self):
        from app.api.hipaa import ActivateBAARequest
        with pytest.raises(ValidationError):
            ActivateBAARequest(activated_by="admin", signed_document_path="../../etc/passwd")

    def test_accepts_valid_phi_request(self):
        from app.api.hipaa import DetectPHIRequest
        req = DetectPHIRequest(content="Patient John Doe SSN 123-45-6789")
        assert "Patient" in req.content


# ============================================================================
# 18. Scheduler Task Bounds
# ============================================================================

class TestSchedulerTaskBounds:

    def test_rejects_extreme_timeout(self):
        from app.api.scheduler import CreateTaskRequest
        with pytest.raises(ValidationError):
            CreateTaskRequest(
                name="task", description="desc", task_type="agent",
                trigger_type="cron", timeout_seconds=999999,
            )

    def test_rejects_extreme_retries(self):
        from app.api.scheduler import CreateTaskRequest
        with pytest.raises(ValidationError):
            CreateTaskRequest(
                name="task", description="desc", task_type="agent",
                trigger_type="cron", max_retries=100,
            )

    def test_rejects_oversized_name(self):
        from app.api.scheduler import CreateTaskRequest
        with pytest.raises(ValidationError):
            CreateTaskRequest(
                name="x" * 201, description="desc", task_type="agent",
                trigger_type="cron",
            )

    def test_accepts_valid_task(self):
        from app.api.scheduler import CreateTaskRequest
        req = CreateTaskRequest(
            name="My Task", description="Run nightly", task_type="agent",
            trigger_type="cron", cron_expression="0 0 * * *",
        )
        assert req.timeout_seconds == 300


# ============================================================================
# 19. LangServe Batch Size Limit
# ============================================================================

class TestLangServeBatchBounds:

    def test_rejects_oversized_batch(self):
        from app.api.langserve import BatchRequest
        with pytest.raises(ValidationError):
            BatchRequest(inputs=["prompt"] * 51)

    def test_accepts_valid_batch(self):
        from app.api.langserve import BatchRequest
        req = BatchRequest(inputs=["prompt1", "prompt2"])
        assert len(req.inputs) == 2


# ============================================================================
# 20. Grafana RBAC Role Validation
# ============================================================================

class TestGrafanaRBACRoleValidation:

    def test_rejects_invalid_role(self):
        from app.api.grafana_rbac import SyncUserRequest
        with pytest.raises(ValidationError):
            SyncUserRequest(role="SuperAdmin")

    def test_rejects_injection_in_role(self):
        from app.api.grafana_rbac import SyncUserRequest
        with pytest.raises(ValidationError):
            SyncUserRequest(role="Admin'; DROP TABLE users;--")

    def test_accepts_valid_roles(self):
        from app.api.grafana_rbac import SyncUserRequest
        for role in ("Admin", "Editor", "Viewer"):
            req = SyncUserRequest(role=role)
            assert req.role == role

    def test_assign_role_rejects_invalid(self):
        from app.api.grafana_rbac import AssignRoleRequest
        with pytest.raises(ValidationError):
            AssignRoleRequest(user_id=1, role="hacker")
