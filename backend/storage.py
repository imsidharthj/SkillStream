"""JSON files under data/sessions/<session_id>/. All filesystem access lives here."""

from __future__ import annotations

import json
from pathlib import Path

from backend.schemas import InterviewReport, InterviewState, TranscriptEntry

DATA_DIR = Path(__file__).resolve().parent.parent / "data" / "sessions"


def _path(session_id: str, name: str) -> Path:
    if not session_id.isalnum():
        raise ValueError(f"Invalid session id: {session_id!r}")
    return DATA_DIR / session_id / name


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(text)
    tmp.replace(path)  # atomic, so the API never reads a half-written file


def save_state(state: InterviewState) -> None:
    _write(_path(state.session_id, "state.json"), state.model_dump_json(indent=2))


def load_state(session_id: str) -> InterviewState | None:
    p = _path(session_id, "state.json")
    return InterviewState.model_validate_json(p.read_text()) if p.exists() else None


def save_transcript(session_id: str, transcript: list[TranscriptEntry]) -> None:
    _write(_path(session_id, "transcript.json"), json.dumps([t.model_dump() for t in transcript], indent=2))


def load_transcript(session_id: str) -> list[TranscriptEntry]:
    p = _path(session_id, "transcript.json")
    return [TranscriptEntry(**t) for t in json.loads(p.read_text())] if p.exists() else []


def save_report(report: InterviewReport) -> None:
    _write(_path(report.session_id, "report.json"), report.model_dump_json(indent=2))


def load_report(session_id: str) -> InterviewReport | None:
    p = _path(session_id, "report.json")
    return InterviewReport.model_validate_json(p.read_text()) if p.exists() else None
