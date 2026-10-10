"""
Repository Index MCP Tool Handlers

Provides tools for code search, file access, git diffs, and repository
exploration through MCP for AI assistant integration.
"""

import json
import logging
import re
from datetime import UTC, datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import dataclass

from .server import MCPToolHandler
from .protocol import MCPTool
from .errors import (
    service_unavailable_error,
    not_found_error,
    connection_error,
    internal_error,
    invalid_input_error,
    ToolErrorResponse,
    ErrorCategory,
)

logger = logging.getLogger(__name__)


# =============================================================================
# Data Models
# =============================================================================

class FileType(str, Enum):
    """Types of files."""

    SOURCE = "source"
    CONFIG = "config"
    DOCUMENTATION = "documentation"
    TEST = "test"
    BUILD = "build"
    OTHER = "other"


@dataclass
class Repository:
    """Repository information."""

    id: str
    name: str
    full_name: str  # owner/repo
    description: Optional[str]
    language: Optional[str]
    default_branch: str
    url: str
    last_updated: datetime
    is_private: bool = False


@dataclass
class SearchResult:
    """Code search result."""

    file_path: str
    repository: str
    branch: str
    line_number: int
    content: str
    context_before: List[str]
    context_after: List[str]
    score: float
    language: Optional[str] = None
    match_type: str = "exact"  # exact, fuzzy, semantic


@dataclass
class FileInfo:
    """File information."""

    path: str
    name: str
    size: int
    file_type: FileType
    language: Optional[str]
    last_modified: datetime
    encoding: str = "utf-8"


@dataclass
class DiffEntry:
    """Git diff entry."""

    file_path: str
    change_type: str  # added, modified, deleted, renamed
    additions: int
    deletions: int
    hunks: List[Dict]


@dataclass
class Commit:
    """Git commit."""

    sha: str
    message: str
    author: str
    author_email: str
    timestamp: datetime
    parent_shas: List[str]
    files_changed: int
    additions: int
    deletions: int


# =============================================================================
# Repository Service (Mock Implementation)
# =============================================================================

