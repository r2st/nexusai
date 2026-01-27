"""PHI (Protected Health Information) Detection Service."""

import hashlib
import logging
import re
import uuid
from datetime import datetime
from typing import Any

from app.services.compliance.hipaa.models import (
    PHICategory,
    PHIDetectionResult,
    PHIPattern,
)

logger = logging.getLogger(__name__)

# Singleton instance
_phi_detector: "PHIDetector | None" = None

# Default PHI detection patterns
DEFAULT_PHI_PATTERNS = [
    # Direct Identifiers
    PHIPattern(
        category=PHICategory.SSN,
        pattern=r"\b\d{3}-\d{2}-\d{4}\b",
        description="Social Security Number (XXX-XX-XXXX)",
        confidence=0.95,
    ),
    PHIPattern(
        category=PHICategory.SSN,
        pattern=r"\b\d{9}\b(?=.*(?:ssn|social|security))",
        description="SSN without dashes near keyword",
        confidence=0.85,
    ),
    PHIPattern(
        category=PHICategory.MRN,
        pattern=r"\b(?:MRN|Medical Record|Patient ID)[:\s#]*([A-Z0-9]{6,12})\b",
        description="Medical Record Number",
        confidence=0.90,
    ),
    PHIPattern(
        category=PHICategory.HEALTH_PLAN_ID,
        pattern=r"\b(?:Member ID|Plan ID|Insurance ID)[:\s#]*([A-Z0-9]{8,15})\b",
        description="Health Plan Beneficiary ID",
        confidence=0.85,
    ),
    PHIPattern(
        category=PHICategory.PHONE,
        pattern=r"\b(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        description="US Phone Number",
        confidence=0.80,
    ),
    PHIPattern(
        category=PHICategory.FAX,
        pattern=r"\b(?:fax|facsimile)[:\s]*(?:\+1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b",
        description="Fax Number",
        confidence=0.85,
    ),
    PHIPattern(
        category=PHICategory.EMAIL,
        pattern=r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b",
        description="Email Address",
        confidence=0.90,
    ),
    PHIPattern(
        category=PHICategory.DATES,
        pattern=r"\b(?:DOB|Date of Birth|Birth Date|Birthdate)[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
        description="Date of Birth",
        confidence=0.95,
    ),
    PHIPattern(
        category=PHICategory.DATES,
        pattern=r"\b(?:admission|discharge|death|deceased)[:\s]*(?:date)?[:\s]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})\b",
        description="Healthcare-related dates",
        confidence=0.90,
    ),
    PHIPattern(
        category=PHICategory.IP_ADDRESS,
        pattern=r"\b(?:\d{1,3}\.){3}\d{1,3}\b",
        description="IP Address",
        confidence=0.70,
    ),
    PHIPattern(
        category=PHICategory.LICENSE_NUMBER,
        pattern=r"\b(?:License|DL|Driver)[:\s#]*([A-Z]{1,2}\d{6,8})\b",
        description="Driver's License Number",
        confidence=0.80,
    ),
    PHIPattern(
        category=PHICategory.ACCOUNT_NUMBER,
        pattern=r"\b(?:Account|Acct)[:\s#]*(\d{8,17})\b",
        description="Account Number",
        confidence=0.75,
    ),
    PHIPattern(
        category=PHICategory.DEVICE_ID,
        pattern=r"\b(?:Device ID|IMEI|Serial)[:\s#]*([A-Z0-9]{10,20})\b",
        description="Device Identifier",
        confidence=0.80,
    ),
    PHIPattern(
        category=PHICategory.VEHICLE_ID,
        pattern=r"\b(?:VIN|Vehicle)[:\s#]*([A-HJ-NPR-Z0-9]{17})\b",
        description="Vehicle Identification Number",
        confidence=0.90,
    ),

    # Clinical Data Patterns
    PHIPattern(
        category=PHICategory.DIAGNOSIS,
        pattern=r"\b(?:diagnosis|dx|diagnosed with)[:\s]*([A-Za-z\s]{5,50})\b",
        description="Diagnosis/Condition",
        confidence=0.75,
    ),
    PHIPattern(
        category=PHICategory.DIAGNOSIS,
        pattern=r"\b(?:ICD-?10?)[:\s-]*([A-Z]\d{2}(?:\.\d{1,4})?)\b",
        description="ICD-10 Code",
        confidence=0.95,
    ),
    PHIPattern(
        category=PHICategory.MEDICATION,
        pattern=r"\b(?:prescribed|medication|rx|taking)[:\s]*([A-Za-z]+\s*\d*\s*mg)\b",
        description="Medication with dosage",
        confidence=0.80,
    ),
    PHIPattern(
        category=PHICategory.PROCEDURE,
        pattern=r"\b(?:CPT|procedure code)[:\s-]*(\d{5})\b",
        description="CPT Procedure Code",
        confidence=0.95,
    ),
    PHIPattern(
        category=PHICategory.LAB_RESULT,
        pattern=r"\b(?:A1C|glucose|cholesterol|CBC|BMP)[:\s]*(\d+(?:\.\d+)?)\b",
        description="Lab Result Value",
        confidence=0.75,
    ),
    PHIPattern(
        category=PHICategory.VITAL_SIGN,
        pattern=r"\b(?:BP|blood pressure)[:\s]*(\d{2,3}/\d{2,3})\b",
        description="Blood Pressure Reading",
        confidence=0.85,
    ),
    PHIPattern(
        category=PHICategory.ALLERGY,
        pattern=r"\b(?:allergic to|allergy)[:\s]*([A-Za-z\s,]+)\b",
        description="Allergy Information",
        confidence=0.80,
    ),

    # Administrative Patterns
    PHIPattern(
        category=PHICategory.INSURANCE_INFO,
        pattern=r"\b(?:insurance|insurer|payer)[:\s]*([A-Za-z\s]+(?:Health|Insurance|Plan))\b",
        description="Insurance Company",
        confidence=0.75,
    ),
    PHIPattern(
        category=PHICategory.PROVIDER_INFO,
        pattern=r"\b(?:NPI|Provider ID)[:\s#]*(\d{10})\b",
        description="National Provider Identifier",
        confidence=0.95,
    ),
]


