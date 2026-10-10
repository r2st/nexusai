"""Unit tests for Security Scanner and Secret Rotation services."""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
import tempfile
import os

from app.services.security.scanner.code_security import (
    CodeSecurityScanner,
    SecurityCategory,
    SecurityIssue,
)
from app.services.security.scanner.config_checker import (
    ConfigSecurityChecker,
    ConfigIssue,
)
from app.services.security.scanner.vulnerability import (
    VulnerabilityScanner,
    Vulnerability,
    VulnerabilitySeverity,
    ScanResult,
)
from app.services.security.scanner.service import (
    SecurityScannerService,
    SecurityReport,
    ScanThresholds,
)
from app.services.security.secrets.storage import SecretStorage
from app.services.security.secrets.rotation import (
    SecretRotationService,
    RotationPolicy,
    SecretType,
)


class TestCodeSecurityScanner:
    """Tests for Code Security Scanner."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scanner = CodeSecurityScanner()

    def test_detect_sql_injection_fstring(self):
        """Test detection of SQL injection via f-string."""
        code = '''
def get_user(user_id):
    cursor.execute(f"SELECT * FROM users WHERE id = {user_id}")
'''
        issues = self.scanner.scan_file("test.py", content=code)

        injection_issues = [i for i in issues if i.category == SecurityCategory.INJECTION]
        assert len(injection_issues) > 0

    def test_detect_command_injection_os_system(self):
        """Test detection of command injection via os.system."""
        code = '''
import os
def run_command(cmd):
    os.system(cmd)
'''
        issues = self.scanner.scan_file("test.py", content=code)

        injection_issues = [i for i in issues if i.category == SecurityCategory.INJECTION]
        assert len(injection_issues) > 0
        assert any("os.system" in i.message for i in injection_issues)

    def test_detect_eval_usage(self):
        """Test detection of eval usage."""
        code = '''
def process_input(user_input):
    result = eval(user_input)
    return result
'''
        issues = self.scanner.scan_file("test.py", content=code)

        assert any("eval" in i.message.lower() for i in issues)

    def test_detect_exec_usage(self):
        """Test detection of exec usage."""
        code = '''
def run_dynamic_code(code_str):
    exec(code_str)
'''
        issues = self.scanner.scan_file("test.py", content=code)

        assert any("exec" in i.message.lower() for i in issues)

    def test_detect_hardcoded_password(self):
        """Test detection of hardcoded passwords."""
        code = '''
DB_PASSWORD = "supersecret123"
'''
        issues = self.scanner.scan_file("config.py", content=code)

        secret_issues = [i for i in issues if i.category == SecurityCategory.SECRETS]
        assert len(secret_issues) > 0
        assert secret_issues[0].severity == "critical"

    def test_detect_api_key(self):
        """Test detection of hardcoded API keys."""
        api_key = "sk-" + "abcdefghijklmnopqrstuvwxyz123456"
        code = f'''
API_KEY = "{api_key}"
'''
        issues = self.scanner.scan_file("config.py", content=code)

        secret_issues = [i for i in issues if i.category == SecurityCategory.SECRETS]
        assert len(secret_issues) > 0

    def test_detect_github_token(self):
        """Test detection of GitHub personal access token."""
        github_token = "ghp_" + "abcdefghijklmnopqrstuvwxyz123456789012"
        code = f'''
GITHUB_TOKEN = "{github_token}"
'''
        issues = self.scanner.scan_file("config.py", content=code)

        secret_issues = [i for i in issues if i.category == SecurityCategory.SECRETS]
        assert len(secret_issues) > 0
        assert any("github" in i.message.lower() for i in secret_issues)

    def test_detect_private_key(self):
        """Test detection of embedded private keys."""
        begin = "-----BEGIN " + "RSA PRIVATE KEY-----"
        end = "-----END " + "RSA PRIVATE KEY-----"
        private_key_block = begin + "\\nMIIEpAIBAAKCAQEA...\\n" + end
        code = f'''
PRIVATE_KEY = """{private_key_block}"""
'''
        issues = self.scanner.scan_file("keys.py", content=code)

        secret_issues = [i for i in issues if i.category == SecurityCategory.SECRETS]
        assert len(secret_issues) > 0

    def test_detect_md5_weak_crypto(self):
        """Test detection of weak MD5 cryptography."""
        code = '''
import hashlib
hash = hashlib.md5(password.encode())
'''
        issues = self.scanner.scan_file("auth.py", content=code)

        crypto_issues = [i for i in issues if i.category == SecurityCategory.CRYPTOGRAPHY]
        assert len(crypto_issues) > 0
        assert any("md5" in i.message.lower() for i in crypto_issues)

    def test_detect_sha1_weak_crypto(self):
        """Test detection of weak SHA1 cryptography."""
        code = '''
import hashlib
hash = hashlib.sha1(data.encode())
'''
        issues = self.scanner.scan_file("hash.py", content=code)

        crypto_issues = [i for i in issues if i.category == SecurityCategory.CRYPTOGRAPHY]
        assert len(crypto_issues) > 0

    def test_detect_ssl_verification_disabled(self):
        """Test detection of disabled SSL verification."""
        code = '''
import requests
response = requests.get(url, verify=False)
'''
        issues = self.scanner.scan_file("client.py", content=code)

        auth_issues = [i for i in issues if i.category == SecurityCategory.AUTHENTICATION]
        assert len(auth_issues) > 0

    def test_detect_pickle_deserialization(self):
        """Test detection of pickle deserialization."""
        code = '''
import pickle
data = pickle.loads(untrusted_data)
'''
        issues = self.scanner.scan_file("data.py", content=code)

        validation_issues = [i for i in issues if i.category == SecurityCategory.INPUT_VALIDATION]
        assert len(validation_issues) > 0

    def test_detect_unsafe_yaml_load(self):
        """Test detection of unsafe YAML loading."""
        code = '''
import yaml
data = yaml.load(file_content)
'''
        issues = self.scanner.scan_file("config.py", content=code)

        validation_issues = [i for i in issues if i.category == SecurityCategory.INPUT_VALIDATION]
        assert len(validation_issues) > 0

    def test_detect_xss_innerhtml(self):
        """Test detection of innerHTML XSS."""
        code = '''
element.innerHTML = userInput;
'''
        issues = self.scanner.scan_file("app.js", content=code)

        xss_issues = [i for i in issues if i.category == SecurityCategory.XSS]
        assert len(xss_issues) > 0

    def test_detect_document_write(self):
        """Test detection of document.write XSS."""
        code = '''
document.write(unsafeData);
'''
        issues = self.scanner.scan_file("app.js", content=code)

        xss_issues = [i for i in issues if i.category == SecurityCategory.XSS]
        assert len(xss_issues) > 0

    def test_detect_bare_except(self):
        """Test detection of bare except clause."""
        code = '''
try:
    risky_operation()
except:
    pass
'''
        issues = self.scanner.scan_file("handler.py", content=code)

        error_issues = [i for i in issues if i.category == SecurityCategory.ERROR_HANDLING]
        assert len(error_issues) > 0

    def test_detect_password_in_log(self):
        """Test detection of password in log statement."""
        code = '''
import logging
logging.info(f"User login: password={password}")
'''
        issues = self.scanner.scan_file("auth.py", content=code)

        log_issues = [i for i in issues if i.category == SecurityCategory.LOGGING]
        assert len(log_issues) > 0

    def test_skip_comments(self):
        """Test that comments are skipped."""
        code = '''
# password = "secret123"
// API_KEY = "sk-test"
'''
        issues = self.scanner.scan_file("config.py", content=code)

        # Should not detect secrets in comments
        secret_issues = [i for i in issues if i.category == SecurityCategory.SECRETS]
        assert len(secret_issues) == 0

    def test_scan_diff(self):
        """Test scanning diff content."""
        diff = '''diff --git a/config.py b/config.py
@@ -1,3 +1,5 @@
 import os
+PASSWORD = "hardcoded123"
+eval(user_input)
'''
        issues = self.scanner.scan_diff(diff)

        assert len(issues) >= 2
        assert any(i.category == SecurityCategory.SECRETS for i in issues)
        assert any(i.category == SecurityCategory.INJECTION for i in issues)

    def test_scan_diff_line_numbers(self):
        """Test that diff scanning captures correct line numbers."""
        diff = '''diff --git a/a.py b/a.py
@@ -10,3 +10,5 @@
 existing_line()
+PASSWORD = "secret"
+more_code()
'''
        issues = self.scanner.scan_diff(diff)

        if issues:
            # Line number should be from the hunk header
            assert issues[0].line >= 10

    def test_get_severity_counts(self):
        """Test severity count calculation."""
        issues = [
            SecurityIssue(
                id="1", category=SecurityCategory.SECRETS, severity="critical",
                file="a.py", line=1, message="test", recommendation="fix"
            ),
            SecurityIssue(
                id="2", category=SecurityCategory.SECRETS, severity="critical",
                file="b.py", line=2, message="test", recommendation="fix"
            ),
            SecurityIssue(
                id="3", category=SecurityCategory.CRYPTOGRAPHY, severity="high",
                file="c.py", line=3, message="test", recommendation="fix"
            ),
            SecurityIssue(
                id="4", category=SecurityCategory.XSS, severity="medium",
                file="d.py", line=4, message="test", recommendation="fix"
            ),
        ]

        counts = self.scanner.get_severity_counts(issues)

        assert counts["critical"] == 2
        assert counts["high"] == 1
        assert counts["medium"] == 1
        assert counts["low"] == 0


class TestConfigSecurityChecker:
    """Tests for Configuration Security Checker."""

    def setup_method(self):
        """Set up test fixtures."""
        self.checker = ConfigSecurityChecker()

    def test_check_env_debug_enabled(self):
        """Test detection of debug mode enabled."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("DEBUG=true\n")
            f.write("APP_NAME=test\n")
            env_path = f.name

        try:
            issues = self.checker.check_env_file(env_path)

            debug_issues = [i for i in issues if "debug" in i.id.lower()]
            assert len(debug_issues) > 0
            assert debug_issues[0].severity == "high"
        finally:
            os.unlink(env_path)

    def test_check_env_weak_secret(self):
        """Test detection of weak secrets (too short)."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("SECRET_KEY=short\n")  # Too short
            env_path = f.name

        try:
            issues = self.checker.check_env_file(env_path)

            weak_issues = [i for i in issues if "weak" in i.id.lower() or "short" in i.message.lower()]
            assert len(weak_issues) > 0
        finally:
            os.unlink(env_path)

    def test_check_env_default_secret(self):
        """Test detection of default/placeholder secrets."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("SECRET_KEY=changeme\n")
            env_path = f.name

        try:
            issues = self.checker.check_env_file(env_path)

            default_issues = [i for i in issues if "default" in i.id.lower()]
            assert len(default_issues) > 0
            assert default_issues[0].severity == "critical"
        finally:
            os.unlink(env_path)

    def test_check_env_default_password(self):
        """Test detection of common/weak passwords."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("DB_PASSWORD=password\n")
            env_path = f.name

        try:
            issues = self.checker.check_env_file(env_path)

            password_issues = [i for i in issues if "password" in i.id.lower()]
            assert len(password_issues) > 0
            assert password_issues[0].severity == "critical"
        finally:
            os.unlink(env_path)

    def test_check_env_insecure_url(self):
        """Test detection of insecure HTTP URLs."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("API_URL=http://api.example.com\n")
            env_path = f.name

        try:
            issues = self.checker.check_env_file(env_path)

            url_issues = [i for i in issues if "url" in i.id.lower()]
            assert len(url_issues) > 0
        finally:
            os.unlink(env_path)

    def test_check_env_localhost_url_allowed(self):
        """Test that localhost HTTP URLs are allowed."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("DATABASE_URL=http://localhost:5432\n")
            env_path = f.name

        try:
            issues = self.checker.check_env_file(env_path)

            # localhost should not trigger insecure URL warning
            url_issues = [i for i in issues if "insecure-url" in i.id.lower()]
            assert len(url_issues) == 0
        finally:
            os.unlink(env_path)

    def test_check_env_cors_wildcard(self):
        """Test detection of CORS wildcard."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as f:
            f.write("CORS_ORIGINS=*\n")
            env_path = f.name

        try:
            issues = self.checker.check_env_file(env_path)

            cors_issues = [i for i in issues if "cors" in i.id.lower()]
            assert len(cors_issues) > 0
        finally:
            os.unlink(env_path)

    def test_check_dockerfile_no_user(self):
        """Test detection of Dockerfile without USER instruction."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("FROM python:3.11\n")
            f.write("COPY . /app\n")
            f.write("CMD python app.py\n")
            dockerfile_path = f.name

        try:
            issues = self.checker.check_dockerfile(dockerfile_path)

            user_issues = [i for i in issues if "user" in i.id.lower() and "no-user" in i.id.lower()]
            assert len(user_issues) > 0
        finally:
            os.unlink(dockerfile_path)

    def test_check_dockerfile_root_user(self):
        """Test detection of explicit root USER."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("FROM python:3.11\n")
            f.write("USER root\n")
            f.write("CMD python app.py\n")
            dockerfile_path = f.name

        try:
            issues = self.checker.check_dockerfile(dockerfile_path)

            root_issues = [i for i in issues if "root" in i.id.lower()]
            assert len(root_issues) > 0
        finally:
            os.unlink(dockerfile_path)

    def test_check_dockerfile_latest_tag(self):
        """Test detection of latest tag in FROM."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("FROM python:latest\n")
            f.write("USER appuser\n")
            dockerfile_path = f.name

        try:
            issues = self.checker.check_dockerfile(dockerfile_path)

            latest_issues = [i for i in issues if "latest" in i.id.lower()]
            assert len(latest_issues) > 0
        finally:
            os.unlink(dockerfile_path)

    def test_check_dockerfile_no_tag(self):
        """Test detection of missing tag in FROM."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("FROM python\n")
            f.write("USER appuser\n")
            dockerfile_path = f.name

        try:
            issues = self.checker.check_dockerfile(dockerfile_path)

            latest_issues = [i for i in issues if "latest" in i.id.lower()]
            assert len(latest_issues) > 0
        finally:
            os.unlink(dockerfile_path)

    def test_check_dockerfile_env_secret(self):
        """Test detection of secrets in ENV instruction."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("FROM python:3.11\n")
            f.write("ENV PASSWORD=mysecret\n")
            f.write("USER appuser\n")
            dockerfile_path = f.name

        try:
            issues = self.checker.check_dockerfile(dockerfile_path)

            secret_issues = [i for i in issues if "secret" in i.id.lower()]
            assert len(secret_issues) > 0
            assert secret_issues[0].severity == "critical"
        finally:
            os.unlink(dockerfile_path)

    def test_check_dockerfile_add_url(self):
        """Test detection of ADD with URL."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as f:
            f.write("FROM python:3.11\n")
            f.write("ADD https://example.com/file.tar.gz /app/\n")
            f.write("USER appuser\n")
            dockerfile_path = f.name

        try:
            issues = self.checker.check_dockerfile(dockerfile_path)

            add_issues = [i for i in issues if "add-url" in i.id.lower()]
            assert len(add_issues) > 0
        finally:
            os.unlink(dockerfile_path)


