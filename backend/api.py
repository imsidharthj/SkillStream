"""FastAPI endpoints: session/token creation, chat turns, finishing, report retrieval."""

from __future__ import annotations

import uuid
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from livekit import api as lk
from pydantic import BaseModel, Field

from backend import storage
from backend.config import get_settings, require
from backend.interview_graph import build_interview_graph, generate_report, transcript_to_messages
from backend.schemas import InterviewState, TranscriptEntry, build_fields

AGENT_NAME = "interviewer"  # must match the worker's rtc_session(agent_name=...)

app = FastAPI(title="SkillStream AI Interviewer")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])


def room_name(session_id: str) -> str:
    return f"interview-{session_id}"


def get_state(session_id: str) -> InterviewState:
    state = storage.load_state(session_id)
    if state is None:
        raise HTTPException(404, f"Session {session_id} not found")
    return state


async def chat_turn(state: InterviewState, transcript: list[TranscriptEntry]) -> str:
    """Run one interviewer turn on the shared graph and persist the result."""
    graph = build_interview_graph(state, storage.save_state)
    history = transcript_to_messages(transcript)
    result = await graph.ainvoke({"messages": history})
    # Same text voice mode would speak: every interviewer message produced this turn.
    new_messages = result["messages"][len(history):]
    reply = " ".join(m.text for m in new_messages if m.type == "ai" and m.text)
    transcript.append(TranscriptEntry(role="interviewer", text=reply))
    storage.save_transcript(state.session_id, transcript)
    return reply


@app.get("/api/config")
def config():
    s = get_settings()
    voice_ready = bool(s.livekit_url and s.livekit_api_key and s.livekit_api_secret)
    return {"default_mode": s.interaction_mode, "voice_available": voice_ready, "avatar": s.avatar_provider}


class InterviewSetup(BaseModel):
    role: str = Field(min_length=1, max_length=120)
    skills: list[str] = Field(min_length=1, max_length=8)
    mode: Literal["voice", "chat"] | None = None  # chosen on the setup screen; INTERACTION_MODE is the default


@app.post("/api/sessions")
async def create_session(setup: InterviewSetup):
    s = get_settings()
    skills = [k.strip() for k in setup.skills if k.strip()]
    if not skills:
        raise HTTPException(422, "Add at least one skill to assess")
    mode = setup.mode or s.interaction_mode
    session_id = uuid.uuid4().hex
    state = InterviewState(session_id=session_id, mode=mode, role=setup.role.strip(),
                           skills=skills, fields=build_fields(skills))

    if mode == "chat":
        try:
            require("Groq chat model", GROQ_API_KEY=s.groq_api_key)
        except RuntimeError as e:
            raise HTTPException(500, str(e))
        storage.save_state(state)
        greeting = await chat_turn(state, [])
        return {"session_id": session_id, "mode": "chat", "message": greeting}

    try:
        require("LiveKit", LIVEKIT_URL=s.livekit_url, LIVEKIT_API_KEY=s.livekit_api_key,
                LIVEKIT_API_SECRET=s.livekit_api_secret)
    except RuntimeError as e:
        raise HTTPException(500, str(e))
    storage.save_state(state)
    # Explicit dispatch: the token asks LiveKit to send our named agent into the room.
    token = (
        lk.AccessToken(s.livekit_api_key, s.livekit_api_secret)
        .with_identity(f"candidate-{session_id[:8]}")
        .with_grants(lk.VideoGrants(room_join=True, room=room_name(session_id)))
        .with_room_config(lk.RoomConfiguration(agents=[lk.RoomAgentDispatch(agent_name=AGENT_NAME)]))
        .to_jwt()
    )
    return {"session_id": session_id, "mode": "voice", "livekit_url": s.livekit_url, "token": token}


class ChatMessage(BaseModel):
    text: str


@app.post("/api/sessions/{session_id}/messages")
async def send_message(session_id: str, msg: ChatMessage):
    state = get_state(session_id)
    if state.mode != "chat":
        raise HTTPException(400, "This session is a voice session")
    if state.status != "active":
        raise HTTPException(409, "The interview has finished")
    transcript = storage.load_transcript(session_id)
    transcript.append(TranscriptEntry(role="candidate", text=msg.text))
    storage.save_transcript(session_id, transcript)
    return {"message": await chat_turn(state, transcript)}


@app.post("/api/sessions/{session_id}/finish")
async def finish(session_id: str):
    state = get_state(session_id)
    if state.status != "active":
        return {"status": state.status}

    if state.mode == "voice":
        # Closing the room ends the agent session; the worker then saves the
        # transcript and writes the report. The frontend polls GET /report.
        s = get_settings()
        async with lk.LiveKitAPI(s.livekit_url, s.livekit_api_key, s.livekit_api_secret) as client:
            await client.room.delete_room(lk.DeleteRoomRequest(room=room_name(session_id)))
        return {"status": "finishing"}

    state.status = "finishing"
    storage.save_state(state)
    try:
        report = await generate_report(state, storage.load_transcript(session_id))
    except Exception as e:
        state.status, state.error = "failed", f"Report generation failed: {e}"
        storage.save_state(state)
        raise HTTPException(500, state.error)
    storage.save_report(report)
    state.status = "completed"
    storage.save_state(state)
    return {"status": "completed"}


@app.get("/api/sessions/{session_id}/report")
def get_report(session_id: str):
    state = get_state(session_id)
    report = storage.load_report(session_id)
    if report and state.status == "completed":
        return report
    if state.status == "failed":
        raise HTTPException(500, state.error)
    return JSONResponse({"status": state.status}, status_code=202)


@app.get("/api/sessions/{session_id}/transcript")
def get_transcript(session_id: str):
    """Candidate-facing view: the transcript only, available once the interview is completed."""
    state = get_state(session_id)
    if state.status != "completed":
        return JSONResponse({"status": state.status}, status_code=202)
    return {"role": state.role, "created_at": state.created_at, "transcript": storage.load_transcript(session_id)}
