"""Text-to-Speech (TTS) service with multiple providers."""

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


class TTSProvider(str, Enum):
    """Supported TTS providers."""

    OPENAI = "openai"
    AZURE = "azure"
    ELEVENLABS = "elevenlabs"
    GOOGLE = "google"
    AWS_POLLY = "aws_polly"


class TTSVoice(str, Enum):
    """Standard TTS voices (OpenAI)."""

    ALLOY = "alloy"
    ECHO = "echo"
    FABLE = "fable"
    ONYX = "onyx"
    NOVA = "nova"
    SHIMMER = "shimmer"


class AudioFormat(str, Enum):
    """Audio output formats."""

    MP3 = "mp3"
    WAV = "wav"
    OGG = "ogg"
    FLAC = "flac"
    PCM = "pcm"


@dataclass
class AudioResult:
    """Result of text-to-speech synthesis."""

    id: str
    text: str
    audio_data: bytes | None = None
    audio_base64: str | None = None
    file_path: str | None = None
    format: AudioFormat = AudioFormat.MP3
    duration_seconds: float | None = None
    provider: TTSProvider | None = None
    voice: str | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary (without binary data)."""
        return {
            "id": self.id,
            "text": self.text,
            "file_path": self.file_path,
            "format": self.format.value,
            "duration_seconds": self.duration_seconds,
            "provider": self.provider.value if self.provider else None,
            "voice": self.voice,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


class BaseTTSProvider(ABC):
    """Base class for TTS providers."""

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        **kwargs,
    ) -> AudioResult:
        """Synthesize speech from text."""
        pass


class OpenAITTSProvider(BaseTTSProvider):
    """OpenAI TTS provider."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_API_BASE or "https://api.openai.com/v1"

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        model: str = "tts-1",
        response_format: str = "mp3",
        speed: float = 1.0,
        **kwargs,
    ) -> AudioResult:
        """Synthesize using OpenAI TTS."""
        if not self.api_key:
            logger.error("OpenAI API key not configured")
            return AudioResult(id=str(uuid4()), text=text)

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/audio/speech",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": model,
                        "input": text,
                        "voice": voice or TTSVoice.ALLOY.value,
                        "response_format": response_format,
                        "speed": speed,
                    },
                    timeout=60.0,
                )
                response.raise_for_status()

                audio_data = response.content

                return AudioResult(
                    id=str(uuid4()),
                    text=text,
                    audio_data=audio_data,
                    audio_base64=base64.b64encode(audio_data).decode("utf-8"),
                    format=AudioFormat(response_format),
                    provider=TTSProvider.OPENAI,
                    voice=voice or TTSVoice.ALLOY.value,
                )

            except Exception as e:
                logger.error("OpenAI TTS failed", error=str(e))
                return AudioResult(id=str(uuid4()), text=text)


class AzureTTSProvider(BaseTTSProvider):
    """Azure Speech Services TTS provider."""

    def __init__(
        self,
        api_key: str | None = None,
        region: str | None = None,
    ):
        self.api_key = api_key or settings.AZURE_SPEECH_KEY
        self.region = region or settings.AZURE_SPEECH_REGION or "eastus"
        self.base_url = f"https://{self.region}.tts.speech.microsoft.com"

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        output_format: str = "audio-24khz-48kbitrate-mono-mp3",
        **kwargs,
    ) -> AudioResult:
        """Synthesize using Azure TTS."""
        if not self.api_key:
            logger.error("Azure Speech API key not configured")
            return AudioResult(id=str(uuid4()), text=text)

        voice_name = voice or "en-US-JennyNeural"

        ssml = f"""
        <speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>
            <voice name='{voice_name}'>{text}</voice>
        </speak>
        """

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/cognitiveservices/v1",
                    headers={
                        "Ocp-Apim-Subscription-Key": self.api_key,
                        "Content-Type": "application/ssml+xml",
                        "X-Microsoft-OutputFormat": output_format,
                    },
                    content=ssml,
                    timeout=60.0,
                )
                response.raise_for_status()

                audio_data = response.content

                return AudioResult(
                    id=str(uuid4()),
                    text=text,
                    audio_data=audio_data,
                    audio_base64=base64.b64encode(audio_data).decode("utf-8"),
                    format=AudioFormat.MP3,
                    provider=TTSProvider.AZURE,
                    voice=voice_name,
                )

            except Exception as e:
                logger.error("Azure TTS failed", error=str(e))
                return AudioResult(id=str(uuid4()), text=text)