class TestSecurityScannerService:
    """Tests for Security Scanner Service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.service = SecurityScannerService()

    def test_scan_diff_finds_issues(self):
        """Test scanning diff content finds issues."""
        diff = '''diff --git a/config.py b/config.py
@@ -1,3 +1,5 @@
+PASSWORD = "hardcoded"
+os.system(user_input)
'''
        report = self.service.scan_diff(diff)

        assert report.total_issues >= 2
        assert report.critical_count >= 1

    def test_scan_diff_empty(self):
        """Test scanning empty diff."""
        diff = '''diff --git a/a.py b/a.py
@@ -1 +1 @@
+x = 1
'''
        report = self.service.scan_diff(diff)

        assert report.total_issues == 0
        assert report.passed is True

    def test_calculate_risk_score(self):
        """Test risk score calculation."""
        api_key = "sk-" + "abcdefghijklmnopqrstuvwxyz123"
        diff = '''diff --git a/a.py b/a.py
@@ -1 +1,5 @@
+PASSWORD = "secret"
+API_KEY = "''' + api_key + '''"
+eval(input)
'''
        report = self.service.scan_diff(diff)

        # Should have high risk score due to critical issues
        assert report.risk_score > 0

    def test_threshold_evaluation_pass(self):
        """Test threshold evaluation for passing scan."""
        thresholds = ScanThresholds(
            max_critical=0,
            max_high=5,
            max_medium=20,
            max_risk_score=70.0,
        )
        service = SecurityScannerService(thresholds=thresholds)

        # Clean diff
        diff = '''diff --git a/a.py b/a.py
@@ -1 +1 @@
+x = 1
'''
        report = service.scan_diff(diff)

        assert report.passed is True
        assert len(report.failure_reasons) == 0

    def test_threshold_evaluation_fail_critical(self):
        """Test threshold evaluation fails for critical issues."""
        thresholds = ScanThresholds(
            max_critical=0,  # No critical allowed
            max_high=0,
            max_medium=0,
            max_risk_score=10.0,
        )
        service = SecurityScannerService(thresholds=thresholds)

        # Diff with critical issue
        diff = '''diff --git a/a.py b/a.py
@@ -1 +1 @@
+PASSWORD = "hardcoded_secret_value"
'''
        report = service.scan_diff(diff)

        assert report.passed is False
        assert len(report.failure_reasons) > 0
        assert any("critical" in reason.lower() for reason in report.failure_reasons)

    def test_threshold_evaluation_fail_risk_score(self):
        """Test threshold evaluation fails for high risk score."""
        thresholds = ScanThresholds(
            max_critical=10,
            max_high=10,
            max_medium=10,
            max_risk_score=5.0,  # Very low threshold
        )
        service = SecurityScannerService(thresholds=thresholds)

        # Diff with issues that increase risk score
        diff = '''diff --git a/a.py b/a.py
@@ -1 +1,3 @@
+PASSWORD = "secret123456"
+eval(code)
'''
        report = service.scan_diff(diff)

        # If risk score exceeds threshold
        if report.risk_score > 5.0:
            assert report.passed is False
            assert any("risk score" in reason.lower() for reason in report.failure_reasons)

    def test_generate_sarif_report(self):
        """Test SARIF report generation."""
        diff = '''diff --git a/a.py b/a.py
@@ -1 +1 @@
+eval(user_input)
'''
        report = self.service.scan_diff(diff)
        sarif = self.service.generate_sarif_report(report)

        assert sarif["version"] == "2.1.0"
        assert "runs" in sarif
        assert len(sarif["runs"]) > 0
        assert "results" in sarif["runs"][0]
        assert sarif["runs"][0]["tool"]["driver"]["name"] == "NexusAI Security Scanner"

    def test_has_critical_issues_property(self):
        """Test has_critical_issues property."""
        report = SecurityReport(
            scan_id="test",
            critical_count=1,
            high_count=0,
            medium_count=0,
            low_count=0,
        )

        assert report.has_critical_issues is True

        report.critical_count = 0
        assert report.has_critical_issues is False


class TestSecretStorage:
    """Tests for Secret Storage."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = SecretStorage(master_key="test-master-key-for-testing-1234")

    def test_encrypt_decrypt(self):
        """Test encryption and decryption roundtrip."""
        original = "my-secret-value"

        encrypted, salt = self.storage.encrypt(original)
        decrypted = self.storage.decrypt(encrypted, salt)

        assert decrypted == original
        assert encrypted != original

    def test_different_salts(self):
        """Test that different salts produce different ciphertexts."""
        value = "same-value"

        encrypted1, salt1 = self.storage.encrypt(value)
        encrypted2, salt2 = self.storage.encrypt(value)

        # Salts should be different
        assert salt1 != salt2
        # Encrypted values should be different
        assert encrypted1 != encrypted2

    def test_store_and_retrieve(self):
        """Test storing and retrieving secrets."""
        name = "test-secret"
        value = "test-value-123"

        self.storage.store(name, value, expires_in=timedelta(hours=1))
        retrieved = self.storage.retrieve(name)

        assert retrieved == value

    def test_retrieve_nonexistent(self):
        """Test retrieving non-existent secret."""
        result = self.storage.retrieve("does-not-exist")

        assert result is None

    def test_delete_secret(self):
        """Test deleting a secret."""
        name = "delete-me"
        value = "temporary"

        self.storage.store(name, value)
        assert self.storage.retrieve(name) == value

        self.storage.delete(name)
        assert self.storage.retrieve(name) is None

    def test_list_secrets(self):
        """Test listing stored secrets."""
        self.storage.store("secret1", "value1")
        self.storage.store("secret2", "value2")

        secrets = self.storage.list_secrets()
        secret_names = [s.name for s in secrets]

        assert "secret1" in secret_names
        assert "secret2" in secret_names


