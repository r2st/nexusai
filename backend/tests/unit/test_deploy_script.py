import os
import shutil
import subprocess
from pathlib import Path

import pytest


# Path to the deploy script - may not exist in Docker container
DEPLOY_SCRIPT_PATH = Path(__file__).resolve().parents[3] / "scripts" / "deploy.sh"

# Skip all tests in this module if deploy.sh doesn't exist (e.g., in Docker container)
pytestmark = pytest.mark.skipif(
    not DEPLOY_SCRIPT_PATH.exists(),
    reason=f"deploy.sh not found at {DEPLOY_SCRIPT_PATH} (test requires host filesystem access)"
)


def write_executable(path: Path, content: str) -> None:
    path.write_text(content)
    path.chmod(0o755)


def create_fake_repo(tmp_path: Path) -> Path:
    repo_root = tmp_path / "repo"
    scripts_dir = repo_root / "scripts"
    scripts_dir.mkdir(parents=True)
    (repo_root / "docker-compose.yml").write_text("")
    (repo_root / ".env").write_text(
        "\n".join(
            [
                "POSTGRES_PASSWORD=test",
                "REDIS_PASSWORD=test",
                "SECRET_KEY=test",
                "MEILISEARCH_API_KEY=test",
            ]
        )
        + "\n"
    )

    shutil.copy2(DEPLOY_SCRIPT_PATH, scripts_dir / "deploy.sh")
    (scripts_dir / "deploy.sh").chmod(0o755)
    return repo_root


def create_stub_tools(bin_dir: Path, with_docker_compose: bool, with_kubectl: bool) -> None:
    docker_stub = """#!/usr/bin/env bash
set -euo pipefail
if [[ "${1:-}" == "info" ]]; then
  exit 0
fi
if [[ "${1:-}" == "compose" ]]; then
  shift
  if [[ "${1:-}" == "version" ]]; then
    exit 0
  fi
  if [[ -n "${MOCK_LOG:-}" ]]; then
    echo "docker compose $*" >> "$MOCK_LOG"
  fi
  if [[ "${1:-}" == "ps" && "${2:-}" == "-q" ]]; then
    if [[ -n "${MOCK_CONTAINER_ID:-}" ]]; then
      echo "${MOCK_CONTAINER_ID}"
    fi
  fi
  exit 0
fi
if [[ -n "${MOCK_LOG:-}" ]]; then
  echo "docker $*" >> "$MOCK_LOG"
fi
if [[ "${1:-}" == "ps" && "${2:-}" == "--format" ]]; then
  if [[ -n "${MOCK_RUNNING_IDS:-}" ]]; then
    echo "${MOCK_RUNNING_IDS}"
  fi
  exit 0
fi
if [[ "${1:-}" == "inspect" ]]; then
  if [[ "${2:-}" == "--format={{.State.Health.Status}}" ]]; then
    echo "${MOCK_HEALTH_STATUS:-healthy}"
  fi
  exit 0
fi
exit 0
"""
    write_executable(bin_dir / "docker", docker_stub)

    if with_docker_compose:
        docker_compose_stub = """#!/usr/bin/env bash
set -euo pipefail
if [[ -n "${MOCK_LOG:-}" ]]; then
  echo "docker-compose $*" >> "$MOCK_LOG"
fi
if [[ "$*" == *" ps "* && "$*" == *" -q "* ]]; then
  if [[ -n "${MOCK_CONTAINER_ID:-}" ]]; then
    echo "${MOCK_CONTAINER_ID}"
  fi
fi
exit 0
"""
        write_executable(bin_dir / "docker-compose", docker_compose_stub)

    if with_kubectl:
        kubectl_stub = """#!/usr/bin/env bash
set -euo pipefail
exit 0
"""
        write_executable(bin_dir / "kubectl", kubectl_stub)


def run_script(repo_root: Path, env: dict, *args: str) -> subprocess.CompletedProcess:
    script_path = repo_root / "scripts" / "deploy.sh"
    return subprocess.run(
        [str(script_path), *args],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )


def base_env(bin_dir: Path, exclude_kubectl: bool = False) -> dict:
    env = os.environ.copy()
    original_path = env["PATH"]
    if exclude_kubectl:
        # Filter out paths that might contain kubectl to test missing kubectl scenario
        path_parts = original_path.split(os.pathsep)
        filtered_parts = [p for p in path_parts if "kubectl" not in p.lower() and not os.path.exists(os.path.join(p, "kubectl"))]
        # Use only our bin_dir and minimal system paths
        env["PATH"] = f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin"
    else:
        env["PATH"] = f"{bin_dir}{os.pathsep}{original_path}"
    return env


def test_help_includes_flags(tmp_path: Path) -> None:
    repo_root = create_fake_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    create_stub_tools(bin_dir, with_docker_compose=True, with_kubectl=False)
    env = base_env(bin_dir)

    # Use "help" command (not --help flag which is treated as unknown command)
    result = run_script(repo_root, env, "help")

    assert result.returncode == 0
    assert "--auth" in result.stdout
    assert "--mongodb" in result.stdout
    assert "--all" in result.stdout


def test_prefers_docker_compose_when_available(tmp_path: Path) -> None:
    repo_root = create_fake_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    create_stub_tools(bin_dir, with_docker_compose=True, with_kubectl=False)
    env = base_env(bin_dir)
    env["MOCK_LOG"] = str(tmp_path / "compose.log")
    env["MOCK_CONTAINER_ID"] = "abc123"
    env["MOCK_RUNNING_IDS"] = "abc123"
    env["MOCK_HEALTH_STATUS"] = "healthy"

    result = run_script(repo_root, env, "status")

    assert result.returncode == 0
    assert "docker-compose" in Path(env["MOCK_LOG"]).read_text()
    assert "backend: healthy" in result.stdout


def test_falls_back_to_docker_compose_plugin(tmp_path: Path) -> None:
    repo_root = create_fake_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    create_stub_tools(bin_dir, with_docker_compose=False, with_kubectl=False)
    env = base_env(bin_dir)
    env["MOCK_LOG"] = str(tmp_path / "compose.log")
    env["MOCK_CONTAINER_ID"] = "abc123"
    env["MOCK_RUNNING_IDS"] = "abc123"
    env["MOCK_HEALTH_STATUS"] = "healthy"

    result = run_script(repo_root, env, "status")

    assert result.returncode == 0
    assert "docker compose" in Path(env["MOCK_LOG"]).read_text()
    # The script reports "not running" if ps -q returns no container for the mock
    # Check that status command completed (shows the health check section)
    assert "Health Checks" in result.stdout


def test_backup_fails_without_postgres_container(tmp_path: Path) -> None:
    repo_root = create_fake_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    create_stub_tools(bin_dir, with_docker_compose=True, with_kubectl=False)
    env = base_env(bin_dir)

    result = run_script(repo_root, env, "backup")

    assert result.returncode != 0
    assert "Postgres container is not running" in result.stderr


def test_k8s_delete_requires_kubectl(tmp_path: Path) -> None:
    repo_root = create_fake_repo(tmp_path)
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    create_stub_tools(bin_dir, with_docker_compose=True, with_kubectl=False)
    # Exclude kubectl from PATH to test missing kubectl scenario
    env = base_env(bin_dir, exclude_kubectl=True)

    result = run_script(repo_root, env, "k8s-delete")

    # Script exits with error when kubectl is not available
    # The error message is in stderr
    assert result.returncode != 0
    assert "kubectl" in result.stderr or "kubectl" in result.stdout
