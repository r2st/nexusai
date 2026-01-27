"""Image editing service."""

import base64
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any
from uuid import uuid4

import aiofiles
import httpx
import structlog

from app.core.config import settings
from app.services.image.generation import GeneratedImage, ImageProvider

logger = structlog.get_logger()


class EditOperation(str, Enum):
    """Image edit operations."""

    INPAINT = "inpaint"  # Edit specific areas
    OUTPAINT = "outpaint"  # Extend the image
    UPSCALE = "upscale"  # Increase resolution
    BACKGROUND_REMOVE = "background_remove"
    STYLE_TRANSFER = "style_transfer"
    COLORIZE = "colorize"


@dataclass
class ImageEditRequest:
    """Request for image editing."""

    image_path: str | None = None
    image_base64: str | None = None
    image_url: str | None = None
    operation: EditOperation = EditOperation.INPAINT
    prompt: str | None = None
    mask_path: str | None = None
    mask_base64: str | None = None
    provider: ImageProvider = ImageProvider.OPENAI_DALLE
    model: str | None = None
    strength: float = 0.8
    guidance_scale: float = 7.5
    size: str = "1024x1024"
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class EditedImage:
    """An edited image."""

    id: str
    operation: EditOperation
    original_id: str | None = None
    url: str | None = None
    base64_data: str | None = None
    file_path: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "operation": self.operation.value,
            "original_id": self.original_id,
            "url": self.url,
            "file_path": self.file_path,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