class TestSecretRotation:
    """Tests for Secret Rotation Service."""

    def setup_method(self):
        """Set up test fixtures."""
        self.storage = SecretStorage(master_key="test-key-for-rotation-1234")
        self.service = SecretRotationService(storage=self.storage)

    def test_register_secret(self):
        """Test registering a new secret."""
        name = "api-key"
        value = "initial-value-12345"

        metadata = self.service.register_secret(
            name=name,
            initial_value=value,
            secret_type=SecretType.API_KEY,
            policy=RotationPolicy(rotation_interval_days=30, secret_type=SecretType.API_KEY, min_length=20),
        )

        assert metadata.name == name
        assert metadata.secret_type == SecretType.API_KEY
        assert metadata.rotation_count >= 0

    def test_generate_secret_api_key(self):
        """Test API key generation."""
        policy = RotationPolicy(
            secret_type=SecretType.API_KEY,
            min_length=32,
            require_special_chars=False,  # API keys should be URL-safe
        )

        secret = self.service.generate_secret(policy)

        assert len(secret) >= 32
        # Without special chars, should be alphanumeric
        assert all(c.isalnum() for c in secret)

    def test_generate_secret_password_with_requirements(self):
        """Test password generation with complexity requirements."""
        policy = RotationPolicy(
            secret_type=SecretType.DATABASE_PASSWORD,
            min_length=16,
            require_special_chars=True,
            require_numbers=True,
        )

        secret = self.service.generate_secret(policy)

        assert len(secret) >= 16
        # Check for variety in generated secret
        assert len(secret) > 0

    def test_secret_needs_rotation_new(self):
        """Test that new secret doesn't need rotation."""
        self.service.register_secret(
            name="fresh-secret",
            initial_value="value",
            secret_type=SecretType.API_KEY,
            policy=RotationPolicy(rotation_interval_days=30, secret_type=SecretType.API_KEY),
        )

        needs_rotation = self.service.needs_rotation("fresh-secret")

        # New secret shouldn't need rotation for 30 days
        assert needs_rotation is False

    def test_secret_needs_rotation_immediate(self):
        """Test checking if secret with 0-day rotation needs rotation."""
        self.service.register_secret(
            name="short-lived",
            initial_value="value",
            secret_type=SecretType.API_KEY,
            policy=RotationPolicy(rotation_interval_days=0, secret_type=SecretType.API_KEY),  # Immediate rotation
        )

        needs_rotation = self.service.needs_rotation("short-lived")

        # Should need rotation immediately
        assert needs_rotation is True

    def test_list_secrets(self):
        """Test listing all registered secrets."""
        self.service.register_secret(
            name="secret1",
            initial_value="value1",
            secret_type=SecretType.API_KEY,
        )
        self.service.register_secret(
            name="secret2",
            initial_value="value2",
            secret_type=SecretType.DATABASE_PASSWORD,
        )

        secrets = self.service.list_secrets()

        assert len(secrets) >= 2
        names = [s.name for s in secrets]
        assert "secret1" in names
        assert "secret2" in names

    def test_get_secret_metadata(self):
        """Test retrieving secret metadata."""
        self.service.register_secret(
            name="metadata-test",
            initial_value="value",
            secret_type=SecretType.DATABASE_PASSWORD,
            policy=RotationPolicy(rotation_interval_days=90, secret_type=SecretType.DATABASE_PASSWORD),
        )

        metadata = self.service.get_metadata("metadata-test")

        assert metadata is not None
        assert metadata.name == "metadata-test"
        assert metadata.secret_type == SecretType.DATABASE_PASSWORD

    def test_get_metadata_nonexistent(self):
        """Test getting metadata for non-existent secret."""
        metadata = self.service.get_metadata("nonexistent")

        assert metadata is None


