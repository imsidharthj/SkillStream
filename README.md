# SkillStream — AI Interviewer (MVP)

A voice (or text) AI interviewer. The interviewer first enters the role and the skills to assess. The AI
then interviews the candidate about those skills through an avatar. When **Finish Interview** is pressed,
it produces a structured report for human review and a transcript link to share with the candidate.

```
Browser (React + LiveKit components)
   │  POST /api/sessions → token with agent dispatch            (voice)
   │  POST /api/sessions/{id}/messages                           (chat)
   ▼
FastAPI (backend/api.py) ───────── data/sessions/<id>/*.json ◄──── LiveKit worker (backend/agent.py)
   │                                                               Groq STT → LangGraph agent → ElevenLabs TTS → LiveAvatar
   └─ chat mode calls the same LangGraph agent ───────────────────┘   (backend/interview_graph.py)
```

## Components

| File | Responsibility |
|---|---|
| `backend/config.py` | Reads `.env`, validates mode/avatar values, `require()` gives clear "X is not configured" errors |
| `backend/providers.py` | `build_stt()`, `build_chat_model()`, `build_tts()`, `build_avatar()` — the only place providers are chosen |
| `backend/interview_graph.py` | Interview instructions, the LangGraph tool-calling agent (model ⇄ tools), and report generation |
| `backend/tools.py` | `record_answer`, `get_missing_fields` — closures bound to one session's state |
| `backend/schemas.py` | `build_fields()` (intro + one field per configured skill + availability), `InterviewState`, `TranscriptEntry`, `InterviewReport` |
| `backend/storage.py` | Reads/writes `state.json`, `transcript.json`, `report.json` per session |
| `backend/api.py` | HTTP API: create session from role + skills (and the token in voice mode), chat turn, finish, report, candidate transcript |
| `backend/agent.py` | LiveKit worker: composes STT + graph (via `LLMAdapter`) + TTS + avatar, captures the transcript, writes the report on shutdown |
| `frontend/` | Vite + React + TypeScript app using the official `@livekit/components-react` building blocks |

### Notes on design choices

- **One interview engine.** Voice mode wraps the compiled graph in `livekit.plugins.langchain.LLMAdapter`;
  chat mode calls `graph.ainvoke` from FastAPI. Same prompt, tools, state and report code.
- **Only the interviewer's words are spoken.** The model node streams text through LangGraph's `custom`
  stream and the adapter uses `stream_mode="custom"`. With the default `messages` mode, the adapter would
  also read tool results aloud.
- **Explicit agent dispatch.** The API token includes a `RoomAgentDispatch(agent_name="interviewer")`, and
  the worker registers with that name. LiveKit secrets never leave the backend.
- **Finishing a voice interview.** `POST /finish` deletes the LiveKit room. The agent and avatar sessions
  close, and the worker's shutdown callback saves the final transcript and then generates the report. The
  frontend polls `GET /report` (202 = still generating, 200 = ready, 500 = failed with the reason).
- **Frontend.** The official agent-starter-react is a Next.js app with its own token route, which would
  duplicate the FastAPI one. This app uses the same LiveKit React components (`LiveKitRoom`,
  `useVoiceAssistant`, `VideoTrack`, `BarVisualizer`, `useTranscriptions`) in a small Vite app instead.
- **Avatar.** `AVATAR_PROVIDER=liveavatar` uses the LiveAvatar plugin (a real lip-synced video avatar)
  and fails loudly if it can't start. `AVATAR_PROVIDER=static`, and chat mode, show an illustrated avatar
  (`frontend/src/Avatar.tsx`) that talks, thinks and listens using CSS animation. This is not lip-sync.
  There is no automatic switch between the two.
- **Sharing the transcript.** The report page shows a link, `/?transcript=<session_id>`. It shows the
  candidate only the transcript, never the scores, and only once the interview is completed.