class RepositoryService:
    """Service for repository indexing and code search."""

    def __init__(self):
        self._repositories: Dict[str, Repository] = {}
        self._file_index: Dict[str, Dict[str, str]] = {}  # repo -> path -> content
        self._commits: Dict[str, List[Commit]] = {}
        self._generate_sample_data()

    def _generate_sample_data(self):
        """Generate sample repository data for demonstration."""
        import random
        from uuid import uuid4

        repos = [
            ("nexusai", "nexusai/backend", "Python backend for NexusAI", "Python"),
            ("nexusai", "nexusai/frontend", "React frontend for NexusAI", "TypeScript"),
            ("nexusai", "nexusai/worker", "Background worker services", "Python"),
        ]

        for owner, full_name, desc, lang in repos:
            repo_id = str(uuid4())[:8]
            self._repositories[full_name] = Repository(
                id=repo_id,
                name=full_name.split("/")[1],
                full_name=full_name,
                description=desc,
                language=lang,
                default_branch="main",
                url=f"https://github.com/{full_name}",
                last_updated=datetime.now(UTC) - timedelta(days=random.randint(0, 30)),
            )

            # Generate sample files
            self._file_index[full_name] = {}

            if lang == "Python":
                files = {
                    "src/main.py": '''"""Main application entry point."""
import uvicorn
from fastapi import FastAPI
from app.api import router

app = FastAPI(title="NexusAI API")
app.include_router(router)

def main():
    """Run the application."""
    uvicorn.run(app, host="0.0.0.0", port=8000)

if __name__ == "__main__":
    main()
''',
                    "src/api/routes.py": '''"""API routes."""
from fastapi import APIRouter, Depends
from app.services import UserService

router = APIRouter()

@router.get("/users")
async def list_users(service: UserService = Depends()):
    """List all users."""
    return await service.list_users()

@router.post("/users")
async def create_user(data: dict, service: UserService = Depends()):
    """Create a new user."""
    return await service.create_user(data)
''',
                    "src/services/user.py": '''"""User service."""
from typing import List
from app.models import User
from app.db import Database

class UserService:
    """Service for user operations."""

    def __init__(self, db: Database):
        self.db = db

    async def list_users(self) -> List[User]:
        """Get all users."""
        return await self.db.query(User).all()

    async def create_user(self, data: dict) -> User:
        """Create a new user."""
        user = User(**data)
        await self.db.save(user)
        return user

    async def get_user_by_email(self, email: str) -> User:
        """Find user by email."""
        return await self.db.query(User).filter(email=email).first()
''',
                    "tests/test_user.py": '''"""User tests."""
import pytest
from app.services import UserService

@pytest.fixture
def user_service():
    """Create user service fixture."""
    return UserService(mock_db)

async def test_create_user(user_service):
    """Test user creation."""
    user = await user_service.create_user({"name": "Test"})
    assert user.name == "Test"

async def test_list_users(user_service):
    """Test listing users."""
    users = await user_service.list_users()
    assert isinstance(users, list)
''',
                    "README.md": '''# NexusAI Backend

Python backend service for NexusAI.

## Setup

```bash
pip install -r requirements.txt
python -m src.main
```

## API Documentation

See `/docs` for Swagger documentation.
''',
                }
            else:
                files = {
                    "src/App.tsx": '''import React from 'react';
import { Dashboard } from './components/Dashboard';
import { AuthProvider } from './context/AuthContext';

function App() {
  return (
    <AuthProvider>
      <Dashboard />
    </AuthProvider>
  );
}

export default App;
''',
                    "src/components/Dashboard.tsx": '''import React from 'react';
import { useAuth } from '../hooks/useAuth';
import { MetricsCard } from './MetricsCard';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();

  return (
    <div className="dashboard">
      <h1>Welcome, {user?.name}</h1>
      <MetricsCard title="DORA Metrics" />
    </div>
  );
};
''',
                }

            self._file_index[full_name] = files

            # Generate commits
            self._commits[full_name] = []
            for i in range(10):
                self._commits[full_name].append(Commit(
                    sha=f"{uuid4().hex[:7]}",
                    message=random.choice([
                        "Add new feature",
                        "Fix bug in user service",
                        "Update dependencies",
                        "Improve error handling",
                        "Add tests",
                        "Refactor code",
                    ]),
                    author=random.choice(["alice", "bob", "charlie"]),
                    author_email=f"{random.choice(['alice', 'bob'])}@example.com",
                    timestamp=datetime.now(UTC) - timedelta(days=i, hours=random.randint(0, 23)),
                    parent_shas=[f"{uuid4().hex[:7]}"],
                    files_changed=random.randint(1, 10),
                    additions=random.randint(10, 200),
                    deletions=random.randint(5, 100),
                ))

    async def health_check(self) -> bool:
        """Check if repository service is available."""
        return True

    async def list_repositories(self) -> List[Repository]:
        """List all indexed repositories."""
        return list(self._repositories.values())

    async def get_repository(self, full_name: str) -> Optional[Repository]:
        """Get repository by full name."""
        return self._repositories.get(full_name)

    async def search_code(
        self,
        query: str,
        repository: Optional[str] = None,
        language: Optional[str] = None,
        path_pattern: Optional[str] = None,
        limit: int = 20,
    ) -> List[SearchResult]:
        """Search for code across repositories."""
        results = []
        query_lower = query.lower()

        repos_to_search = [repository] if repository else self._file_index.keys()

        for repo in repos_to_search:
            if repo not in self._file_index:
                continue

            repo_info = self._repositories.get(repo)

            for file_path, content in self._file_index[repo].items():
                # Apply filters
                if language and repo_info and repo_info.language != language:
                    continue
                if path_pattern and not re.search(path_pattern, file_path):
                    continue

                # Search in content
                lines = content.split("\n")
                for i, line in enumerate(lines):
                    if query_lower in line.lower():
                        # Get context
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)

                        results.append(SearchResult(
                            file_path=file_path,
                            repository=repo,
                            branch="main",
                            line_number=i + 1,
                            content=line,
                            context_before=lines[start:i],
                            context_after=lines[i+1:end],
                            score=0.9 if query_lower == line.lower().strip() else 0.7,
                            language=self._detect_language(file_path),
                            match_type="exact",
                        ))

        # Sort by score
        results.sort(key=lambda r: r.score, reverse=True)
        return results[:limit]

    async def get_file(
        self,
        repository: str,
        path: str,
        branch: str = "main",
    ) -> Optional[Dict]:
        """Get file content."""
        if repository not in self._file_index:
            return None

        files = self._file_index[repository]
        if path not in files:
            return None

        content = files[path]
        return {
            "path": path,
            "repository": repository,
            "branch": branch,
            "content": content,
            "size": len(content),
            "language": self._detect_language(path),
            "encoding": "utf-8",
        }

    async def list_files(
        self,
        repository: str,
        path: str = "",
        branch: str = "main",
    ) -> List[Dict]:
        """List files in a repository directory."""
        if repository not in self._file_index:
            return []

        files = self._file_index[repository]
        result = []

        for file_path, content in files.items():
            if path and not file_path.startswith(path):
                continue

            result.append({
                "path": file_path,
                "name": file_path.split("/")[-1],
                "type": "file",
                "size": len(content),
                "language": self._detect_language(file_path),
            })

        return result

    async def get_diff(
        self,
        repository: str,
        base: str,
        head: str,
    ) -> List[DiffEntry]:
        """Get diff between two refs."""
        # Mock diff generation
        if repository not in self._file_index:
            return []

        diffs = []
        for file_path in list(self._file_index[repository].keys())[:3]:
            diffs.append(DiffEntry(
                file_path=file_path,
                change_type="modified",
                additions=15,
                deletions=5,
                hunks=[
                    {
                        "old_start": 10,
                        "old_count": 5,
                        "new_start": 10,
                        "new_count": 15,
                        "content": "@@ -10,5 +10,15 @@\n- old line\n+ new line",
                    }
                ],
            ))

        return diffs

    async def get_commits(
        self,
        repository: str,
        branch: str = "main",
        limit: int = 20,
    ) -> List[Commit]:
        """Get recent commits."""
        commits = self._commits.get(repository, [])
        return commits[:limit]

    async def get_commit(
        self,
        repository: str,
        sha: str,
    ) -> Optional[Commit]:
        """Get a specific commit."""
        commits = self._commits.get(repository, [])
        for commit in commits:
            if commit.sha == sha or commit.sha.startswith(sha):
                return commit
        return None

    async def get_blame(
        self,
        repository: str,
        path: str,
        branch: str = "main",
    ) -> List[Dict]:
        """Get blame information for a file."""
        if repository not in self._file_index:
            return []

        files = self._file_index[repository]
        if path not in files:
            return []

        content = files[path]
        lines = content.split("\n")
        commits = self._commits.get(repository, [])

        blame = []
        for i, line in enumerate(lines):
            commit = commits[i % len(commits)] if commits else None
            blame.append({
                "line_number": i + 1,
                "content": line,
                "commit_sha": commit.sha if commit else "unknown",
                "author": commit.author if commit else "unknown",
                "timestamp": commit.timestamp.isoformat() if commit else None,
            })

        return blame

    def _detect_language(self, path: str) -> Optional[str]:
        """Detect programming language from file extension."""
        ext_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".tsx": "TypeScript",
            ".jsx": "JavaScript",
            ".java": "Java",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP",
            ".cs": "C#",
            ".cpp": "C++",
            ".c": "C",
            ".md": "Markdown",
            ".json": "JSON",
            ".yaml": "YAML",
            ".yml": "YAML",
        }

        for ext, lang in ext_map.items():
            if path.endswith(ext):
                return lang
        return None