class PHIDetector:
    """Service for detecting PHI in text content.

    Implements HIPAA-compliant PHI detection for the 18 HIPAA identifiers
    plus clinical and administrative healthcare data.
    """

    def __init__(self, patterns: list[PHIPattern] | None = None):
        self._patterns = patterns or DEFAULT_PHI_PATTERNS
        self._compiled_patterns: dict[str, re.Pattern] = {}
        self._compile_patterns()

    def _compile_patterns(self) -> None:
        """Pre-compile regex patterns for performance."""
        for pattern in self._patterns:
            if pattern.enabled:
                try:
                    self._compiled_patterns[pattern.pattern] = re.compile(
                        pattern.pattern,
                        re.IGNORECASE | re.MULTILINE
                    )
                except re.error as e:
                    logger.warning(f"Invalid pattern {pattern.pattern}: {e}")

    async def detect(
        self,
        content: str,
        categories: list[PHICategory] | None = None,
        min_confidence: float = 0.7,
    ) -> PHIDetectionResult:
        """Detect PHI in content.

        Args:
            content: Text content to scan
            categories: Optional filter for specific PHI categories
            min_confidence: Minimum confidence threshold for findings

        Returns:
            PHIDetectionResult with all findings
        """
        content_hash = hashlib.sha256(content.encode()).hexdigest()[:16]

        result = PHIDetectionResult(
            id=str(uuid.uuid4()),
            content_hash=content_hash,
        )

        findings: list[dict[str, Any]] = []
        categories_found: set[PHICategory] = set()

        for pattern in self._patterns:
            # Filter by category if specified
            if categories and pattern.category not in categories:
                continue

            # Skip low confidence patterns
            if pattern.confidence < min_confidence:
                continue

            if not pattern.enabled:
                continue

            compiled = self._compiled_patterns.get(pattern.pattern)
            if not compiled:
                continue

            # Find all matches
            for match in compiled.finditer(content):
                finding = {
                    "category": pattern.category.value,
                    "pattern_description": pattern.description,
                    "confidence": pattern.confidence,
                    "match": match.group(0),
                    "start": match.start(),
                    "end": match.end(),
                    "context": self._get_context(content, match.start(), match.end()),
                }
                findings.append(finding)
                categories_found.add(pattern.category)

        # Deduplicate overlapping findings
        findings = self._deduplicate_findings(findings)

        # Calculate statistics
        high_conf = len([f for f in findings if f["confidence"] >= 0.9])
        medium_conf = len([f for f in findings if 0.75 <= f["confidence"] < 0.9])
        low_conf = len([f for f in findings if f["confidence"] < 0.75])

        result.phi_found = len(findings) > 0
        result.findings = findings
        result.categories_detected = list(categories_found)
        result.total_findings = len(findings)
        result.high_confidence_findings = high_conf
        result.medium_confidence_findings = medium_conf
        result.low_confidence_findings = low_conf

        # Generate recommendations
        if result.phi_found:
            result.redaction_required = True
            result.recommendations = self._generate_recommendations(findings, categories_found)

        return result

    async def detect_in_code(
        self,
        code: str,
        language: str | None = None,
    ) -> PHIDetectionResult:
        """Detect PHI in source code.

        Handles code-specific patterns like string literals, comments, etc.
        """
        # Extract string literals and comments for scanning
        content_to_scan = code

        # For better accuracy, focus on strings and comments
        string_patterns = [
            r'"([^"\\]|\\.)*"',  # Double-quoted strings
            r"'([^'\\]|\\.)*'",  # Single-quoted strings
            r'"""[\s\S]*?"""',  # Python docstrings
            r"'''[\s\S]*?'''",  # Python docstrings
            r"//.*$",  # Single-line comments
            r"/\*[\s\S]*?\*/",  # Multi-line comments
            r"#.*$",  # Hash comments
        ]

        extracted_content = []
        for pattern in string_patterns:
            matches = re.findall(pattern, code, re.MULTILINE)
            extracted_content.extend(matches)

        # Scan both full code and extracted content
        full_result = await self.detect(code)
        if extracted_content:
            extracted_result = await self.detect(" ".join(str(m) for m in extracted_content))
            # Merge results, prioritizing extracted content findings
            for finding in extracted_result.findings:
                if finding not in full_result.findings:
                    full_result.findings.append(finding)

        # Add code-specific recommendations
        if full_result.phi_found:
            full_result.recommendations.append(
                "Consider using environment variables or secure vaults for sensitive data"
            )
            full_result.recommendations.append(
                "Implement data masking in logs and error messages"
            )

        return full_result

    def _get_context(self, content: str, start: int, end: int, window: int = 30) -> str:
        """Get surrounding context for a match."""
        context_start = max(0, start - window)
        context_end = min(len(content), end + window)
        context = content[context_start:context_end]

        # Mask the actual PHI in context
        match_in_context = content[start:end]
        masked = "*" * len(match_in_context)
        context = context.replace(match_in_context, masked, 1)

        return f"...{context}..."

    def _deduplicate_findings(self, findings: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Remove overlapping findings, keeping higher confidence ones."""
        if not findings:
            return findings

        # Sort by confidence (descending) then by position
        sorted_findings = sorted(
            findings,
            key=lambda f: (-f["confidence"], f["start"])
        )

        deduplicated = []
        covered_ranges: list[tuple[int, int]] = []

        for finding in sorted_findings:
            start, end = finding["start"], finding["end"]

            # Check if this range overlaps with any already covered
            overlaps = False
            for cov_start, cov_end in covered_ranges:
                if not (end <= cov_start or start >= cov_end):
                    overlaps = True
                    break

            if not overlaps:
                deduplicated.append(finding)
                covered_ranges.append((start, end))

        return deduplicated

    def _generate_recommendations(
        self,
        findings: list[dict[str, Any]],
        categories: set[PHICategory],
    ) -> list[str]:
        """Generate recommendations based on findings."""
        recommendations = []

        if PHICategory.SSN in categories:
            recommendations.append(
                "CRITICAL: Social Security Numbers detected - implement immediate redaction"
            )

        if PHICategory.MRN in categories or PHICategory.HEALTH_PLAN_ID in categories:
            recommendations.append(
                "Medical identifiers detected - ensure proper access controls are in place"
            )

        if any(c in categories for c in [PHICategory.DIAGNOSIS, PHICategory.MEDICATION, PHICategory.LAB_RESULT]):
            recommendations.append(
                "Clinical data detected - verify minimum necessary access is enforced"
            )

        if PHICategory.DATES in categories:
            recommendations.append(
                "Date information detected - consider de-identification (e.g., year only)"
            )

        if len(categories) > 3:
            recommendations.append(
                "Multiple PHI categories detected - comprehensive data review recommended"
            )

        recommendations.append(
            "Review HIPAA Safe Harbor de-identification standards for data sharing"
        )

        return recommendations

    def add_pattern(self, pattern: PHIPattern) -> None:
        """Add a custom detection pattern."""
        self._patterns.append(pattern)
        if pattern.enabled:
            try:
                self._compiled_patterns[pattern.pattern] = re.compile(
                    pattern.pattern,
                    re.IGNORECASE | re.MULTILINE
                )
            except re.error as e:
                logger.warning(f"Invalid pattern {pattern.pattern}: {e}")

    def get_patterns(self, category: PHICategory | None = None) -> list[PHIPattern]:
        """Get configured patterns, optionally filtered by category."""
        if category:
            return [p for p in self._patterns if p.category == category]
        return self._patterns.copy()


def get_phi_detector() -> PHIDetector:
    """Get or create the PHI detector singleton."""
    global _phi_detector

    if _phi_detector is None:
        _phi_detector = PHIDetector()

    return _phi_detector
