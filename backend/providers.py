"""Provider factories. Swapping a provider only touches this file and .env."""

from __future__ import annotations

from backend.config import get_settings, require


def build_stt():
    from livekit.plugins import groq

    s = get_settings()
    require("Groq STT", GROQ_API_KEY=s.groq_api_key)
    return groq.STT(model=s.groq_stt_model, language=s.groq_stt_language, api_key=s.groq_api_key)


def build_chat_model():
    from langchain_groq import ChatGroq

    s = get_settings()
    require("Groq chat model", GROQ_API_KEY=s.groq_api_key, GROQ_CHAT_MODEL=s.groq_chat_model)
    return ChatGroq(model=s.groq_chat_model, api_key=s.groq_api_key, temperature=0.3)


def build_tts():
    from livekit.plugins import elevenlabs

    s = get_settings()
    require("ElevenLabs TTS", ELEVEN_API_KEY=s.eleven_api_key, ELEVENLABS_VOICE_ID=s.elevenlabs_voice_id)
    return elevenlabs.TTS(voice_id=s.elevenlabs_voice_id, model=s.elevenlabs_model_id, api_key=s.eleven_api_key)


def build_avatar():
    """Return a LiveAvatar session, or None when AVATAR_PROVIDER=static."""
    s = get_settings()
    if s.avatar_provider == "static":
        return None
    from livekit.plugins import liveavatar

    require("LiveAvatar", LIVEAVATAR_API_KEY=s.liveavatar_api_key, LIVEAVATAR_AVATAR_ID=s.liveavatar_avatar_id)
    return liveavatar.AvatarSession(avatar_id=s.liveavatar_avatar_id, api_key=s.liveavatar_api_key)
