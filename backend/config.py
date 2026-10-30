"""Settings loaded from environment variables (.env in the project root)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")


@dataclass(frozen=True)
class Settings:
    interaction_mode: str
    livekit_url: str
    livekit_api_key: str
    livekit_api_secret: str
    groq_api_key: str
    groq_stt_model: str
    groq_stt_language: str
    groq_chat_model: str
    eleven_api_key: str
    elevenlabs_model_id: str
    elevenlabs_voice_id: str
    avatar_provider: str
    liveavatar_api_key: str
    liveavatar_avatar_id: str


@lru_cache
def get_settings() -> Settings:
    s = Settings(
        interaction_mode=os.getenv("INTERACTION_MODE", "voice").strip().lower(),
        livekit_url=os.getenv("LIVEKIT_URL", ""),
        livekit_api_key=os.getenv("LIVEKIT_API_KEY", ""),
        livekit_api_secret=os.getenv("LIVEKIT_API_SECRET", ""),
        groq_api_key=os.getenv("GROQ_API_KEY", ""),
        groq_stt_model=os.getenv("GROQ_STT_MODEL", "whisper-large-v3-turbo"),
        groq_stt_language=os.getenv("GROQ_STT_LANGUAGE", "en"),
        groq_chat_model=os.getenv("GROQ_CHAT_MODEL", "openai/gpt-oss-120b"),
        eleven_api_key=os.getenv("ELEVEN_API_KEY", ""),
        elevenlabs_model_id=os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5"),
        elevenlabs_voice_id=os.getenv("ELEVENLABS_VOICE_ID", ""),
        avatar_provider=os.getenv("AVATAR_PROVIDER", "static").strip().lower(),
        liveavatar_api_key=os.getenv("LIVEAVATAR_API_KEY", ""),
        liveavatar_avatar_id=os.getenv("LIVEAVATAR_AVATAR_ID", ""),
    )
    if s.interaction_mode not in ("voice", "chat"):
        raise ValueError(f"INTERACTION_MODE must be 'voice' or 'chat', got {s.interaction_mode!r}")
    if s.avatar_provider not in ("liveavatar", "static"):
        raise ValueError(f"AVATAR_PROVIDER must be 'liveavatar' or 'static', got {s.avatar_provider!r}")
    return s


def require(component: str, **values: str) -> None:
    """Raise a clear error naming the component and every missing variable."""
    missing = [name for name, value in values.items() if not value]
    if missing:
        raise RuntimeError(f"{component} is not configured: set {', '.join(missing)} in .env")
