"""GB053: M18 testing — PII detection edge cases, Luhn validation, redaction, and overlap removal."""

import pytest

from app.services.guardrails.models import PIIMatch, PIIType
from app.services.guardrails.pii import PIIDetector, PIIRedactor


class TestPIIDetectorEdgeCases:
    @pytest.fixture
    def detector(self):
        return PIIDetector()

    def test_empty_string(self, detector):
        assert detector.detect("") == []

    def test_no_pii(self, detector):
        assert detector.detect("Hello, how are you today?") == []

    def test_multiple_pii_types_in_one_text(self, detector):
        text = "My email is test@example.com and my phone is 555-123-4567"
        matches = detector.detect(text)
        types = {m.type for m in matches}
        assert PIIType.EMAIL in types
        assert PIIType.PHONE in types

    def test_detect_password_in_context(self, detector):
        text = "password: MySecretP@ss123"
        matches = detector.detect(text)
        types = {m.type for m in matches}
        assert PIIType.PASSWORD in types

    def test_detect_iban(self, detector):
        text = "My IBAN is DE89370400440532013000"
        matches = detector.detect(text)
        types = {m.type for m in matches}
        assert PIIType.BANK_ACCOUNT in types

    def test_custom_types_filter(self):
        detector = PIIDetector(types_to_detect=[PIIType.EMAIL])
        text = "email test@example.com phone 555-123-4567"
        matches = detector.detect(text)
        types = {m.type for m in matches}
        assert PIIType.EMAIL in types
        assert PIIType.PHONE not in types

    def test_custom_patterns(self):
        custom = {PIIType.EMAIL: [(r"custom@match\.test", 0.99)]}
        detector = PIIDetector(custom_patterns=custom)
        matches = detector.detect("contact custom@match.test please")
        assert any(m.type == PIIType.EMAIL for m in matches)


class TestLuhnValidation:
    @pytest.fixture
    def detector(self):
        return PIIDetector(types_to_detect=[PIIType.CREDIT_CARD])

    def test_valid_visa(self, detector):
        assert detector._validate_credit_card("4111111111111111") is True

    def test_valid_mastercard(self, detector):
        assert detector._validate_credit_card("5500000000000004") is True

    def test_invalid_number(self, detector):
        assert detector._validate_credit_card("4111111111111112") is False

    def test_too_short(self, detector):
        assert detector._validate_credit_card("411111") is False

    def test_too_long(self, detector):
        assert detector._validate_credit_card("41111111111111111111") is False

    def test_with_separators(self, detector):
        assert detector._validate_credit_card("4111-1111-1111-1111") is True


class TestContextConfidenceAdjustment:
    @pytest.fixture
    def detector(self):
        return PIIDetector()

    def test_phone_context_increases_confidence(self, detector):
        text_with = "My phone number is 555-123-4567"
        text_without = "The code is 555-123-4567"
        matches_with = detector.detect(text_with)
        matches_without = detector.detect(text_without)
        phone_with = [m for m in matches_with if m.type == PIIType.PHONE]
        phone_without = [m for m in matches_without if m.type == PIIType.PHONE]
        if phone_with and phone_without:
            assert phone_with[0].confidence >= phone_without[0].confidence

    def test_ssn_context_keyword_boosts(self, detector):
        text_with_context = "SSN: 123-45-6789"
        text_without = "reference 123-45-6789"
        matches_with = detector.detect(text_with_context)
        matches_without = detector.detect(text_without)
        ssn_with = [m for m in matches_with if m.type == PIIType.SSN]
        ssn_without = [m for m in matches_without if m.type == PIIType.SSN]
        if ssn_with and ssn_without:
            assert ssn_with[0].confidence > ssn_without[0].confidence

    def test_credit_card_context(self, detector):
        text = "My credit card is 4111111111111111"
        matches = detector.detect(text)
        cc = [m for m in matches if m.type == PIIType.CREDIT_CARD]
        assert len(cc) > 0