class ElevenLabsTTSProvider(BaseTTSProvider):
    """ElevenLabs TTS provider."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.ELEVENLABS_API_KEY
        self.base_url = "https://api.elevenlabs.io/v1"

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        model_id: str = "eleven_multilingual_v2",
        stability: float = 0.5,
        similarity_boost: float = 0.75,
        **kwargs,
    ) -> AudioResult:
        """Synthesize using ElevenLabs."""
        if not self.api_key:
            logger.error("ElevenLabs API key not configured")
            return AudioResult(id=str(uuid4()), text=text)

        voice_id = voice or "21m00Tcm4TlvDq8ikWAM"  # Rachel voice

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/text-to-speech/{voice_id}",
                    headers={
                        "xi-api-key": self.api_key,
                        "Content-Type": "application/json",
                        "Accept": "audio/mpeg",
                    },
                    json={
                        "text": text,
                        "model_id": model_id,
                        "voice_settings": {
                            "stability": stability,
                            "similarity_boost": similarity_boost,
                        },
                    },
                    timeout=60.0,
                )
                response.raise_for_status()

                audio_data = response.content

                return AudioResult(
                    id=str(uuid4()),
                    text=text,
                    audio_data=audio_data,
                    audio_base64=base64.b64encode(audio_data).decode("utf-8"),
                    format=AudioFormat.MP3,
                    provider=TTSProvider.ELEVENLABS,
                    voice=voice_id,
                )

            except Exception as e:
                logger.error("ElevenLabs TTS failed", error=str(e))
                return AudioResult(id=str(uuid4()), text=text)

    async def list_voices(self) -> list[dict[str, Any]]:
        """List available voices."""
        if not self.api_key:
            return []

        async with httpx.AsyncClient() as client:
            try:
                response = await client.get(
                    f"{self.base_url}/voices",
                    headers={"xi-api-key": self.api_key},
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

                return [
                    {
                        "voice_id": v.get("voice_id"),
                        "name": v.get("name"),
                        "category": v.get("category"),
                        "labels": v.get("labels", {}),
                    }
                    for v in data.get("voices", [])
                ]

            except Exception as e:
                logger.error("Failed to list ElevenLabs voices", error=str(e))
                return []


class GoogleTTSProvider(BaseTTSProvider):
    """Google Cloud TTS provider."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.GOOGLE_TTS_API_KEY
        self.base_url = "https://texttospeech.googleapis.com/v1"

    async def synthesize(
        self,
        text: str,
        voice: str | None = None,
        language_code: str = "en-US",
        audio_encoding: str = "MP3",
        **kwargs,
    ) -> AudioResult:
        """Synthesize using Google TTS."""
        if not self.api_key:
            logger.error("Google TTS API key not configured")
            return AudioResult(id=str(uuid4()), text=text)

        voice_name = voice or "en-US-Wavenet-D"

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/text:synthesize",
                    params={"key": self.api_key},
                    json={
                        "input": {"text": text},
                        "voice": {
                            "languageCode": language_code,
                            "name": voice_name,
                        },
                        "audioConfig": {"audioEncoding": audio_encoding},
                    },
                    timeout=60.0,
                )
                response.raise_for_status()
                data = response.json()

                audio_content = data.get("audioContent", "")
                audio_data = base64.b64decode(audio_content)

                return AudioResult(
                    id=str(uuid4()),
                    text=text,
                    audio_data=audio_data,
                    audio_base64=audio_content,
                    format=AudioFormat.MP3,
                    provider=TTSProvider.GOOGLE,
                    voice=voice_name,
                )

            except Exception as e:
                logger.error("Google TTS failed", error=str(e))
                return AudioResult(id=str(uuid4()), text=text)


class TextToSpeechService:
    """Main TTS service with provider abstraction."""

    def __init__(self, storage_dir: str | None = None):
        self.storage_dir = Path(storage_dir or settings.UPLOAD_DIR) / "tts_audio"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._providers: dict[TTSProvider, BaseTTSProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize available providers."""
        if settings.OPENAI_API_KEY:
            self._providers[TTSProvider.OPENAI] = OpenAITTSProvider()

        if settings.AZURE_SPEECH_KEY:
            self._providers[TTSProvider.AZURE] = AzureTTSProvider()

        if settings.ELEVENLABS_API_KEY:
            self._providers[TTSProvider.ELEVENLABS] = ElevenLabsTTSProvider()

        if settings.GOOGLE_TTS_API_KEY:
            self._providers[TTSProvider.GOOGLE] = GoogleTTSProvider()

    async def synthesize(
        self,
        text: str,
        provider: TTSProvider | None = None,
        voice: str | None = None,
        save_to_disk: bool = True,
        **kwargs,
    ) -> AudioResult:
        """Synthesize speech from text."""
        # Select provider
        if provider and provider in self._providers:
            selected_provider = provider
        elif self._providers:
            # Prefer OpenAI
            if TTSProvider.OPENAI in self._providers:
                selected_provider = TTSProvider.OPENAI
            else:
                selected_provider = list(self._providers.keys())[0]
        else:
            logger.error("No TTS providers configured")
            return AudioResult(id=str(uuid4()), text=text)

        provider_instance = self._providers[selected_provider]
        result = await provider_instance.synthesize(text, voice, **kwargs)

        # Save to disk if requested
        if save_to_disk and result.audio_data:
            file_path = self.storage_dir / f"{result.id}.{result.format.value}"
            async with aiofiles.open(file_path, "wb") as f:
                await f.write(result.audio_data)
            result.file_path = str(file_path)

        return result

    def get_available_providers(self) -> list[TTSProvider]:
        """Get list of available providers."""
        return list(self._providers.keys())

    def get_voices(self, provider: TTSProvider | None = None) -> list[dict[str, str]]:
        """Get available voices for a provider."""
        if provider == TTSProvider.OPENAI or provider is None:
            return [
                {"id": v.value, "name": v.value.title()}
                for v in TTSVoice
            ]
        elif provider == TTSProvider.AZURE:
            # Azure has many voices - return common ones
            return [
                {"id": "en-US-JennyNeural", "name": "Jenny (US)"},
                {"id": "en-US-GuyNeural", "name": "Guy (US)"},
                {"id": "en-GB-SoniaNeural", "name": "Sonia (UK)"},
                {"id": "en-AU-NatashaNeural", "name": "Natasha (AU)"},
            ]

        return []


# Global service instance
tts_service = TextToSpeechService()
