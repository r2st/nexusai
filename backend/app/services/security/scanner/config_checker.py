"""Configuration Security Checker."""

import os
import re
from datetime import datetime
from pathlib import Path

from pydantic import BaseModel


class ConfigIssue(BaseModel):
    """A configuration security issue."""

    id: str
    category: str
    severity: str
    file: str
    setting: str
    current_value: str | None = None
    expected_value: str | None = None
    message: str
    recommendation: str


class ConfigSecurityChecker:
    """Checks configuration files for security issues.

    Validates security settings in:
    - Application configuration
    - Docker/container settings
    - Web server configuration
    - Database configuration
    - Cloud provider settings
    """

    def __init__(self):
        """Initialize config checker."""
        pass

    def check_env_file(
        self,
        file_path: str | Path,
    ) -> list[ConfigIssue]:
        """Check .env file for security issues.

        Args:
            file_path: Path to .env file

        Returns:
            List of configuration issues
        """
        issues = []
        path = Path(file_path)

        if not path.exists():
            return issues

        content = path.read_text()
        lines = content.split("\n")

        for i, line in enumerate(lines, 1):
            line = line.strip()

            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue

            # Parse key=value
            if "=" not in line:
                continue

            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"")

            # Check for insecure settings
            issues.extend(self._check_env_setting(str(file_path), key, value))

        return issues

    def _check_env_setting(
        self,
        file_path: str,
        key: str,
        value: str,
    ) -> list[ConfigIssue]:
        """Check individual environment setting."""
        issues = []
        key_lower = key.lower()

        # Check for debug mode in production
        if key_lower in ("debug", "app_debug") and value.lower() in ("true", "1", "yes"):
            issues.append(ConfigIssue(
                id=f"env-debug-{key}",
                category="configuration",
                severity="high",
                file=file_path,
                setting=key,
                current_value=value,
                expected_value="false",
                message="Debug mode should be disabled in production",
                recommendation="Set DEBUG=false in production environments",
            ))

        # Check for weak secrets
        secret_keys = ["secret_key", "jwt_secret", "encryption_key", "api_key"]
        if any(s in key_lower for s in secret_keys):
            if len(value) < 32:
                issues.append(ConfigIssue(
                    id=f"env-weak-secret-{key}",
                    category="cryptography",
                    severity="high",
                    file=file_path,
                    setting=key,
                    message=f"{key} appears to be too short ({len(value)} chars)",
                    recommendation="Use a secret of at least 32 characters",
                ))

            if value in ("change-me", "changeme", "secret", "password", "default"):
                issues.append(ConfigIssue(
                    id=f"env-default-secret-{key}",
                    category="secrets",
                    severity="critical",
                    file=file_path,
                    setting=key,
                    message=f"{key} contains a default/placeholder value",
                    recommendation="Generate a strong random secret",
                ))

        # Check for default passwords
        password_keys = ["password", "passwd", "pwd", "db_password", "redis_password"]
        if any(p in key_lower for p in password_keys):
            weak_passwords = ["password", "admin", "root", "123456", "postgres", "mysql"]
            if value.lower() in weak_passwords:
                issues.append(ConfigIssue(
                    id=f"env-weak-password-{key}",
                    category="authentication",
                    severity="critical",
                    file=file_path,
                    setting=key,
                    message=f"{key} uses a common/weak password",
                    recommendation="Use a strong, unique password",
                ))

        # Check for insecure URLs
        if "url" in key_lower and value.startswith("http://"):
            if "localhost" not in value and "127.0.0.1" not in value:
                issues.append(ConfigIssue(
                    id=f"env-insecure-url-{key}",
                    category="configuration",
                    severity="medium",
                    file=file_path,
                    setting=key,
                    current_value=value[:50],
                    message="Using HTTP instead of HTTPS for remote URL",
                    recommendation="Use HTTPS for all remote connections",
                ))

        # Check CORS settings
        if "cors" in key_lower and value == "*":
            issues.append(ConfigIssue(
                id=f"env-cors-{key}",
                category="access_control",
                severity="medium",
                file=file_path,
                setting=key,
                current_value=value,
                message="CORS is set to allow all origins",
                recommendation="Restrict CORS to specific allowed origins",
            ))

        return issues

    def check_docker_compose(
        self,
        file_path: str | Path,
    ) -> list[ConfigIssue]:
        """Check Docker Compose file for security issues.

        Args:
            file_path: Path to docker-compose.yml

        Returns:
            List of configuration issues
        """
        import yaml

        issues = []
        path = Path(file_path)

        if not path.exists():
            return issues

        try:
            content = yaml.safe_load(path.read_text())
        except Exception:
            return issues

        services = content.get("services", {})

        for service_name, service in services.items():
            # Check for privileged mode
            if service.get("privileged"):
                issues.append(ConfigIssue(
                    id=f"docker-privileged-{service_name}",
                    category="access_control",
                    severity="critical",
                    file=str(file_path),
                    setting=f"services.{service_name}.privileged",
                    current_value="true",
                    message=f"Service '{service_name}' runs in privileged mode",
                    recommendation="Remove privileged mode unless absolutely necessary",
                ))

            # Check for running as root
            if not service.get("user"):
                issues.append(ConfigIssue(
                    id=f"docker-root-{service_name}",
                    category="access_control",
                    severity="medium",
                    file=str(file_path),
                    setting=f"services.{service_name}.user",
                    message=f"Service '{service_name}' may run as root",
                    recommendation="Specify a non-root user for the container",
                ))

            # Check for exposed ports
            ports = service.get("ports", [])
            for port in ports:
                port_str = str(port)
                if port_str.startswith("0.0.0.0:") or ":" in port_str and not port_str.startswith("127.0.0.1"):
                    issues.append(ConfigIssue(
                        id=f"docker-exposed-port-{service_name}-{port_str}",
                        category="network",
                        severity="medium",
                        file=str(file_path),
                        setting=f"services.{service_name}.ports",
                        current_value=port_str,
                        message=f"Port {port_str} is exposed on all interfaces",
                        recommendation="Bind to 127.0.0.1 for local-only access",
                    ))

            # Check for sensitive environment variables
            environment = service.get("environment", {})
            if isinstance(environment, list):
                environment = dict(e.split("=", 1) for e in environment if "=" in e)

            for key, value in environment.items():
                if any(s in key.lower() for s in ["password", "secret", "key", "token"]):
                    if value and not value.startswith("${"):
                        issues.append(ConfigIssue(
                            id=f"docker-hardcoded-secret-{service_name}-{key}",
                            category="secrets",
                            severity="high",
                            file=str(file_path),
                            setting=f"services.{service_name}.environment.{key}",
                            message=f"Hardcoded sensitive value for {key}",
                            recommendation="Use environment variable substitution: ${VAR_NAME}",
                        ))

        return issues

    def check_dockerfile(
        self,
        file_path: str | Path,
    ) -> list[ConfigIssue]:
        """Check Dockerfile for security issues.

        Args:
            file_path: Path to Dockerfile

        Returns:
            List of configuration issues
        """
        issues = []
        path = Path(file_path)

        if not path.exists():
            return issues

        content = path.read_text()
        lines = content.split("\n")

        has_user_instruction = False
        uses_latest_tag = False

        for i, line in enumerate(lines, 1):
            line = line.strip()

            # Check for USER instruction
            if line.upper().startswith("USER "):
                has_user_instruction = True
                user = line.split()[1] if len(line.split()) > 1 else ""
                if user.lower() == "root":
                    issues.append(ConfigIssue(
                        id=f"dockerfile-root-user-{i}",
                        category="access_control",
                        severity="high",
                        file=str(file_path),
                        setting=f"Line {i}",
                        current_value="USER root",
                        message="Dockerfile explicitly sets USER to root",
                        recommendation="Use a non-root user for the final image",
                    ))

            # Check for latest tag
            if line.upper().startswith("FROM "):
                image = line.split()[1] if len(line.split()) > 1 else ""
                if ":latest" in image or ":" not in image:
                    uses_latest_tag = True
                    issues.append(ConfigIssue(
                        id=f"dockerfile-latest-{i}",
                        category="configuration",
                        severity="medium",
                        file=str(file_path),
                        setting=f"Line {i}",
                        current_value=image,
                        message="Using 'latest' tag or no tag for base image",
                        recommendation="Pin to a specific image version for reproducibility",
                    ))

            # Check for secrets in ENV
            if line.upper().startswith("ENV "):
                env_content = line[4:].strip()
                if any(s in env_content.lower() for s in ["password=", "secret=", "key="]):
                    issues.append(ConfigIssue(
                        id=f"dockerfile-env-secret-{i}",
                        category="secrets",
                        severity="critical",
                        file=str(file_path),
                        setting=f"Line {i}",
                        message="Secrets should not be set via ENV instruction",
                        recommendation="Use build arguments or runtime secrets",
                    ))

            # Check for ADD with URL
            if line.upper().startswith("ADD ") and "http" in line:
                issues.append(ConfigIssue(
                    id=f"dockerfile-add-url-{i}",
                    category="input_validation",
                    severity="medium",
                    file=str(file_path),
                    setting=f"Line {i}",
                    message="Using ADD with URL can be insecure",
                    recommendation="Use curl/wget with verification, or COPY local files",
                ))

        # Check if no USER instruction at all
        if not has_user_instruction:
            issues.append(ConfigIssue(
                id="dockerfile-no-user",
                category="access_control",
                severity="medium",
                file=str(file_path),
                setting="USER instruction",
                message="Dockerfile does not set a non-root USER",
                recommendation="Add USER instruction to run as non-root",
            ))

        return issues

    def check_all(
        self,
        project_dir: str | Path,
    ) -> list[ConfigIssue]:
        """Check all configuration files in a project.

        Args:
            project_dir: Project root directory

        Returns:
            All configuration issues found
        """
        issues = []
        path = Path(project_dir)

        # Check .env files
        for env_file in path.rglob(".env*"):
            if env_file.is_file():
                issues.extend(self.check_env_file(env_file))

        # Check Docker Compose files
        for compose_file in path.rglob("*compose*.y*ml"):
            issues.extend(self.check_docker_compose(compose_file))

        # Check Dockerfiles
        for dockerfile in path.rglob("Dockerfile*"):
            issues.extend(self.check_dockerfile(dockerfile))

        return issues
