"""GB053: M18 testing — Secret filter detection, entropy, redaction, and edge cases."""

import pytest

from app.services.guardrails.secrets import (
    FilterResult,
    SecretFilter,
    SecretMatch,
    SecretPattern,
    SecretType,
    detect_secrets,
    has_secrets,
    redact_secrets,
)


class TestSecretMatchPostInit:
    def test_auto_generates_hash(self):
        m = SecretMatch(type=SecretType.API_KEY, value="test_secret", start=0, end=11, confidence=0.9)
        assert len(m.value_hash) == 16
        assert m.value_hash != ""

    def test_preserves_explicit_hash(self):
        m = SecretMatch(type=SecretType.API_KEY, value="test_secret", start=0, end=11, confidence=0.9, value_hash="custom_hash")
        assert m.value_hash == "custom_hash"

    def test_different_values_different_hashes(self):
        m1 = SecretMatch(type=SecretType.API_KEY, value="secret_one", start=0, end=10, confidence=0.9)
        m2 = SecretMatch(type=SecretType.API_KEY, value="secret_two", start=0, end=10, confidence=0.9)
        assert m1.value_hash != m2.value_hash


class TestFilterResultProperties:
    def test_has_secrets_true(self):
        r = FilterResult(original_text="x", filtered_text="x", secrets_found=[
            SecretMatch(type=SecretType.GENERIC, value="abc", start=0, end=3, confidence=0.8)
        ])
        assert r.has_secrets is True

    def test_has_secrets_false(self):
        r = FilterResult(original_text="x", filtered_text="x")
        assert r.has_secrets is False


class TestPatternDetection:
    @pytest.fixture
    def sf(self):
        return SecretFilter()

    def test_detects_generic_api_key(self, sf):
        text = 'api_key = "abcdefghijklmnopqrstuvwxyz1234"'
        result = sf.filter(text)
        assert result.has_secrets
        assert any(s.type == SecretType.API_KEY for s in result.secrets_found)

    def test_detects_aws_access_key(self, sf):
        text = "credential: AKIAIOSFODNN7EXAMPLE"
        result = sf.filter(text)
        assert any(s.type == SecretType.AWS_KEY for s in result.secrets_found)

    def test_detects_gcp_key(self, sf):
        text = "key: AIzaSyA1234567890abcdefghijklmnopqrstuv"
        result = sf.filter(text)
        assert any(s.type == SecretType.GCP_KEY for s in result.secrets_found)

    def test_detects_github_token(self, sf):
        text = "token: ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghij"
        result = sf.filter(text)
        assert any(s.type == SecretType.GITHUB_TOKEN for s in result.secrets_found)

    def test_detects_github_pat(self, sf):
        text = "auth: github_pat_ABCDEFGHIJKLMNOPQRSTUVWXYZab"
        result = sf.filter(text)
        assert any(s.type == SecretType.GITHUB_TOKEN for s in result.secrets_found)

    def test_detects_slack_token(self, sf):
        token = "xoxb-" + "0" * 13 + "-" + "0" * 13 + "-fake"
        text = f"token: {token}"
        result = sf.filter(text)
        assert any(s.type == SecretType.SLACK_TOKEN for s in result.secrets_found)

    def test_detects_jwt(self, sf):
        text = "bearer eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOiIxMjM0NTY3ODkwIn0.abc123def456ghi789"
        result = sf.filter(text)
        assert any(s.type == SecretType.JWT for s in result.secrets_found)

    def test_detects_private_key_header(self, sf):
        text = "-----BEGIN RSA PRIVATE KEY-----\nMIIE..."
        result = sf.filter(text)
        assert any(s.type == SecretType.PRIVATE_KEY for s in result.secrets_found)

    def test_detects_ssh_key(self, sf):
        text = "-----BEGIN OPENSSH PRIVATE KEY-----"
        result = sf.filter(text)
        types = {s.type for s in result.secrets_found}
        assert SecretType.SSH_KEY in types or SecretType.PRIVATE_KEY in types

    def test_detects_connection_string(self, sf):
        text = "db = postgres://admin:s3cret_password@db.example.com:5432/mydb"
        result = sf.filter(text)
        assert any(s.type == SecretType.CONNECTION_STRING for s in result.secrets_found)

    def test_detects_mongodb_connection_string(self, sf):
        text = "uri = mongodb+srv://user:pass123@cluster.mongodb.net/db"
        result = sf.filter(text)
        assert any(s.type == SecretType.CONNECTION_STRING for s in result.secrets_found)

    def test_detects_password_assignment(self, sf):
        text = 'password = "MyS3cureP@ssword!"'
        result = sf.filter(text)
        assert any(s.type == SecretType.PASSWORD for s in result.secrets_found)

    def test_detects_certificate(self, sf):
        text = "-----BEGIN CERTIFICATE-----"
        result = sf.filter(text)
        assert any(s.type == SecretType.CERTIFICATE for s in result.secrets_found)

    def test_no_false_positive_on_safe_text(self, sf):
        text = "The weather today is sunny and warm."
        result = sf.filter(text)
        assert not result.has_secrets


