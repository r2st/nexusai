"""GB053: M18 testing — Input validation boundary conditions."""

import pytest
from fastapi import HTTPException

from app.core.input_validation import (
    validate_cypher_identifier,
    validate_no_path_traversal,
    sanitize_error_string,
)


class TestValidateCypherIdentifierBoundaries:
    def test_single_underscore(self):
        assert validate_cypher_identifier("_") == "_"

    def test_exactly_128_chars(self):
        v = "a" * 128
        assert validate_cypher_identifier(v) == v

    def test_129_chars_rejected(self):
        v = "a" * 129
        with pytest.raises(HTTPException) as exc_info:
            validate_cypher_identifier(v)
        assert exc_info.value.status_code == 400

    def test_leading_digit_rejected(self):
        with pytest.raises(HTTPException):
            validate_cypher_identifier("1abc")

    def test_space_rejected(self):
        with pytest.raises(HTTPException):
            validate_cypher_identifier("ab cd")

    def test_empty_rejected(self):
        with pytest.raises(HTTPException):
            validate_cypher_identifier("")

    def test_unicode_rejected(self):
        with pytest.raises(HTTPException):
            validate_cypher_identifier("café")

    def test_custom_field_name_in_error(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_cypher_identifier("!!!", field_name="label")
        assert "label" in exc_info.value.detail

    def test_sql_injection_rejected(self):
        with pytest.raises(HTTPException):
            validate_cypher_identifier("'; DROP TABLE--")

    def test_newline_rejected(self):
        with pytest.raises(HTTPException):
            validate_cypher_identifier("abc\ndef")

    def test_tab_rejected(self):
        with pytest.raises(HTTPException):
            validate_cypher_identifier("abc\tdef")


class TestValidateNoPathTraversalBoundaries:
    def test_simple_filename(self):
        assert validate_no_path_traversal("report.pdf") == "report.pdf"

    def test_nested_path(self):
        assert validate_no_path_traversal("dir/file.txt") == "dir/file.txt"

    def test_dot_dot_rejected(self):
        with pytest.raises(HTTPException):
            validate_no_path_traversal("../etc/passwd")

    def test_dot_dot_in_middle(self):
        with pytest.raises(HTTPException):
            validate_no_path_traversal("dir/../secret")

    def test_absolute_path_rejected(self):
        with pytest.raises(HTTPException):
            validate_no_path_traversal("/etc/passwd")

    def test_null_byte_rejected(self):
        with pytest.raises(HTTPException):
            validate_no_path_traversal("file\x00.txt")

    def test_windows_dot_dot_rejected(self):
        with pytest.raises(HTTPException):
            validate_no_path_traversal("..\\windows\\system32")

    def test_single_dot_allowed(self):
        assert validate_no_path_traversal("file.txt") == "file.txt"

    def test_hidden_file_allowed(self):
        assert validate_no_path_traversal(".hidden") == ".hidden"

    def test_custom_field_name(self):
        with pytest.raises(HTTPException) as exc_info:
            validate_no_path_traversal("../hack", field_name="file_key")
        assert "file_key" in exc_info.value.detail

    def test_url_encoded_traversal(self):
        assert validate_no_path_traversal("%2e%2e/etc") == "%2e%2e/etc"

    def test_double_slash(self):
        assert validate_no_path_traversal("dir//file.txt") == "dir//file.txt"


class TestSanitizeErrorStringBoundaries:
    def test_short_string_unchanged(self):
        assert sanitize_error_string("hello") == "hello"

    def test_truncates_at_max_length(self):
        long = "a" * 500
        result = sanitize_error_string(long, max_length=200)
        assert len(result) == 200

    def test_custom_max_length(self):
        result = sanitize_error_string("hello world", max_length=5)
        assert result == "hello"

    def test_strips_html_angle_brackets(self):
        result = sanitize_error_string("<script>alert(1)</script>")
        assert "<" not in result
        assert ">" not in result

    def test_strips_quotes(self):
        result = sanitize_error_string("""she said "hello" and 'bye'""")
        assert '"' not in result
        assert "'" not in result

    def test_strips_ampersand(self):
        result = sanitize_error_string("foo&bar")
        assert "&" not in result

    def test_empty_string(self):
        assert sanitize_error_string("") == ""

    def test_only_special_chars(self):
        result = sanitize_error_string("<>&\"'")
        assert result == ""

    def test_mixed_content(self):
        result = sanitize_error_string("Error: <b>bad input</b> & 'value'", max_length=50)
        assert "<" not in result
        assert ">" not in result
        assert "&" not in result
        assert "'" not in result
        assert "Error:" in result

    def test_max_length_zero(self):
        result = sanitize_error_string("anything", max_length=0)
        assert result == ""

    def test_unicode_preserved(self):
        result = sanitize_error_string("café résumé")
        assert "café" in result
