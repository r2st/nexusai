"""DevLake Integration Services.

Services for interacting with Apache DevLake:
- Pipeline management (blueprints)
- Data collection
- DORA metrics
- Plugin management
"""

__all__ = [
    # Blueprint service
    "blueprint_service",
    "Blueprint",
    "BlueprintMode",
    "BlueprintStatus",
    "PipelineRun",
    "PipelineStatus",
    # DevLake API service
    "devlake_service",
    "DevLakeService",
    "DORAMetrics",
]


def __getattr__(name: str):
    if name in {
        "blueprint_service",
        "Blueprint",
        "BlueprintMode",
        "BlueprintStatus",
        "PipelineRun",
        "PipelineStatus",
    }:
        from app.services.devlake.blueprints import (
            blueprint_service,
            Blueprint,
            BlueprintMode,
            BlueprintStatus,
            PipelineRun,
            PipelineStatus,
        )

        return {
            "blueprint_service": blueprint_service,
            "Blueprint": Blueprint,
            "BlueprintMode": BlueprintMode,
            "BlueprintStatus": BlueprintStatus,
            "PipelineRun": PipelineRun,
            "PipelineStatus": PipelineStatus,
        }[name]

    if name in {"devlake_service", "DevLakeService", "DORAMetrics"}:
        from app.services.devlake.service import (
            devlake_service,
            DevLakeService,
            DORAMetrics,
        )

        return {
            "devlake_service": devlake_service,
            "DevLakeService": DevLakeService,
            "DORAMetrics": DORAMetrics,
        }[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