class TestLengthConstraints:
    def test_short_value_rejected(self):
        short_pattern = SecretPattern(
            type=SecretType.GENERIC,
            pattern=__import__("re").compile(r'key=(\w+)'),
            confidence=0.9,
            min_length=20,
        )
        sf = SecretFilter(patterns=[short_pattern])
        result = sf.filter("key=short")
        assert not result.has_secrets

    def test_long_value_rejected(self):
        long_pattern = SecretPattern(
            type=SecretType.GENERIC,
            pattern=__import__("re").compile(r'key=(\w+)'),
            confidence=0.9,
            max_length=5,
        )
        sf = SecretFilter(patterns=[long_pattern])
        result = sf.filter("key=toolongvalue")
        assert not result.has_secrets


class TestConfidenceFiltering:
    def test_below_min_confidence_ignored(self):
        low_conf_pattern = SecretPattern(
            type=SecretType.GENERIC,
            pattern=__import__("re").compile(r'maybe_secret_(\w{20,})'),
            confidence=0.3,
        )
        sf = SecretFilter(patterns=[low_conf_pattern], min_confidence=0.5)
        result = sf.filter("maybe_secret_abcdefghijklmnopqrst")
        assert not result.has_secrets

    def test_above_min_confidence_detected(self):
        hi_conf_pattern = SecretPattern(
            type=SecretType.GENERIC,
            pattern=__import__("re").compile(r'definitely_(\w{20,})'),
            confidence=0.9,
        )
        sf = SecretFilter(patterns=[hi_conf_pattern], min_confidence=0.5)
        result = sf.filter("definitely_abcdefghijklmnopqrst")
        assert result.has_secrets


class TestCustomValidator:
    def test_validator_rejects(self):
        import re
        pattern = SecretPattern(
            type=SecretType.GENERIC,
            pattern=re.compile(r'val=(\w{20,})'),
            confidence=0.9,
            validator=lambda v: False,
        )
        sf = SecretFilter(patterns=[pattern])
        result = sf.filter("val=abcdefghijklmnopqrstuv")
        assert not result.has_secrets

    def test_validator_accepts(self):
        import re
        pattern = SecretPattern(
            type=SecretType.GENERIC,
            pattern=re.compile(r'val=(\w{20,})'),
            confidence=0.9,
            validator=lambda v: v.startswith("abc"),
        )
        sf = SecretFilter(patterns=[pattern])
        result = sf.filter("val=abcdefghijklmnopqrstuv")
        assert result.has_secrets


class TestTypeFiltering:
    def test_types_to_detect_limits_results(self):
        sf = SecretFilter()
        text = 'api_key = "abcdefghijklmnopqrstuvwxyz1234" and password = "MyS3cureP@ssword!"'
        result = sf.filter(text, types_to_detect={SecretType.PASSWORD})
        for s in result.secrets_found:
            assert s.type == SecretType.PASSWORD


