"""Image generation service with multiple providers."""

import base64
from abc import ABC, abstractmethod
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

logger = structlog.get_logger()


class ImageProvider(str, Enum):
    """Supported image generation providers."""

    OPENAI_DALLE = "openai_dalle"
    OPENAI_GPT_IMAGE = "openai_gpt_image"
    STABILITY = "stability"
    FLUX = "flux"
    REPLICATE = "replicate"
    LOCAL_SD = "local_sd"


class ImageSize(str, Enum):
    """Standard image sizes."""

    SQUARE_256 = "256x256"
    SQUARE_512 = "512x512"
    SQUARE_1024 = "1024x1024"
    LANDSCAPE_1792 = "1792x1024"
    PORTRAIT_1024 = "1024x1792"
    HD_1920 = "1920x1080"
    CUSTOM = "custom"


class ImageQuality(str, Enum):
    """Image quality settings."""

    STANDARD = "standard"
    HD = "hd"
    ULTRA = "ultra"


class ImageStyle(str, Enum):
    """Image style presets."""

    VIVID = "vivid"
    NATURAL = "natural"
    CINEMATIC = "cinematic"
    ANIME = "anime"
    PHOTOREALISTIC = "photorealistic"


@dataclass
class GeneratedImage:
    """A generated image."""

    id: str
    provider: ImageProvider
    prompt: str
    url: str | None = None
    base64_data: str | None = None
    file_path: str | None = None
    revised_prompt: str | None = None
    width: int | None = None
    height: int | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "provider": self.provider.value,
            "prompt": self.prompt,
            "url": self.url,
            "revised_prompt": self.revised_prompt,
            "width": self.width,
            "height": self.height,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


@dataclass
class ImageGenerationRequest:
    """Request for image generation."""

    prompt: str
    provider: ImageProvider = ImageProvider.OPENAI_DALLE
    size: ImageSize = ImageSize.SQUARE_1024
    quality: ImageQuality = ImageQuality.STANDARD
    style: ImageStyle | None = None
    n: int = 1
    response_format: str = "url"  # url or b64_json
    model: str | None = None
    negative_prompt: str | None = None
    seed: int | None = None
    custom_width: int | None = None
    custom_height: int | None = None


class BaseImageProvider(ABC):
    """Base class for image providers."""

    @abstractmethod
    async def generate(
        self,
        request: ImageGenerationRequest,
    ) -> list[GeneratedImage]:
        """Generate images from a prompt."""
        pass


class OpenAIDALLEProvider(BaseImageProvider):
    """OpenAI DALL-E provider (DALL-E 2 and 3)."""

    def __init__(self, api_key: str | None = None, model: str = "dall-e-3"):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.model = model
        self.base_url = settings.OPENAI_API_BASE or "https://api.openai.com/v1"

    async def generate(
        self,
        request: ImageGenerationRequest,
    ) -> list[GeneratedImage]:
        """Generate images using DALL-E."""
        if not self.api_key:
            logger.error("OpenAI API key not configured")
            return []

        model = request.model or self.model

        # Map size
        size = request.size.value
        if request.size == ImageSize.CUSTOM and request.custom_width and request.custom_height:
            # DALL-E 3 only supports specific sizes
            size = "1024x1024"

        async with httpx.AsyncClient() as client:
            try:
                payload: dict[str, Any] = {
                    "model": model,
                    "prompt": request.prompt,
                    "n": min(request.n, 1 if model == "dall-e-3" else 10),
                    "size": size,
                    "response_format": request.response_format,
                }

                if model == "dall-e-3":
                    payload["quality"] = request.quality.value
                    if request.style:
                        payload["style"] = request.style.value

                response = await client.post(
                    f"{self.base_url}/images/generations",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=120.0,
                )
                response.raise_for_status()
                data = response.json()

                images = []
                for i, img_data in enumerate(data.get("data", [])):
                    width, height = map(int, size.split("x"))
                    images.append(GeneratedImage(
                        id=str(uuid4()),
                        provider=ImageProvider.OPENAI_DALLE,
                        prompt=request.prompt,
                        url=img_data.get("url"),
                        base64_data=img_data.get("b64_json"),
                        revised_prompt=img_data.get("revised_prompt"),
                        width=width,
                        height=height,
                    ))

                return images

            except Exception as e:
                logger.error("DALL-E generation failed", error=str(e))
                return []