class TestOverlapRemoval:
    def test_removes_overlapping_lower_confidence(self):
        detector = PIIDetector()
        matches = [
            PIIMatch(type=PIIType.PHONE, value="555-123-4567", start=0, end=12, confidence=0.9),
            PIIMatch(type=PIIType.SSN, value="555-12-3456", start=0, end=11, confidence=0.6),
        ]
        result = detector._remove_overlaps(matches)
        assert len(result) == 1
        assert result[0].type == PIIType.PHONE

    def test_keeps_non_overlapping(self):
        detector = PIIDetector()
        matches = [
            PIIMatch(type=PIIType.EMAIL, value="a@b.com", start=0, end=7, confidence=0.95),
            PIIMatch(type=PIIType.PHONE, value="555-1234", start=20, end=28, confidence=0.9),
        ]
        result = detector._remove_overlaps(matches)
        assert len(result) == 2

    def test_empty_matches(self):
        detector = PIIDetector()
        assert detector._remove_overlaps([]) == []

    def test_higher_confidence_replaces(self):
        detector = PIIDetector()
        matches = [
            PIIMatch(type=PIIType.PHONE, value="555-123-4567", start=0, end=12, confidence=0.7),
            PIIMatch(type=PIIType.SSN, value="555-12-3456", start=0, end=11, confidence=0.95),
        ]
        result = detector._remove_overlaps(matches)
        assert len(result) == 1
        assert result[0].type == PIIType.SSN


class TestPIIRedactor:
    def test_full_redaction(self):
        redactor = PIIRedactor()
        matches = [PIIMatch(type=PIIType.EMAIL, value="test@example.com", start=10, end=26, confidence=0.95)]
        text = "Email is: test@example.com ok?"
        redacted, updated = redactor.redact(text, matches)
        assert "[EMAIL]" in redacted
        assert "test@example.com" not in redacted

    def test_no_matches_returns_original(self):
        redactor = PIIRedactor()
        text = "no PII here"
        redacted, updated = redactor.redact(text, [])
        assert redacted == text

    def test_multiple_redactions(self):
        redactor = PIIRedactor()
        matches = [
            PIIMatch(type=PIIType.EMAIL, value="a@b.com", start=0, end=7, confidence=0.95),
            PIIMatch(type=PIIType.PHONE, value="555-1234", start=20, end=28, confidence=0.9),
        ]
        text = "a@b.com is my email 555-1234 phone"
        redacted, updated = redactor.redact(text, matches)
        assert "[EMAIL]" in redacted
        assert "[PHONE]" in redacted
        assert "a@b.com" not in redacted

    def test_partial_redaction_email(self):
        redactor = PIIRedactor(partial_redact=True)
        match = PIIMatch(type=PIIType.EMAIL, value="test@example.com", start=0, end=16, confidence=0.95)
        result = redactor._partial_redact(match)
        assert result.startswith("t")
        assert "@example.com" in result

    def test_partial_redaction_phone(self):
        redactor = PIIRedactor(partial_redact=True)
        match = PIIMatch(type=PIIType.PHONE, value="555-123-4567", start=0, end=12, confidence=0.9)
        result = redactor._partial_redact(match)
        assert "4567" in result
        assert result.startswith("***")

    def test_partial_redaction_ssn(self):
        redactor = PIIRedactor(partial_redact=True)
        match = PIIMatch(type=PIIType.SSN, value="123-45-6789", start=0, end=11, confidence=0.9)
        result = redactor._partial_redact(match)
        assert "6789" in result
        assert "***-**-" in result

    def test_partial_redaction_credit_card(self):
        redactor = PIIRedactor(partial_redact=True)
        match = PIIMatch(type=PIIType.CREDIT_CARD, value="4111111111111111", start=0, end=16, confidence=0.95)
        result = redactor._partial_redact(match)
        assert "1111" in result
        assert "****" in result

    def test_partial_redaction_api_key(self):
        redactor = PIIRedactor(partial_redact=True)
        match = PIIMatch(type=PIIType.API_KEY, value="sk-abcdefghijklmnop1234", start=0, end=22, confidence=0.9)
        result = redactor._partial_redact(match)
        assert result.startswith("sk-a")
        assert result.endswith("1234")
        assert "..." in result

    def test_partial_redaction_short_api_key_fallback(self):
        redactor = PIIRedactor(partial_redact=True)
        match = PIIMatch(type=PIIType.API_KEY, value="sk-short", start=0, end=8, confidence=0.9)
        result = redactor._partial_redact(match)
        assert result == "[API_KEY]"

    def test_partial_redaction_unknown_type(self):
        redactor = PIIRedactor(partial_redact=True)
        match = PIIMatch(type=PIIType.NAME, value="John Doe", start=0, end=8, confidence=0.9)
        result = redactor._partial_redact(match)
        assert result == "[NAME]"

    def test_full_redaction_unknown_type(self):
        redactor = PIIRedactor()
        match = PIIMatch(type=PIIType.DRIVER_LICENSE, value="DL12345", start=0, end=7, confidence=0.9)
        result = redactor._get_redaction(match)
        assert result == "[LICENSE]"
