"""GB067: Tests for core/input_validation.py — cypher injection, path traversal, sanitization."""

import pytest
from fastapi import HTTPException

from app.core.input_validation import (
    sanitize_error_string,
    validate_cypher_identifier,
    validate_no_path_traversal,
)


# ---------------------------------------------------------------------------
# validate_cypher_identifier
# ---------------------------------------------------------------------------

class TestCypherIdentifier:
    def test_valid_identifiers(self):
        assert validate_cypher_identifier("User") == "User"
        assert validate_cypher_identifier("_private") == "_private"
        assert validate_cypher_identifier("my_label_123") == "my_label_123"
        assert validate_cypher_identifier("A") == "A"

    def test_rejects_empty_string(self):
        with pytest.raises(HTTPException) as exc:
            validate_cypher_identifier("")
        assert exc.value.status_code == 400

    def test_rejects_starting_with_digit(self):
        with pytest.raises(HTTPException):
            validate_cypher_identifier("1BadLabel")

    def test_rejects_special_characters(self):
        for bad in ["user;DROP", "la bel", "a.b", "x-y", "foo()", "a{b}", "a'b"]:
            with pytest.raises(HTTPException):
                validate_cypher_identifier(bad)

    def test_rejects_cypher_injection_payloads(self):
        payloads = [
            "User} RETURN n; MATCH (m) DELETE m //",
            "User' OR 1=1 --",
            "Label\nMATCH (n) DELETE n",
            "x\x00y",
        ]
        for payload in payloads:
            with pytest.raises(HTTPException):
                validate_cypher_identifier(payload)

    def test_max_length_128(self):
        assert validate_cypher_identifier("a" * 128) == "a" * 128
        with pytest.raises(HTTPException):
            validate_cypher_identifier("a" * 129)

    def test_custom_field_name_in_error(self):
        with pytest.raises(HTTPException) as exc:
            validate_cypher_identifier("1bad", field_name="label")
        assert "label" in exc.value.detail


# ---------------------------------------------------------------------------
# validate_no_path_traversal
# ---------------------------------------------------------------------------

class TestPathTraversal:
    def test_valid_paths(self):
        assert validate_no_path_traversal("file.txt") == "file.txt"
        assert validate_no_path_traversal("subdir/file.txt") == "subdir/file.txt"
        assert validate_no_path_traversal("a/b/c.pdf") == "a/b/c.pdf"

    def test_rejects_dot_dot(self):
        with pytest.raises(HTTPException) as exc:
            validate_no_path_traversal("../etc/passwd")
        assert exc.value.status_code == 400

    def test_rejects_embedded_dot_dot(self):
        with pytest.raises(HTTPException):
            validate_no_path_traversal("subdir/../../etc/passwd")

    def test_rejects_absolute_path(self):
        with pytest.raises(HTTPException):
            validate_no_path_traversal("/etc/passwd")

    def test_rejects_null_byte(self):
        with pytest.raises(HTTPException):
            validate_no_path_traversal("file.txt\x00.jpg")

    def test_custom_field_name_in_error(self):
        with pytest.raises(HTTPException) as exc:
            validate_no_path_traversal("../x", field_name="file_key")
        assert "file_key" in exc.value.detail

    def test_dot_dot_in_filename_rejected(self):
        with pytest.raises(HTTPException):
            validate_no_path_traversal("something..hidden")


# ---------------------------------------------------------------------------
# sanitize_error_string
# ---------------------------------------------------------------------------

class TestSanitizeErrorString:
    def test_plain_text_unchanged(self):
        assert sanitize_error_string("hello world") == "hello world"

    def test_strips_html_special_chars(self):
        result = sanitize_error_string("<script>alert('xss')</script>")
        assert "<" not in result
        assert ">" not in result
        assert "'" not in result

    def test_strips_ampersand(self):
        result = sanitize_error_string("a & b")
        assert "&" not in result

    def test_strips_double_quotes(self):
        result = sanitize_error_string('a "b" c')
        assert '"' not in result

    def test_truncates_to_max_length(self):
        long_input = "x" * 500
        result = sanitize_error_string(long_input, max_length=100)
        assert len(result) == 100

    def test_default_max_length_200(self):
        long_input = "a" * 300
        result = sanitize_error_string(long_input)
        assert len(result) == 200

    def test_empty_string(self):
        assert sanitize_error_string("") == ""

    def test_combined_html_and_length(self):
        payload = "<b>" + "a" * 300
        result = sanitize_error_string(payload, max_length=50)
        assert len(result) <= 50
        assert "<" not in result