class StabilityAIProvider(BaseImageProvider):
    """Stability AI (Stable Diffusion) provider."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.STABILITY_API_KEY
        self.base_url = "https://api.stability.ai/v1"

    async def generate(
        self,
        request: ImageGenerationRequest,
    ) -> list[GeneratedImage]:
        """Generate images using Stability AI."""
        if not self.api_key:
            logger.error("Stability API key not configured")
            return []

        # Parse size
        if request.size != ImageSize.CUSTOM:
            width, height = map(int, request.size.value.split("x"))
        else:
            width = request.custom_width or 1024
            height = request.custom_height or 1024

        async with httpx.AsyncClient() as client:
            try:
                engine_id = request.model or "stable-diffusion-xl-1024-v1-0"

                payload: dict[str, Any] = {
                    "text_prompts": [
                        {"text": request.prompt, "weight": 1.0},
                    ],
                    "width": width,
                    "height": height,
                    "samples": request.n,
                }

                if request.negative_prompt:
                    payload["text_prompts"].append(
                        {"text": request.negative_prompt, "weight": -1.0}
                    )

                if request.seed:
                    payload["seed"] = request.seed

                response = await client.post(
                    f"{self.base_url}/generation/{engine_id}/text-to-image",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "Accept": "application/json",
                    },
                    timeout=120.0,
                )
                response.raise_for_status()
                data = response.json()

                images = []
                for artifact in data.get("artifacts", []):
                    images.append(GeneratedImage(
                        id=str(uuid4()),
                        provider=ImageProvider.STABILITY,
                        prompt=request.prompt,
                        base64_data=artifact.get("base64"),
                        width=width,
                        height=height,
                        metadata={"seed": artifact.get("seed")},
                    ))

                return images

            except Exception as e:
                logger.error("Stability AI generation failed", error=str(e))
                return []


class FluxProvider(BaseImageProvider):
    """Black Forest Labs Flux provider."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.FLUX_API_KEY
        self.base_url = "https://api.bfl.ml/v1"

    async def generate(
        self,
        request: ImageGenerationRequest,
    ) -> list[GeneratedImage]:
        """Generate images using Flux."""
        if not self.api_key:
            logger.error("Flux API key not configured")
            return []

        # Parse size
        if request.size != ImageSize.CUSTOM:
            width, height = map(int, request.size.value.split("x"))
        else:
            width = request.custom_width or 1024
            height = request.custom_height or 1024

        async with httpx.AsyncClient() as client:
            try:
                model = request.model or "flux-pro-1.1"

                payload: dict[str, Any] = {
                    "prompt": request.prompt,
                    "width": width,
                    "height": height,
                }

                if request.seed:
                    payload["seed"] = request.seed

                # Submit generation request
                response = await client.post(
                    f"{self.base_url}/flux-{model.split('-')[-1]}",
                    json=payload,
                    headers={
                        "x-key": self.api_key,
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                request_id = data.get("id")

                # Poll for result
                for _ in range(60):  # Max 60 seconds
                    import asyncio
                    await asyncio.sleep(1)

                    status_response = await client.get(
                        f"{self.base_url}/get_result",
                        params={"id": request_id},
                        headers={"x-key": self.api_key},
                    )
                    status_data = status_response.json()

                    if status_data.get("status") == "Ready":
                        return [GeneratedImage(
                            id=str(uuid4()),
                            provider=ImageProvider.FLUX,
                            prompt=request.prompt,
                            url=status_data.get("result", {}).get("sample"),
                            width=width,
                            height=height,
                        )]

                    if status_data.get("status") == "Error":
                        logger.error("Flux generation error", error=status_data)
                        return []

                return []

            except Exception as e:
                logger.error("Flux generation failed", error=str(e))
                return []


class ReplicateProvider(BaseImageProvider):
    """Replicate provider for various models."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.REPLICATE_API_KEY
        self.base_url = "https://api.replicate.com/v1"

    async def generate(
        self,
        request: ImageGenerationRequest,
    ) -> list[GeneratedImage]:
        """Generate images using Replicate."""
        if not self.api_key:
            logger.error("Replicate API key not configured")
            return []

        # Parse size
        if request.size != ImageSize.CUSTOM:
            width, height = map(int, request.size.value.split("x"))
        else:
            width = request.custom_width or 1024
            height = request.custom_height or 1024

        model = request.model or "stability-ai/sdxl:39ed52f2a78e934b3ba6e2a89f5b1c712de7dfea535525255b1aa35c5565e08b"

        async with httpx.AsyncClient() as client:
            try:
                payload: dict[str, Any] = {
                    "version": model.split(":")[-1] if ":" in model else model,
                    "input": {
                        "prompt": request.prompt,
                        "width": width,
                        "height": height,
                        "num_outputs": request.n,
                    },
                }

                if request.negative_prompt:
                    payload["input"]["negative_prompt"] = request.negative_prompt

                if request.seed:
                    payload["input"]["seed"] = request.seed

                response = await client.post(
                    f"{self.base_url}/predictions",
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                prediction_id = data.get("id")

                # Poll for result
                for _ in range(120):  # Max 2 minutes
                    import asyncio
                    await asyncio.sleep(1)

                    status_response = await client.get(
                        f"{self.base_url}/predictions/{prediction_id}",
                        headers={"Authorization": f"Bearer {self.api_key}"},
                    )
                    status_data = status_response.json()

                    if status_data.get("status") == "succeeded":
                        output = status_data.get("output", [])
                        if isinstance(output, str):
                            output = [output]

                        return [
                            GeneratedImage(
                                id=str(uuid4()),
                                provider=ImageProvider.REPLICATE,
                                prompt=request.prompt,
                                url=url,
                                width=width,
                                height=height,
                            )
                            for url in output
                        ]

                    if status_data.get("status") == "failed":
                        logger.error("Replicate generation failed", error=status_data.get("error"))
                        return []

                return []

            except Exception as e:
                logger.error("Replicate generation failed", error=str(e))
                return []


class ImageGenerationService:
    """Main image generation service."""

    def __init__(self, storage_dir: str | None = None):
        self.storage_dir = Path(storage_dir or settings.UPLOAD_DIR) / "generated_images"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._providers: dict[ImageProvider, BaseImageProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize available providers."""
        if settings.OPENAI_API_KEY:
            self._providers[ImageProvider.OPENAI_DALLE] = OpenAIDALLEProvider()
            self._providers[ImageProvider.OPENAI_GPT_IMAGE] = OpenAIDALLEProvider(model="gpt-image-1")

        if settings.STABILITY_API_KEY:
            self._providers[ImageProvider.STABILITY] = StabilityAIProvider()

        if settings.FLUX_API_KEY:
            self._providers[ImageProvider.FLUX] = FluxProvider()

        if settings.REPLICATE_API_KEY:
            self._providers[ImageProvider.REPLICATE] = ReplicateProvider()

    async def generate(
        self,
        request: ImageGenerationRequest,
        save_to_disk: bool = True,
    ) -> list[GeneratedImage]:
        """Generate images."""
        provider = request.provider

        if provider not in self._providers:
            # Fall back to available provider
            if self._providers:
                provider = list(self._providers.keys())[0]
                logger.warning(
                    "Requested provider not available, falling back",
                    requested=request.provider,
                    using=provider,
                )
            else:
                logger.error("No image generation providers configured")
                return []

        provider_instance = self._providers[provider]
        images = await provider_instance.generate(request)

        # Save to disk if requested
        if save_to_disk:
            for image in images:
                if image.base64_data:
                    file_path = await self._save_image(image)
                    image.file_path = str(file_path)

        return images

    async def _save_image(self, image: GeneratedImage) -> Path:
        """Save a generated image to disk."""
        filename = f"{image.id}.png"
        file_path = self.storage_dir / filename

        if image.base64_data:
            image_data = base64.b64decode(image.base64_data)
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(image_data)
        elif image.url:
            async with httpx.AsyncClient() as client:
                response = await client.get(image.url)
                async with aiofiles.open(file_path, "wb") as f:
                    await f.write(response.content)

        return file_path

    def get_available_providers(self) -> list[ImageProvider]:
        """Get list of available providers."""
        return list(self._providers.keys())

    async def generate_variations(
        self,
        image_path: str,
        prompt: str | None = None,
        n: int = 1,
    ) -> list[GeneratedImage]:
        """Generate variations of an existing image (DALL-E 2 only)."""
        if ImageProvider.OPENAI_DALLE not in self._providers:
            logger.error("OpenAI provider required for variations")
            return []

        # This would use the variations endpoint
        # For now, just return empty - full implementation would read the image
        # and send to OpenAI variations API
        return []


# Global service instance
image_generation_service = ImageGenerationService()
