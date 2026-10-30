"""Interview template, session state, transcript and report models."""

from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel, Field


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


Section = Literal["background", "technical", "wrap_up"]


class InterviewField(BaseModel):
    name: str
    question: str
    section: Section


def build_fields(skills: list[str]) -> list[InterviewField]:
    """Interview plan in order: background questions, one technical field per configured skill, wrap-up."""
    fields = [
        InterviewField(name="name_and_role", question="Your name and current or most recent role.", section="background"),
        InterviewField(name="background", question="Your education and relevant professional experience so far.",
                       section="background"),
    ]
    for skill in skills:
        slug = re.sub(r"[^a-z0-9]+", "_", skill.lower()).strip("_")
        fields.append(InterviewField(
            name=f"skill_{slug}",
            question=(f"{skill}: assess real depth. For problem-solving topics such as DSA or coding, pose one short "
                      "problem and have them reason through approach and complexity; for design topics, a small "
                      "design scenario; otherwise a concrete example of using it, with trade-offs."),
            section="technical",
        ))
    fields.append(InterviewField(name="availability", question="When you could start.", section="wrap_up"))
    return fields


class RecordedAnswer(BaseModel):
    field: str
    answer: str


class InterviewState(BaseModel):
    session_id: str
    mode: Literal["voice", "chat"]
    role: str
    skills: list[str]
    fields: list[InterviewField]
    announced_sections: list[Section] = Field(default_factory=list)  # section transitions already spoken
    status: Literal["active", "finishing", "completed", "failed"] = "active"
    error: str | None = None
    answers: dict[str, RecordedAnswer] = Field(default_factory=dict)
    created_at: str = Field(default_factory=now)

    def missing_fields(self) -> list[InterviewField]:
        return [f for f in self.fields if f.name not in self.answers]

    def current_section(self) -> Section | None:
        missing = self.missing_fields()
        return missing[0].section if missing else None


class TranscriptEntry(BaseModel):
    role: Literal["candidate", "interviewer"]
    text: str
    timestamp: str = Field(default_factory=now)


class QuestionAnswer(BaseModel):
    question: str
    answer: str


class RubricScore(BaseModel):
    category: str
    score: int = Field(ge=1, le=5)
    evidence: str = Field(description="Direct evidence from the transcript supporting the score")


class ReportContent(BaseModel):
    """The part of the report written by the LLM."""

    summary: str
    questions_and_answers: list[QuestionAnswer]
    key_strengths: list[str]
    missing_information: list[str]
    rubric_scores: list[RubricScore] = Field(
        description="Only include a score when the transcript contains clear evidence for it"
    )
    draft_final_answers: list[RecordedAnswer] = Field(
        description="One cleaned-up final answer per template field, using only what the candidate said"
    )


class InterviewReport(ReportContent):
    session_id: str
    generated_at: str = Field(default_factory=now)
    requires_human_review: bool = True
    transcript: list[TranscriptEntry]