# Global repository service instance
repo_service = RepositoryService()


# =============================================================================
# Repository Tools
# =============================================================================

class RepoHealthCheckHandler(MCPToolHandler):
    """Check repository service health."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="repo_health_check",
            description="Check if the repository indexing service is available and healthy",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        try:
            is_healthy = await repo_service.health_check()
            repos = await repo_service.list_repositories()

            return {
                "success": True,
                "healthy": is_healthy,
                "status": "available" if is_healthy else "unavailable",
                "indexed_repositories": len(repos),
                "message": "Repository service is running and ready to use.",
                "next_steps": [
                    "Use 'repo_list' to see indexed repositories",
                    "Use 'repo_search_code' to search across codebases",
                ],
            }
        except Exception as e:
            return connection_error(
                target="Repository Service",
                original_error=str(e),
            ).to_dict()


class RepoListHandler(MCPToolHandler):
    """List indexed repositories."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="repo_list",
            description="List all indexed repositories available for code search",
            input_schema={
                "type": "object",
                "properties": {},
                "required": [],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        try:
            repos = await repo_service.list_repositories()

            return {
                "success": True,
                "count": len(repos),
                "repositories": [
                    {
                        "name": r.name,
                        "full_name": r.full_name,
                        "description": r.description,
                        "language": r.language,
                        "default_branch": r.default_branch,
                        "url": r.url,
                        "last_updated": r.last_updated.isoformat(),
                    }
                    for r in repos
                ],
            }
        except Exception as e:
            return internal_error(
                operation="list_repositories",
                error_message=str(e),
            ).to_dict()


class RepoSearchCodeHandler(MCPToolHandler):
    """Search code across repositories."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="repo_search_code",
            description="Search for code patterns, function definitions, or text across indexed repositories",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (code pattern, function name, or text)",
                    },
                    "repository": {
                        "type": "string",
                        "description": "Limit search to a specific repository (owner/repo format)",
                    },
                    "language": {
                        "type": "string",
                        "description": "Filter by programming language",
                    },
                    "path_pattern": {
                        "type": "string",
                        "description": "Regex pattern to filter file paths",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of results (default: 20)",
                        "default": 20,
                    },
                },
                "required": ["query"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        query = arguments["query"]
        repository = arguments.get("repository")
        language = arguments.get("language")
        path_pattern = arguments.get("path_pattern")
        limit = arguments.get("limit", 20)

        if not query or len(query) < 2:
            return invalid_input_error(
                parameter_name="query",
                expected="At least 2 characters",
                received=query,
            ).to_dict()

        try:
            results = await repo_service.search_code(
                query=query,
                repository=repository,
                language=language,
                path_pattern=path_pattern,
                limit=limit,
            )

            return {
                "success": True,
                "query": query,
                "filters": {
                    "repository": repository,
                    "language": language,
                    "path_pattern": path_pattern,
                },
                "result_count": len(results),
                "results": [
                    {
                        "file": r.file_path,
                        "repository": r.repository,
                        "line": r.line_number,
                        "content": r.content.strip(),
                        "context_before": r.context_before,
                        "context_after": r.context_after,
                        "language": r.language,
                        "score": round(r.score, 2),
                    }
                    for r in results
                ],
            }
        except Exception as e:
            return internal_error(
                operation="search_code",
                error_message=str(e),
            ).to_dict()


class RepoGetFileHandler(MCPToolHandler):
    """Get file content."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="repo_get_file",
            description="Get the contents of a specific file from a repository",
            input_schema={
                "type": "object",
                "properties": {
                    "repository": {
                        "type": "string",
                        "description": "Repository in owner/repo format",
                    },
                    "path": {
                        "type": "string",
                        "description": "File path within the repository",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (default: main)",
                        "default": "main",
                    },
                },
                "required": ["repository", "path"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        repository = arguments["repository"]
        path = arguments["path"]
        branch = arguments.get("branch", "main")

        try:
            file_data = await repo_service.get_file(repository, path, branch)

            if not file_data:
                return not_found_error(
                    resource_type="file",
                    resource_name=f"{repository}/{path}",
                ).to_dict()

            return {
                "success": True,
                **file_data,
            }
        except Exception as e:
            return internal_error(
                operation="get_file",
                error_message=str(e),
            ).to_dict()


class RepoListFilesHandler(MCPToolHandler):
    """List files in a repository."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="repo_list_files",
            description="List files in a repository directory",
            input_schema={
                "type": "object",
                "properties": {
                    "repository": {
                        "type": "string",
                        "description": "Repository in owner/repo format",
                    },
                    "path": {
                        "type": "string",
                        "description": "Directory path (empty for root)",
                        "default": "",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (default: main)",
                        "default": "main",
                    },
                },
                "required": ["repository"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        repository = arguments["repository"]
        path = arguments.get("path", "")
        branch = arguments.get("branch", "main")

        try:
            files = await repo_service.list_files(repository, path, branch)

            return {
                "success": True,
                "repository": repository,
                "path": path or "/",
                "branch": branch,
                "file_count": len(files),
                "files": files,
            }
        except Exception as e:
            return internal_error(
                operation="list_files",
                error_message=str(e),
            ).to_dict()


class RepoGetDiffHandler(MCPToolHandler):
    """Get diff between two refs."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="repo_get_diff",
            description="Get the diff (changes) between two branches, commits, or tags",
            input_schema={
                "type": "object",
                "properties": {
                    "repository": {
                        "type": "string",
                        "description": "Repository in owner/repo format",
                    },
                    "base": {
                        "type": "string",
                        "description": "Base ref (branch, commit SHA, or tag)",
                    },
                    "head": {
                        "type": "string",
                        "description": "Head ref to compare against base",
                    },
                },
                "required": ["repository", "base", "head"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        repository = arguments["repository"]
        base = arguments["base"]
        head = arguments["head"]

        try:
            diffs = await repo_service.get_diff(repository, base, head)

            total_additions = sum(d.additions for d in diffs)
            total_deletions = sum(d.deletions for d in diffs)

            return {
                "success": True,
                "repository": repository,
                "comparison": f"{base}...{head}",
                "summary": {
                    "files_changed": len(diffs),
                    "additions": total_additions,
                    "deletions": total_deletions,
                },
                "files": [
                    {
                        "path": d.file_path,
                        "change_type": d.change_type,
                        "additions": d.additions,
                        "deletions": d.deletions,
                        "hunks": d.hunks,
                    }
                    for d in diffs
                ],
            }
        except Exception as e:
            return internal_error(
                operation="get_diff",
                error_message=str(e),
            ).to_dict()


class RepoGetCommitsHandler(MCPToolHandler):
    """Get recent commits."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="repo_get_commits",
            description="Get recent commits from a repository branch",
            input_schema={
                "type": "object",
                "properties": {
                    "repository": {
                        "type": "string",
                        "description": "Repository in owner/repo format",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (default: main)",
                        "default": "main",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of commits (default: 20)",
                        "default": 20,
                    },
                },
                "required": ["repository"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        repository = arguments["repository"]
        branch = arguments.get("branch", "main")
        limit = arguments.get("limit", 20)

        try:
            commits = await repo_service.get_commits(repository, branch, limit)

            return {
                "success": True,
                "repository": repository,
                "branch": branch,
                "commit_count": len(commits),
                "commits": [
                    {
                        "sha": c.sha,
                        "message": c.message,
                        "author": c.author,
                        "email": c.author_email,
                        "timestamp": c.timestamp.isoformat(),
                        "files_changed": c.files_changed,
                        "additions": c.additions,
                        "deletions": c.deletions,
                    }
                    for c in commits
                ],
            }
        except Exception as e:
            return internal_error(
                operation="get_commits",
                error_message=str(e),
            ).to_dict()


class RepoGetCommitHandler(MCPToolHandler):
    """Get a specific commit."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="repo_get_commit",
            description="Get detailed information about a specific commit",
            input_schema={
                "type": "object",
                "properties": {
                    "repository": {
                        "type": "string",
                        "description": "Repository in owner/repo format",
                    },
                    "sha": {
                        "type": "string",
                        "description": "Commit SHA (full or short)",
                    },
                },
                "required": ["repository", "sha"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        repository = arguments["repository"]
        sha = arguments["sha"]

        try:
            commit = await repo_service.get_commit(repository, sha)

            if not commit:
                return not_found_error(
                    resource_type="commit",
                    resource_name=sha,
                ).to_dict()

            return {
                "success": True,
                "commit": {
                    "sha": commit.sha,
                    "message": commit.message,
                    "author": commit.author,
                    "email": commit.author_email,
                    "timestamp": commit.timestamp.isoformat(),
                    "parent_shas": commit.parent_shas,
                    "files_changed": commit.files_changed,
                    "additions": commit.additions,
                    "deletions": commit.deletions,
                },
            }
        except Exception as e:
            return internal_error(
                operation="get_commit",
                error_message=str(e),
            ).to_dict()


class RepoGetBlameHandler(MCPToolHandler):
    """Get blame information for a file."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="repo_get_blame",
            description="Get git blame information showing who last modified each line of a file",
            input_schema={
                "type": "object",
                "properties": {
                    "repository": {
                        "type": "string",
                        "description": "Repository in owner/repo format",
                    },
                    "path": {
                        "type": "string",
                        "description": "File path within the repository",
                    },
                    "branch": {
                        "type": "string",
                        "description": "Branch name (default: main)",
                        "default": "main",
                    },
                },
                "required": ["repository", "path"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        repository = arguments["repository"]
        path = arguments["path"]
        branch = arguments.get("branch", "main")

        try:
            blame = await repo_service.get_blame(repository, path, branch)

            if not blame:
                return not_found_error(
                    resource_type="file",
                    resource_name=f"{repository}/{path}",
                ).to_dict()

            return {
                "success": True,
                "repository": repository,
                "path": path,
                "branch": branch,
                "line_count": len(blame),
                "blame": blame[:100],  # Limit output
                "truncated": len(blame) > 100,
            }
        except Exception as e:
            return internal_error(
                operation="get_blame",
                error_message=str(e),
            ).to_dict()


class RepoFindDefinitionHandler(MCPToolHandler):
    """Find function/class definitions."""

    @property
    def tool(self) -> MCPTool:
        return MCPTool(
            name="repo_find_definition",
            description="Find the definition of a function, class, or variable across repositories",
            input_schema={
                "type": "object",
                "properties": {
                    "name": {
                        "type": "string",
                        "description": "Name of the function, class, or variable to find",
                    },
                    "repository": {
                        "type": "string",
                        "description": "Limit search to a specific repository",
                    },
                    "definition_type": {
                        "type": "string",
                        "description": "Type of definition to search for",
                        "enum": ["function", "class", "variable", "any"],
                        "default": "any",
                    },
                },
                "required": ["name"],
            },
        )

    async def execute(
        self,
        arguments: Dict[str, Any],
        context: Dict[str, Any],
    ) -> Any:
        name = arguments["name"]
        repository = arguments.get("repository")
        definition_type = arguments.get("definition_type", "any")

        # Build search patterns based on definition type
        patterns = []
        if definition_type in ["function", "any"]:
            patterns.extend([
                f"def {name}",  # Python
                f"function {name}",  # JavaScript
                f"func {name}",  # Go
                f"fn {name}",  # Rust
            ])
        if definition_type in ["class", "any"]:
            patterns.extend([
                f"class {name}",
                f"interface {name}",  # TypeScript
                f"struct {name}",  # Go/Rust
            ])
        if definition_type in ["variable", "any"]:
            patterns.extend([
                f"const {name}",
                f"let {name}",
                f"var {name}",
            ])

        try:
            all_results = []
            for pattern in patterns:
                results = await repo_service.search_code(
                    query=pattern,
                    repository=repository,
                    limit=5,
                )
                all_results.extend(results)

            # Deduplicate and sort by score
            seen = set()
            unique_results = []
            for r in sorted(all_results, key=lambda x: x.score, reverse=True):
                key = (r.repository, r.file_path, r.line_number)
                if key not in seen:
                    seen.add(key)
                    unique_results.append(r)

            return {
                "success": True,
                "name": name,
                "definition_type": definition_type,
                "definitions_found": len(unique_results),
                "definitions": [
                    {
                        "file": r.file_path,
                        "repository": r.repository,
                        "line": r.line_number,
                        "content": r.content.strip(),
                        "language": r.language,
                    }
                    for r in unique_results[:10]
                ],
            }
        except Exception as e:
            return internal_error(
                operation="find_definition",
                error_message=str(e),
            ).to_dict()


# =============================================================================
# Helper function to get all repository tool handlers
# =============================================================================

def get_all_repo_tool_handlers() -> list[MCPToolHandler]:
    """Return all Repository MCP tool handlers."""
    return [
        # Health
        RepoHealthCheckHandler(),

        # Repository
        RepoListHandler(),

        # Code Search
        RepoSearchCodeHandler(),
        RepoFindDefinitionHandler(),

        # File Access
        RepoGetFileHandler(),
        RepoListFilesHandler(),
        RepoGetBlameHandler(),

        # Git Operations
        RepoGetDiffHandler(),
        RepoGetCommitsHandler(),
        RepoGetCommitHandler(),
    ]
