"""Speech-to-Text (STT) service with multiple providers."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import uuid4

import aiofiles
import httpx
import structlog

from app.core.config import settings

logger = structlog.get_logger()


class STTProvider(str, Enum):
    """Supported STT providers."""

    OPENAI_WHISPER = "openai_whisper"
    AZURE_SPEECH = "azure_speech"
    GOOGLE_SPEECH = "google_speech"
    DEEPGRAM = "deepgram"
    ASSEMBLY_AI = "assembly_ai"
    LOCAL_WHISPER = "local_whisper"


class TranscriptionLanguage(str, Enum):
    """Common transcription languages."""

    ENGLISH = "en"
    SPANISH = "es"
    FRENCH = "fr"
    GERMAN = "de"
    ITALIAN = "it"
    PORTUGUESE = "pt"
    CHINESE = "zh"
    JAPANESE = "ja"
    KOREAN = "ko"
    ARABIC = "ar"
    RUSSIAN = "ru"
    AUTO = "auto"


@dataclass
class TranscriptionSegment:
    """A segment of transcribed audio."""

    text: str
    start_time: float
    end_time: float
    confidence: float | None = None
    speaker: str | None = None


@dataclass
class TranscriptionResult:
    """Result of speech-to-text transcription."""

    id: str
    text: str
    language: str | None = None
    duration_seconds: float | None = None
    segments: list[TranscriptionSegment] = field(default_factory=list)
    words: list[dict[str, Any]] = field(default_factory=list)
    confidence: float | None = None
    provider: STTProvider | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "text": self.text,
            "language": self.language,
            "duration_seconds": self.duration_seconds,
            "segments": [
                {
                    "text": s.text,
                    "start_time": s.start_time,
                    "end_time": s.end_time,
                    "confidence": s.confidence,
                    "speaker": s.speaker,
                }
                for s in self.segments
            ],
            "confidence": self.confidence,
            "provider": self.provider.value if self.provider else None,
            "created_at": self.created_at.isoformat(),
            "metadata": self.metadata,
        }


class BaseSTTProvider(ABC):
    """Base class for STT providers."""

    @abstractmethod
    async def transcribe(
        self,
        audio_data: bytes,
        language: str | None = None,
        **kwargs,
    ) -> TranscriptionResult:
        """Transcribe audio to text."""
        pass


class OpenAIWhisperProvider(BaseSTTProvider):
    """OpenAI Whisper API provider."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.OPENAI_API_KEY
        self.base_url = settings.OPENAI_API_BASE or "https://api.openai.com/v1"

    async def transcribe(
        self,
        audio_data: bytes,
        language: str | None = None,
        model: str = "whisper-1",
        response_format: str = "verbose_json",
        timestamp_granularities: list[str] | None = None,
        **kwargs,
    ) -> TranscriptionResult:
        """Transcribe using OpenAI Whisper."""
        if not self.api_key:
            logger.error("OpenAI API key not configured")
            return TranscriptionResult(id=str(uuid4()), text="", metadata={"error": "API key not configured"})

        async with httpx.AsyncClient() as client:
            try:
                files = {
                    "file": ("audio.wav", audio_data, "audio/wav"),
                    "model": (None, model),
                    "response_format": (None, response_format),
                }

                if language and language != "auto":
                    files["language"] = (None, language)

                if timestamp_granularities:
                    for granularity in timestamp_granularities:
                        files[f"timestamp_granularities[]"] = (None, granularity)

                response = await client.post(
                    f"{self.base_url}/audio/transcriptions",
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    files=files,
                    timeout=120.0,
                )
                response.raise_for_status()
                data = response.json()

                # Parse segments
                segments = []
                if "segments" in data:
                    for seg in data["segments"]:
                        segments.append(TranscriptionSegment(
                            text=seg.get("text", ""),
                            start_time=seg.get("start", 0.0),
                            end_time=seg.get("end", 0.0),
                            confidence=seg.get("avg_logprob"),
                        ))

                # Parse words if available
                words = data.get("words", [])

                return TranscriptionResult(
                    id=str(uuid4()),
                    text=data.get("text", ""),
                    language=data.get("language"),
                    duration_seconds=data.get("duration"),
                    segments=segments,
                    words=words,
                    provider=STTProvider.OPENAI_WHISPER,
                )

            except Exception as e:
                logger.error("Whisper transcription failed", error=str(e))
                return TranscriptionResult(
                    id=str(uuid4()),
                    text="",
                    metadata={"error": str(e)},
                )