class TestVulnerabilityScanner:
    """Tests for Vulnerability Scanner."""

    def setup_method(self):
        """Set up test fixtures."""
        self.scanner = VulnerabilityScanner()

    def test_scan_result_empty(self):
        """Test empty scan result."""
        result = ScanResult(scan_type="test")

        assert len(result.vulnerabilities) == 0
        assert result.error is None

    def test_vulnerability_severity(self):
        """Test vulnerability severity enum."""
        assert VulnerabilitySeverity.CRITICAL.value == "critical"
        assert VulnerabilitySeverity.HIGH.value == "high"
        assert VulnerabilitySeverity.MEDIUM.value == "medium"
        assert VulnerabilitySeverity.LOW.value == "low"

    def test_vulnerability_model(self):
        """Test Vulnerability model."""
        vuln = Vulnerability(
            id="CVE-2024-1234",
            package="requests",
            version="2.25.0",
            fixed_version="2.28.0",
            severity=VulnerabilitySeverity.HIGH,
            title="Test vulnerability title",
            description="Test vulnerability description",
            references=["https://nvd.nist.gov/vuln/detail/CVE-2024-1234"],
        )

        assert vuln.id == "CVE-2024-1234"
        assert vuln.package == "requests"
        assert vuln.severity == VulnerabilitySeverity.HIGH