- **Mode switch.** Voice or chat is chosen per interview on the setup screen. `INTERACTION_MODE` is only
  the default selection. Voice is disabled on the setup screen when LiveKit isn't configured. Chat needs
  only `GROQ_API_KEY`.
- **Structured flow.** Each session's plan is built from the setup: background fields, one technical
  field per skill, then wrap-up. The current section comes from what has been recorded, so the
  introduction, the "moving to the technical round" announcement and the wrap-up are triggered by state
  instead of relying on the model to remember them.
- **Candidate camera.** Shown locally on the candidate's screen only. It is never sent to LiveKit or recorded.

## Setup

Prerequisites: Python 3.11+, [uv](https://docs.astral.sh/uv/), Node 20+, a LiveKit Cloud project,
and Groq, ElevenLabs and (optionally) LiveAvatar API keys.

```bash
cp .env.example .env        # then fill in the values
uv sync                     # Python dependencies (uses uv.lock)
cd frontend && npm install && cd ..
```

## Run (three terminals, from the project root)

```bash
# 1. API
uv run uvicorn backend.api:app --port 8000 --reload

# 2. LiveKit worker (voice mode only)
uv run python -m backend.agent dev

# 3. Frontend
cd frontend && npm run dev          # open http://localhost:5173
```

For chat-only use the worker is not needed.

## Voice and chat behaviour

| | Voice | Chat |
|---|---|---|
| Candidate input | Microphone → Groq STT (end of turn detected by VAD) | Text box → `POST /messages` |
| Interviewer output | ElevenLabs speech + avatar (LiveAvatar video, or illustrated avatar animated by agent state) | Text bubble + illustrated avatar animated while "speaking"/"thinking" |
| Conversation panel | Live transcriptions of both sides | The messages themselves |
| Interview logic | Same LangGraph agent, tools, prompt and section flow | Same |
| Saved transcript | Built by the worker from committed conversation items | Built by the API on every turn |
| Finish | API deletes the room → worker saves transcript and writes report → page polls | API writes the report directly |
| Report | Same `InterviewReport` schema, same share link | Same |

## Acceptance criteria

1. The home page introduces SkillStream. Start stays disabled until a role and at least one skill are set.
   Skills can be typed or picked from suggestions (e.g. DSA, System design).
2. The setup screen offers Voice and Chat. Voice is disabled with a reason when LiveKit isn't configured.
3. The first interviewer message introduces SkillStream, states the purpose and role, outlines the three
   sections and the configured topics, then asks for the candidate's name and role.
4. Background questions (name/role, then education/experience) come before any technical question.
5. Before the first technical question the interviewer explicitly says it is moving to the technical
   round, and does so only once. The same applies to the wrap-up.
6. Each configured skill gets at least one targeted question. DSA/coding topics get a problem to reason
   through, design topics get a design scenario. There are at most two follow-ups per skill.
7. Fields already recorded are never asked again, and one answer can fill several fields.
8. The interview screen is split: interviewer (avatar/video with a speaking/listening/thinking status) at
   top-left, the candidate's camera at bottom-left (or a clear message if the camera is denied), and the
   conversation as chat bubbles on the right, scrolling to the newest message. On narrow screens the
   sections stack.
9. Finish Interview produces a report with the same schema in both modes, marked as requiring human review,
   with a transcript link for the candidate that shows the transcript only.

Manual check: run through criteria 1–9 in chat mode, then once in voice mode. Then confirm
`data/sessions/<id>/` holds `state.json`, `transcript.json` and `report.json`.

## Swapping providers

Edit the matching function in `backend/providers.py` (and `.env`). For example, replace `groq.STT` with
`deepgram.STT`, `ChatGroq` with any LangChain chat model that supports tool calling, `elevenlabs.TTS` with
another LiveKit TTS plugin, or `liveavatar.AvatarSession` with another LiveKit avatar plugin.
Nothing else needs to change.