class AzureSpeechProvider(BaseSTTProvider):
    """Azure Speech Services provider."""

    def __init__(
        self,
        api_key: str | None = None,
        region: str | None = None,
    ):
        self.api_key = api_key or settings.AZURE_SPEECH_KEY
        self.region = region or settings.AZURE_SPEECH_REGION or "eastus"
        self.base_url = f"https://{self.region}.stt.speech.microsoft.com"

    async def transcribe(
        self,
        audio_data: bytes,
        language: str | None = None,
        **kwargs,
    ) -> TranscriptionResult:
        """Transcribe using Azure Speech Services."""
        if not self.api_key:
            logger.error("Azure Speech API key not configured")
            return TranscriptionResult(id=str(uuid4()), text="")

        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    f"{self.base_url}/speech/recognition/conversation/cognitiveservices/v1",
                    headers={
                        "Ocp-Apim-Subscription-Key": self.api_key,
                        "Content-Type": "audio/wav",
                    },
                    params={
                        "language": language or "en-US",
                    },
                    content=audio_data,
                    timeout=120.0,
                )
                response.raise_for_status()
                data = response.json()

                return TranscriptionResult(
                    id=str(uuid4()),
                    text=data.get("DisplayText", ""),
                    language=language,
                    duration_seconds=data.get("Duration", 0) / 10000000,  # Ticks to seconds
                    confidence=data.get("Confidence"),
                    provider=STTProvider.AZURE_SPEECH,
                )

            except Exception as e:
                logger.error("Azure Speech transcription failed", error=str(e))
                return TranscriptionResult(id=str(uuid4()), text="")