class ImageEditingService:
    """Service for editing images."""

    def __init__(self, storage_dir: str | None = None):
        self.storage_dir = Path(storage_dir or settings.UPLOAD_DIR) / "edited_images"
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    async def edit(self, request: ImageEditRequest) -> EditedImage | None:
        """Edit an image based on the request."""
        if request.operation == EditOperation.INPAINT:
            return await self._inpaint(request)
        elif request.operation == EditOperation.UPSCALE:
            return await self._upscale(request)
        elif request.operation == EditOperation.BACKGROUND_REMOVE:
            return await self._remove_background(request)
        elif request.operation == EditOperation.OUTPAINT:
            return await self._outpaint(request)
        else:
            logger.error("Unsupported edit operation", operation=request.operation)
            return None

    async def _get_image_data(self, request: ImageEditRequest) -> bytes | None:
        """Get image data from request."""
        if request.image_base64:
            return base64.b64decode(request.image_base64)
        elif request.image_path:
            async with aiofiles.open(request.image_path, "rb") as f:
                return await f.read()
        elif request.image_url:
            async with httpx.AsyncClient() as client:
                response = await client.get(request.image_url)
                return response.content
        return None

    async def _inpaint(self, request: ImageEditRequest) -> EditedImage | None:
        """Inpaint (edit) an image using OpenAI."""
        if not settings.OPENAI_API_KEY:
            logger.error("OpenAI API key required for inpainting")
            return None

        image_data = await self._get_image_data(request)
        if not image_data:
            logger.error("No image data provided")
            return None

        # Get mask data if provided
        mask_data = None
        if request.mask_base64:
            mask_data = base64.b64decode(request.mask_base64)
        elif request.mask_path:
            async with aiofiles.open(request.mask_path, "rb") as f:
                mask_data = await f.read()

        async with httpx.AsyncClient() as client:
            try:
                files = {
                    "image": ("image.png", image_data, "image/png"),
                    "prompt": (None, request.prompt or ""),
                    "size": (None, request.size),
                    "response_format": (None, "b64_json"),
                }

                if mask_data:
                    files["mask"] = ("mask.png", mask_data, "image/png")

                response = await client.post(
                    f"{settings.OPENAI_API_BASE or 'https://api.openai.com/v1'}/images/edits",
                    headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
                    files=files,
                    timeout=120.0,
                )
                response.raise_for_status()
                data = response.json()

                if data.get("data"):
                    img_data = data["data"][0]
                    edited = EditedImage(
                        id=str(uuid4()),
                        operation=EditOperation.INPAINT,
                        base64_data=img_data.get("b64_json"),
                        url=img_data.get("url"),
                    )

                    # Save to disk
                    if edited.base64_data:
                        file_path = self.storage_dir / f"{edited.id}.png"
                        async with aiofiles.open(file_path, "wb") as f:
                            await f.write(base64.b64decode(edited.base64_data))
                        edited.file_path = str(file_path)

                    return edited

                return None

            except Exception as e:
                logger.error("Inpainting failed", error=str(e))
                return None

    async def _upscale(self, request: ImageEditRequest) -> EditedImage | None:
        """Upscale an image using Stability AI."""
        if not settings.STABILITY_API_KEY:
            logger.error("Stability API key required for upscaling")
            return None

        image_data = await self._get_image_data(request)
        if not image_data:
            return None

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://api.stability.ai/v1/generation/esrgan-v1-x2plus/image-to-image/upscale",
                    headers={
                        "Authorization": f"Bearer {settings.STABILITY_API_KEY}",
                        "Accept": "application/json",
                    },
                    files={
                        "image": ("image.png", image_data, "image/png"),
                    },
                    timeout=120.0,
                )
                response.raise_for_status()
                data = response.json()

                if data.get("artifacts"):
                    artifact = data["artifacts"][0]
                    edited = EditedImage(
                        id=str(uuid4()),
                        operation=EditOperation.UPSCALE,
                        base64_data=artifact.get("base64"),
                        metadata={"seed": artifact.get("seed")},
                    )

                    # Save to disk
                    if edited.base64_data:
                        file_path = self.storage_dir / f"{edited.id}.png"
                        async with aiofiles.open(file_path, "wb") as f:
                            await f.write(base64.b64decode(edited.base64_data))
                        edited.file_path = str(file_path)

                    return edited

                return None

            except Exception as e:
                logger.error("Upscaling failed", error=str(e))
                return None

    async def _remove_background(self, request: ImageEditRequest) -> EditedImage | None:
        """Remove background from an image."""
        # Using remove.bg API or similar
        if not settings.REMOVEBG_API_KEY:
            # Fall back to Replicate's rembg model
            return await self._remove_background_replicate(request)

        image_data = await self._get_image_data(request)
        if not image_data:
            return None

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    "https://api.remove.bg/v1.0/removebg",
                    headers={"X-Api-Key": settings.REMOVEBG_API_KEY},
                    files={"image_file": ("image.png", image_data, "image/png")},
                    data={"size": "auto", "format": "png"},
                    timeout=60.0,
                )
                response.raise_for_status()

                edited = EditedImage(
                    id=str(uuid4()),
                    operation=EditOperation.BACKGROUND_REMOVE,
                    base64_data=base64.b64encode(response.content).decode("utf-8"),
                )

                # Save to disk
                file_path = self.storage_dir / f"{edited.id}.png"
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(response.content)
                edited.file_path = str(file_path)

                return edited

            except Exception as e:
                logger.error("Background removal failed", error=str(e))
                return None

    async def _remove_background_replicate(self, request: ImageEditRequest) -> EditedImage | None:
        """Remove background using Replicate's rembg model."""
        if not settings.REPLICATE_API_KEY:
            logger.error("No background removal API configured")
            return None

        image_data = await self._get_image_data(request)
        if not image_data:
            return None

        async with httpx.AsyncClient() as client:
            try:
                # Use rembg model on Replicate
                response = await client.post(
                    "https://api.replicate.com/v1/predictions",
                    headers={
                        "Authorization": f"Bearer {settings.REPLICATE_API_KEY}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "version": "fb8af171cfa1616ddcf1242c093f9c46bcada5ad4cf6f2fbe8b81b330ec5c003",
                        "input": {
                            "image": f"data:image/png;base64,{base64.b64encode(image_data).decode('utf-8')}",
                        },
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                prediction_id = data.get("id")

                # Poll for result
                for _ in range(60):
                    import asyncio
                    await asyncio.sleep(1)

                    status_response = await client.get(
                        f"https://api.replicate.com/v1/predictions/{prediction_id}",
                        headers={"Authorization": f"Bearer {settings.REPLICATE_API_KEY}"},
                    )
                    status_data = status_response.json()

                    if status_data.get("status") == "succeeded":
                        output_url = status_data.get("output")

                        # Download the result
                        img_response = await client.get(output_url)

                        edited = EditedImage(
                            id=str(uuid4()),
                            operation=EditOperation.BACKGROUND_REMOVE,
                            url=output_url,
                            base64_data=base64.b64encode(img_response.content).decode("utf-8"),
                        )

                        # Save to disk
                        file_path = self.storage_dir / f"{edited.id}.png"
                        async with aiofiles.open(file_path, "wb") as f:
                            await f.write(img_response.content)
                        edited.file_path = str(file_path)

                        return edited

                    if status_data.get("status") == "failed":
                        logger.error("Background removal failed on Replicate")
                        return None

                return None

            except Exception as e:
                logger.error("Background removal (Replicate) failed", error=str(e))
                return None

    async def _outpaint(self, request: ImageEditRequest) -> EditedImage | None:
        """Outpaint (extend) an image."""
        # This would use Stability AI's outpainting or similar
        # For now, return None as it requires specific implementation
        logger.warning("Outpainting not fully implemented")
        return None


# Global service instance
image_editing_service = ImageEditingService()