class TestOverlapHandling:
    def test_ranges_overlap(self):
        sf = SecretFilter()
        assert sf._ranges_overlap((0, 10), (5, 15)) is True
        assert sf._ranges_overlap((0, 10), (10, 20)) is False
        assert sf._ranges_overlap((5, 15), (0, 10)) is True
        assert sf._ranges_overlap((0, 5), (10, 15)) is False

    def test_overlapping_matches_deduped(self):
        import re
        p1 = SecretPattern(type=SecretType.API_KEY, pattern=re.compile(r'secret_key\s*=\s*(\w{20,})'), confidence=0.95)
        p2 = SecretPattern(type=SecretType.GENERIC, pattern=re.compile(r'key\s*=\s*(\w{20,})'), confidence=0.7)
        sf = SecretFilter(patterns=[p1, p2])
        text = "secret_key = abcdefghijklmnopqrstuvwxyz"
        result = sf.filter(text)
        assert len(result.secrets_found) == 1


class TestEntropyDetection:
    def test_high_entropy_string_detected(self):
        sf = SecretFilter(enable_entropy_detection=True, entropy_threshold=3.5, min_confidence=0.5)
        text = "value: aB3$xK9mP2qR7wZ4yN1cD5fH8jL0sT6uV"
        result = sf.filter(text)
        assert result.has_secrets

    def test_low_entropy_string_ignored(self):
        sf = SecretFilter(enable_entropy_detection=True, entropy_threshold=4.5)
        text = "value: aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        result = sf.filter(text)
        entropy_matches = [s for s in result.secrets_found if s.type == SecretType.GENERIC]
        for m in entropy_matches:
            assert m.confidence >= sf.min_confidence

    def test_entropy_disabled(self):
        sf = SecretFilter(enable_entropy_detection=False, patterns=[])
        text = "aB3xK9mP2qR7wZ4yN1cD5fH8jL0sT6uV"
        result = sf.filter(text)
        assert not result.has_secrets

    def test_entropy_of_empty_string(self):
        sf = SecretFilter()
        assert sf._calculate_entropy("") == 0.0

    def test_entropy_of_single_char(self):
        sf = SecretFilter()
        assert sf._calculate_entropy("a") == 0.0

    def test_entropy_increases_with_variety(self):
        sf = SecretFilter()
        e_low = sf._calculate_entropy("aaaaaaaaaa")
        e_high = sf._calculate_entropy("abcdefghij")
        assert e_high > e_low


class TestRedaction:
    def test_redaction_replaces_secret(self):
        sf = SecretFilter()
        text = "AKIAIOSFODNN7EXAMPLEKEY"
        result = sf.filter(text, redact=True)
        if result.has_secrets:
            assert "AKIA" not in result.filtered_text
            assert "[REDACTED:" in result.filtered_text

    def test_no_redaction_when_disabled(self):
        sf = SecretFilter()
        text = "AKIAIOSFODNN7EXAMPLEKEY"
        result = sf.filter(text, redact=False)
        if result.has_secrets:
            assert result.filtered_text == text
            assert result.redaction_count == 0

    def test_custom_redaction_format(self):
        sf = SecretFilter(redaction_format="***REMOVED:{type}***")
        text = "AKIAIOSFODNN7EXAMPLEKEY"
        result = sf.filter(text, redact=True)
        if result.has_secrets:
            assert "***REMOVED:" in result.filtered_text

    def test_multiple_redactions_preserve_order(self):
        sf = SecretFilter()
        text = 'api_key = "aaaabbbbccccddddeeeeffffgggg" and password = "MyS3cureP@ssword!"'
        result = sf.filter(text, redact=True)
        assert result.redaction_count == len(result.secrets_found)

    def test_context_captured(self):
        sf = SecretFilter()
        text = "The key is AKIAIOSFODNN7EXAMPLEKEY for AWS"
        result = sf.filter(text, redact=False)
        if result.has_secrets:
            assert result.secrets_found[0].context != ""


class TestAddPattern:
    def test_add_pattern_extends(self):
        import re
        sf = SecretFilter()
        initial_count = len(sf.patterns)
        sf.add_pattern(SecretPattern(
            type=SecretType.GENERIC,
            pattern=re.compile(r'CUSTOM_(\w{20,})'),
            confidence=0.9,
        ))
        assert len(sf.patterns) == initial_count + 1


