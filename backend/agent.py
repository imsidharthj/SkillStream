"""LiveKit Agents worker: composes STT + interview graph + TTS + avatar for one room."""

from __future__ import annotations

import logging

from livekit.agents import Agent, AgentServer, AgentSession, ConversationItemAddedEvent, JobContext, cli
from livekit.plugins import langchain, silero

from backend import storage
from backend.api import AGENT_NAME
from backend.config import get_settings, require
from backend.interview_graph import build_interview_graph, generate_report
from backend.providers import build_avatar, build_stt, build_tts
from backend.schemas import TranscriptEntry

logger = logging.getLogger("interviewer")
server = AgentServer(shutdown_process_timeout=60)  # leave time to write the report


@server.rtc_session(agent_name=AGENT_NAME)
async def entrypoint(ctx: JobContext):
    s = get_settings()
    require("LiveKit worker", LIVEKIT_URL=s.livekit_url, LIVEKIT_API_KEY=s.livekit_api_key,
            LIVEKIT_API_SECRET=s.livekit_api_secret)
    session_id = ctx.room.name.removeprefix("interview-")
    state = storage.load_state(session_id)
    if state is None:
        raise RuntimeError(f"No session state for room {ctx.room.name}; create sessions via the API")

    transcript: list[TranscriptEntry] = []
    graph = build_interview_graph(state, storage.save_state)
    session = AgentSession(
        stt=build_stt(),
        llm=langchain.LLMAdapter(graph, stream_mode="custom"),
        tts=build_tts(),
        vad=silero.VAD.load(),  # Groq STT is not streaming, so VAD segments the speech
    )

    # Transcript capture: every committed user/agent message is appended and saved.
    @session.on("conversation_item_added")
    def on_item(ev: ConversationItemAddedEvent):
        text = getattr(ev.item, "text_content", None)
        role = getattr(ev.item, "role", None)
        if text and role in ("user", "assistant"):
            transcript.append(TranscriptEntry(role="candidate" if role == "user" else "interviewer", text=text))
            storage.save_transcript(session_id, transcript)

    async def finalize(reason: str):
        """Runs after the session closes, so the transcript is final."""
        logger.info("finalizing %s (%s)", session_id, reason)
        state.status = "finishing"
        storage.save_state(state)
        storage.save_transcript(session_id, transcript)
        try:
            storage.save_report(await generate_report(state, transcript))
        except Exception as e:
            state.status, state.error = "failed", f"Report generation failed: {e}"
            storage.save_state(state)
            raise
        state.status = "completed"
        storage.save_state(state)

    ctx.add_shutdown_callback(finalize)

    avatar = build_avatar()
    if avatar is not None:
        try:
            await avatar.start(session, room=ctx.room)
        except Exception as e:
            raise RuntimeError(f"LiveAvatar failed to start (AVATAR_PROVIDER=liveavatar): {e}") from e

    # The interview prompt lives in the graph, so the LiveKit Agent has no instructions of its own.
    await session.start(agent=Agent(instructions=""), room=ctx.room)
    session.generate_reply()  # the graph greets the candidate when there are no messages yet


if __name__ == "__main__":
    cli.run_app(server)
