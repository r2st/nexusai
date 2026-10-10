"""
API Versioning

API version management and routing.
"""

from datetime import date
from typing import Callable, Dict, List, Optional
from fastapi import APIRouter, Header, HTTPException, Request, Response
from fastapi.routing import APIRoute
from pydantic import BaseModel
import structlog
import re

logger = structlog.get_logger()


# Version Configuration

class APIVersion(BaseModel):
    """API version metadata."""
    version: str  # e.g., "v1", "v2"
    major: int
    minor: int
    released: date
    deprecated: Optional[date] = None
    sunset: Optional[date] = None
    description: str = ""
    
    @property
    def is_deprecated(self) -> bool:
        return self.deprecated is not None and date.today() >= self.deprecated
    
    @property
    def is_sunset(self) -> bool:
        return self.sunset is not None and date.today() >= self.sunset


# Current API versions
API_VERSIONS: Dict[str, APIVersion] = {
    "v1": APIVersion(
        version="v1",
        major=1,
        minor=0,
        released=date(2025, 1, 1),
        deprecated=date(2026, 6, 1),
        sunset=date(2027, 1, 1),
        description="Initial API version",
    ),
    "v2": APIVersion(
        version="v2",
        major=2,
        minor=0,
        released=date(2026, 1, 1),
        description="Current stable API version with enhanced features",
    ),
}

CURRENT_VERSION = "v2"
MINIMUM_VERSION = "v1"


# Version Header Middleware

class VersionedRoute(APIRoute):
    """Custom route class that handles API versioning."""
    
    def get_route_handler(self) -> Callable:
        original_route_handler = super().get_route_handler()
        
        async def versioned_route_handler(request: Request) -> Response:
            # Extract version from path or header
            version = self._extract_version(request)
            
            # Validate version
            if version not in API_VERSIONS:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid API version: {version}. Supported versions: {list(API_VERSIONS.keys())}",
                )
            
            api_version = API_VERSIONS[version]
            
            # Check if version is sunset
            if api_version.is_sunset:
                raise HTTPException(
                    status_code=410,
                    detail=f"API version {version} has been sunset. Please upgrade to {CURRENT_VERSION}.",
                )
            
            # Add version to request state
            request.state.api_version = version
            
            # Execute handler
            response = await original_route_handler(request)
            
            # Add deprecation headers
            if api_version.is_deprecated:
                response.headers["Deprecation"] = api_version.deprecated.isoformat()
                if api_version.sunset:
                    response.headers["Sunset"] = api_version.sunset.isoformat()
                response.headers["Link"] = f'</api/{CURRENT_VERSION}>; rel="successor-version"'
            
            # Add API version header
            response.headers["X-API-Version"] = version
            
            return response
        
        return versioned_route_handler
    
    def _extract_version(self, request: Request) -> str:
        """Extract API version from request."""
        # Check URL path first
        path = request.url.path
        match = re.search(r"/api/(v\d+)/", path)
        if match:
            return match.group(1)
        
        # Check header
        version_header = request.headers.get("X-API-Version")
        if version_header:
            return version_header
        
        # Check Accept header
        accept = request.headers.get("Accept", "")
        match = re.search(r"application/vnd\.nexusai\.(v\d+)\+json", accept)
        if match:
            return match.group(1)
        
        # Default to current version
        return CURRENT_VERSION


# Versioned Router Factory

def create_versioned_router(
    version: str,
    prefix: str = "",
    **kwargs,
) -> APIRouter:
    """Create a versioned API router."""
    return APIRouter(
        prefix=f"/api/{version}{prefix}",
        route_class=VersionedRoute,
        **kwargs,
    )


# Version Info Endpoints

router = APIRouter(prefix="/api", tags=["API Versioning"])


class VersionInfo(BaseModel):
    """API version information."""
    version: str
    major: int
    minor: int
    released: str
    deprecated: Optional[str] = None
    sunset: Optional[str] = None
    is_current: bool
    is_deprecated: bool
    description: str


class VersionsResponse(BaseModel):
    """Available API versions response."""
    current_version: str
    minimum_version: str
    versions: List[VersionInfo]