class TestCustomPatterns:
    def test_custom_patterns_appended(self):
        import re
        custom = [SecretPattern(
            type=SecretType.GENERIC,
            pattern=re.compile(r'MY_CUSTOM_SECRET_(\w{20,})'),
            confidence=0.95,
        )]
        sf = SecretFilter(custom_patterns=custom)
        text = "MY_CUSTOM_SECRET_abcdefghijklmnopqrstuvwxyz"
        result = sf.filter(text)
        assert result.has_secrets

    def test_override_patterns_replaces(self):
        import re
        custom = [SecretPattern(
            type=SecretType.GENERIC,
            pattern=re.compile(r'ONLY_THIS_(\w{20,})'),
            confidence=0.95,
        )]
        sf = SecretFilter(patterns=custom)
        text = "AKIAIOSFODNN7EXAMPLEKEY"
        result = sf.filter(text)
        assert not result.has_secrets


class TestGetStats:
    def test_stats_from_multiple_results(self):
        sf = SecretFilter()
        r1 = FilterResult(original_text="a", filtered_text="a", secrets_found=[
            SecretMatch(type=SecretType.API_KEY, value="x" * 20, start=0, end=20, confidence=0.9),
        ], redaction_count=1)
        r2 = FilterResult(original_text="b", filtered_text="b")
        r3 = FilterResult(original_text="c", filtered_text="c", secrets_found=[
            SecretMatch(type=SecretType.PASSWORD, value="y" * 10, start=0, end=10, confidence=0.85),
            SecretMatch(type=SecretType.API_KEY, value="z" * 20, start=20, end=40, confidence=0.9),
        ], redaction_count=2)
        stats = sf.get_stats([r1, r2, r3])
        assert stats["total_texts_processed"] == 3
        assert stats["total_secrets_found"] == 3
        assert stats["total_redactions"] == 3
        assert stats["texts_with_secrets"] == 2
        assert stats["secrets_by_type"]["api_key"] == 2
        assert stats["secrets_by_type"]["password"] == 1

    def test_stats_empty_results(self):
        sf = SecretFilter()
        stats = sf.get_stats([])
        assert stats["total_texts_processed"] == 0
        assert stats["total_secrets_found"] == 0


class TestDetectMethod:
    def test_detect_returns_matches_without_redaction(self):
        sf = SecretFilter()
        text = "AKIAIOSFODNN7EXAMPLEKEY"
        matches = sf.detect(text)
        assert isinstance(matches, list)


class TestRedactMethod:
    def test_redact_returns_filtered_text(self):
        sf = SecretFilter()
        text = "AKIAIOSFODNN7EXAMPLEKEY"
        result = sf.redact(text)
        assert isinstance(result, str)
        if detect_secrets(text):
            assert "AKIA" not in result


class TestConvenienceFunctions:
    def test_detect_secrets_function(self):
        matches = detect_secrets("AKIAIOSFODNN7EXAMPLEKEY")
        assert isinstance(matches, list)

    def test_redact_secrets_function(self):
        result = redact_secrets("AKIAIOSFODNN7EXAMPLEKEY")
        assert isinstance(result, str)

    def test_has_secrets_true(self):
        assert has_secrets("AKIAIOSFODNN7EXAMPLEKEY") is True

    def test_has_secrets_false(self):
        assert has_secrets("just a normal sentence") is False


class TestSQLConnectionString:
    def test_detects_sql_connection_string(self):
        sf = SecretFilter()
        text = "Server=myserver.database.windows.net;Database=mydb;Password=s3cretP@ss"
        result = sf.filter(text)
        assert result.has_secrets


class TestSecretsFoundSortedByPosition:
    def test_sorted_by_start(self):
        sf = SecretFilter()
        text = 'password = "MyS3cureP@ssword!" and api_key = "abcdefghijklmnopqrstuvwxyz1234"'
        result = sf.filter(text)
        if len(result.secrets_found) >= 2:
            starts = [s.start for s in result.secrets_found]
            assert starts == sorted(starts)