class DeepgramProvider(BaseSTTProvider):
    """Deepgram STT provider."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.DEEPGRAM_API_KEY
        self.base_url = "https://api.deepgram.com/v1"

    async def transcribe(
        self,
        audio_data: bytes,
        language: str | None = None,
        model: str = "nova-2",
        **kwargs,
    ) -> TranscriptionResult:
        """Transcribe using Deepgram."""
        if not self.api_key:
            logger.error("Deepgram API key not configured")
            return TranscriptionResult(id=str(uuid4()), text="")

        async with httpx.AsyncClient() as client:
            try:
                params = {
                    "model": model,
                    "smart_format": "true",
                    "punctuate": "true",
                    "paragraphs": "true",
                    "utterances": "true",
                }

                if language and language != "auto":
                    params["language"] = language
                else:
                    params["detect_language"] = "true"

                response = await client.post(
                    f"{self.base_url}/listen",
                    headers={
                        "Authorization": f"Token {self.api_key}",
                        "Content-Type": "audio/wav",
                    },
                    params=params,
                    content=audio_data,
                    timeout=120.0,
                )
                response.raise_for_status()
                data = response.json()

                # Extract results
                results = data.get("results", {})
                channels = results.get("channels", [{}])
                alternatives = channels[0].get("alternatives", [{}]) if channels else [{}]
                transcript = alternatives[0].get("transcript", "") if alternatives else ""

                # Parse words
                words = alternatives[0].get("words", []) if alternatives else []

                # Create segments from utterances
                segments = []
                for utterance in results.get("utterances", []):
                    segments.append(TranscriptionSegment(
                        text=utterance.get("transcript", ""),
                        start_time=utterance.get("start", 0.0),
                        end_time=utterance.get("end", 0.0),
                        confidence=utterance.get("confidence"),
                        speaker=str(utterance.get("speaker")) if utterance.get("speaker") is not None else None,
                    ))

                return TranscriptionResult(
                    id=str(uuid4()),
                    text=transcript,
                    language=results.get("channels", [{}])[0].get("detected_language"),
                    duration_seconds=data.get("metadata", {}).get("duration"),
                    segments=segments,
                    words=words,
                    confidence=alternatives[0].get("confidence") if alternatives else None,
                    provider=STTProvider.DEEPGRAM,
                )

            except Exception as e:
                logger.error("Deepgram transcription failed", error=str(e))
                return TranscriptionResult(id=str(uuid4()), text="")


class AssemblyAIProvider(BaseSTTProvider):
    """AssemblyAI STT provider."""

    def __init__(self, api_key: str | None = None):
        self.api_key = api_key or settings.ASSEMBLYAI_API_KEY
        self.base_url = "https://api.assemblyai.com/v2"

    async def transcribe(
        self,
        audio_data: bytes,
        language: str | None = None,
        **kwargs,
    ) -> TranscriptionResult:
        """Transcribe using AssemblyAI."""
        if not self.api_key:
            logger.error("AssemblyAI API key not configured")
            return TranscriptionResult(id=str(uuid4()), text="")

        async with httpx.AsyncClient() as client:
            try:
                # First upload the audio
                upload_response = await client.post(
                    f"{self.base_url}/upload",
                    headers={"Authorization": self.api_key},
                    content=audio_data,
                    timeout=60.0,
                )
                upload_response.raise_for_status()
                audio_url = upload_response.json().get("upload_url")

                # Create transcription
                transcript_request = {
                    "audio_url": audio_url,
                    "punctuate": True,
                    "format_text": True,
                }

                if language and language != "auto":
                    transcript_request["language_code"] = language
                else:
                    transcript_request["language_detection"] = True

                create_response = await client.post(
                    f"{self.base_url}/transcript",
                    headers={
                        "Authorization": self.api_key,
                        "Content-Type": "application/json",
                    },
                    json=transcript_request,
                    timeout=30.0,
                )
                create_response.raise_for_status()
                transcript_id = create_response.json().get("id")

                # Poll for result
                for _ in range(120):  # Max 2 minutes
                    import asyncio
                    await asyncio.sleep(1)

                    status_response = await client.get(
                        f"{self.base_url}/transcript/{transcript_id}",
                        headers={"Authorization": self.api_key},
                    )
                    status_data = status_response.json()

                    if status_data.get("status") == "completed":
                        # Parse words into segments
                        segments = []
                        words = status_data.get("words", [])

                        return TranscriptionResult(
                            id=str(uuid4()),
                            text=status_data.get("text", ""),
                            language=status_data.get("language_code"),
                            duration_seconds=status_data.get("audio_duration"),
                            segments=segments,
                            words=words,
                            confidence=status_data.get("confidence"),
                            provider=STTProvider.ASSEMBLY_AI,
                        )

                    if status_data.get("status") == "error":
                        logger.error("AssemblyAI transcription error", error=status_data.get("error"))
                        return TranscriptionResult(id=str(uuid4()), text="")

                return TranscriptionResult(id=str(uuid4()), text="")

            except Exception as e:
                logger.error("AssemblyAI transcription failed", error=str(e))
                return TranscriptionResult(id=str(uuid4()), text="")


class SpeechToTextService:
    """Main STT service with provider abstraction."""

    def __init__(self):
        self._providers: dict[STTProvider, BaseSTTProvider] = {}
        self._initialize_providers()

    def _initialize_providers(self) -> None:
        """Initialize available providers."""
        if settings.OPENAI_API_KEY:
            self._providers[STTProvider.OPENAI_WHISPER] = OpenAIWhisperProvider()

        if settings.AZURE_SPEECH_KEY:
            self._providers[STTProvider.AZURE_SPEECH] = AzureSpeechProvider()

        if settings.DEEPGRAM_API_KEY:
            self._providers[STTProvider.DEEPGRAM] = DeepgramProvider()

        if settings.ASSEMBLYAI_API_KEY:
            self._providers[STTProvider.ASSEMBLY_AI] = AssemblyAIProvider()

    async def transcribe(
        self,
        audio_data: bytes,
        provider: STTProvider | None = None,
        language: str | None = None,
        **kwargs,
    ) -> TranscriptionResult:
        """Transcribe audio to text."""
        # Select provider
        if provider and provider in self._providers:
            selected_provider = provider
        elif self._providers:
            # Prefer Whisper
            if STTProvider.OPENAI_WHISPER in self._providers:
                selected_provider = STTProvider.OPENAI_WHISPER
            else:
                selected_provider = list(self._providers.keys())[0]
        else:
            logger.error("No STT providers configured")
            return TranscriptionResult(id=str(uuid4()), text="")

        provider_instance = self._providers[selected_provider]
        return await provider_instance.transcribe(audio_data, language, **kwargs)

    async def transcribe_file(
        self,
        file_path: str,
        provider: STTProvider | None = None,
        language: str | None = None,
        **kwargs,
    ) -> TranscriptionResult:
        """Transcribe an audio file."""
        async with aiofiles.open(file_path, "rb") as f:
            audio_data = await f.read()

        return await self.transcribe(audio_data, provider, language, **kwargs)

    def get_available_providers(self) -> list[STTProvider]:
        """Get list of available providers."""
        return list(self._providers.keys())


# Global service instance
stt_service = SpeechToTextService()