@router.get("/versions", response_model=VersionsResponse)
async def list_api_versions():
    """
    List all available API versions.
    
    Returns information about all API versions including deprecation status.
    """
    versions = []
    for version_id, version in API_VERSIONS.items():
        versions.append(VersionInfo(
            version=version.version,
            major=version.major,
            minor=version.minor,
            released=version.released.isoformat(),
            deprecated=version.deprecated.isoformat() if version.deprecated else None,
            sunset=version.sunset.isoformat() if version.sunset else None,
            is_current=version_id == CURRENT_VERSION,
            is_deprecated=version.is_deprecated,
            description=version.description,
        ))
    
    return VersionsResponse(
        current_version=CURRENT_VERSION,
        minimum_version=MINIMUM_VERSION,
        versions=versions,
    )


@router.get("/versions/{version}", response_model=VersionInfo)
async def get_api_version(version: str):
    """Get information about a specific API version."""
    if version not in API_VERSIONS:
        raise HTTPException(status_code=404, detail=f"Version not found: {version}")
    
    v = API_VERSIONS[version]
    return VersionInfo(
        version=v.version,
        major=v.major,
        minor=v.minor,
        released=v.released.isoformat(),
        deprecated=v.deprecated.isoformat() if v.deprecated else None,
        sunset=v.sunset.isoformat() if v.sunset else None,
        is_current=version == CURRENT_VERSION,
        is_deprecated=v.is_deprecated,
        description=v.description,
    )


# Migration Guides

MIGRATION_GUIDES: Dict[str, Dict[str, str]] = {
    "v1_to_v2": {
        "overview": """
# Migration Guide: v1 to v2

## Overview
API v2 introduces several breaking changes to improve consistency and add new features.

## Breaking Changes

### 1. Authentication
- OAuth 2.0 is now required for all endpoints
- API keys are deprecated; use access tokens instead
- New SSO endpoints available

### 2. Response Format
- All responses now wrapped in `data` field
- Pagination uses cursor-based approach
- Error responses follow RFC 7807

### 3. Endpoint Changes
- `/metrics` → `/v2/metrics/dora` and `/v2/metrics/space`
- `/analysis` → `/v2/code/analyze`
- `/chat` → `/v2/assistant/chat`

### 4. Removed Endpoints
- `/legacy/*` endpoints removed
- `/sync/*` replaced by webhooks

## New Features in v2
- Real-time collaboration endpoints
- Enhanced code analysis
- Workflow automation API
- Data residency controls

## Migration Steps
1. Update authentication to use OAuth 2.0
2. Update response parsing for new format
3. Update endpoint URLs
4. Test with v2 sandbox environment
5. Switch production traffic
""",
        "authentication": "OAuth 2.0 required; API keys deprecated",
        "response_format": "Wrapped in 'data' field; cursor pagination",
        "endpoints": "New URL structure under /v2/",
    },
}


class MigrationGuide(BaseModel):
    """Migration guide response."""
    from_version: str
    to_version: str
    overview: str
    breaking_changes: Dict[str, str]


@router.get("/versions/migrate/{from_version}/{to_version}", response_model=MigrationGuide)
async def get_migration_guide(from_version: str, to_version: str):
    """
    Get migration guide between versions.
    
    Returns detailed instructions for upgrading API versions.
    """
    guide_key = f"{from_version}_to_{to_version}"
    
    if guide_key not in MIGRATION_GUIDES:
        raise HTTPException(
            status_code=404,
            detail=f"No migration guide available from {from_version} to {to_version}",
        )
    
    guide = MIGRATION_GUIDES[guide_key]
    
    return MigrationGuide(
        from_version=from_version,
        to_version=to_version,
        overview=guide.get("overview", ""),
        breaking_changes={
            k: v for k, v in guide.items() if k != "overview"
        },
    )


# Version-specific routers

v1_router = create_versioned_router("v1", tags=["API v1 (Deprecated)"])
v2_router = create_versioned_router("v2", tags=["API v2"])


@v1_router.get("/status")
async def v1_status():
    """[DEPRECATED] Get API status."""
    return {
        "status": "ok",
        "version": "v1",
        "message": "This version is deprecated. Please migrate to v2.",
    }


@v2_router.get("/status")
async def v2_status():
    """Get API status."""
    return {
        "status": "ok",
        "version": "v2",
        "features": [
            "enhanced_analysis",
            "real_time_collaboration",
            "workflow_automation",
            "data_residency",
        ],
    }
