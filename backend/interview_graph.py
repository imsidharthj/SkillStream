"""Interview policy: the LangGraph tool-calling agent and the report generator.

Both voice mode (via LiveKit's LLMAdapter) and chat mode (via FastAPI) use this file.
"""

from __future__ import annotations

from typing import Annotated, Callable, TypedDict

from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage, HumanMessage, SystemMessage
from langgraph.config import get_stream_writer
from langgraph.graph import END, START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode

from backend.providers import build_chat_model
from backend.schemas import InterviewReport, InterviewState, ReportContent, TranscriptEntry
from backend.tools import create_tools

INSTRUCTIONS = """\
You are the SkillStream AI interviewer, running a structured screening interview for this role: {role}.
Your replies are spoken aloud: plain sentences only, no markdown, lists or emojis.

The interview has three sections, in this order:
1. Introduction and background: who the candidate is and their experience.
2. Technical round: the skills configured by the hiring team: {skills}.
3. Wrap-up: availability, then close the interview.

Interview fields (in order):
{fields}

Already recorded (never ask for these again):
{answers}

Current section: {section}
{stage_instruction}

Every turn, in this order:
1. For every field the candidate's latest message gives concrete information about (even briefly), call
   record_answer first, without writing any text alongside the tool calls. One message can answer
   several fields. Match answers by their content, not by the question you asked.
2. Then reply with exactly one question, about the first field that is NOT recorded yet. If the last
   answer was vague, ask one short follow-up that names the specific missing detail instead.
   In the technical round, ask practical questions that reveal real depth (how they used it, a trade-off,
   a problem they solved; for topics like DSA, a short problem to reason through out loud). Go deeper when
   answers are strong, simpler when they struggle. At most two follow-ups per skill, then record and move on.

Rules:
- Keep normal turns to at most three sentences.
- Never invent facts, achievements or numbers. Do not evaluate the candidate during the interview.
"""

OPENING = (
    "This is the start of the interview. Introduce yourself as the SkillStream AI interviewer, explain that this "
    "is a screening interview for the {role} role, briefly outline the three sections and the technical topics, "
    "say the candidate can take their time, then ask the first background question. Up to six sentences."
)
TRANSITIONS = {
    "technical": "The background section is complete. Before your next question, tell the candidate clearly that "
                 "you are now moving to the technical round and which topics it covers.",
    "wrap_up": "The technical round is complete. Before your next question, tell the candidate that the technical "
               "round is done and you are moving to a short wrap-up.",
}
CLOSING = "Every field is recorded. Thank the candidate warmly and tell them they can press Finish Interview."


class GraphState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]


def stage_instruction(state: InterviewState, opening: bool) -> str:
    """What this turn must do, decided from the recorded state rather than left to the model."""
    section = state.current_section()
    if opening:
        return OPENING.format(role=state.role)
    if section is None:
        return CLOSING
    if section in TRANSITIONS and section not in state.announced_sections:
        return TRANSITIONS[section]
    return ""


def system_prompt(state: InterviewState, opening: bool) -> str:
    fields = "\n".join(f"- [{f.section}] {f.name}: {f.question}" for f in state.fields)
    answers = "\n".join(f"- {a.field}: {a.answer}" for a in state.answers.values()) or "(nothing yet)"
    return INSTRUCTIONS.format(
        role=state.role, skills=", ".join(state.skills), fields=fields, answers=answers,
        section=state.current_section() or "finished", stage_instruction=stage_instruction(state, opening),
    )


def build_interview_graph(state: InterviewState, on_change: Callable[[InterviewState], None]):
    """Compile a per-session graph: model -> (tools -> model)* -> end.

    The model node streams its text through the LangGraph "custom" stream, so voice
    mode speaks only the interviewer's words, never tool calls or tool results.
    """
    tools = create_tools(state, on_change)
    model = build_chat_model().bind_tools(tools)

    async def call_model(graph_state: GraphState) -> dict:
        write = get_stream_writer()
        # The prompt is rebuilt every turn so it always shows the latest recorded answers.
        opening = not any(m.type == "human" for m in graph_state["messages"])
        # Some models reject a request with no user message, so the opening turn gets a stand-in.
        history = graph_state["messages"] or [HumanMessage("(The candidate has joined the interview.)")]
        messages = [SystemMessage(system_prompt(state, opening))] + history
        full: AIMessageChunk | None = None
        async for chunk in model.astream(messages):
            if chunk.text:
                write(chunk.text)
            full = chunk if full is None else full + chunk
        # A spoken reply (no tool calls) delivered any pending section transition.
        section = state.current_section()
        if not full.tool_calls and section in TRANSITIONS and section not in state.announced_sections:
            state.announced_sections.append(section)
            on_change(state)
        return {"messages": [full]}

    def route(graph_state: GraphState) -> str:
        return "tools" if graph_state["messages"][-1].tool_calls else END

    builder = StateGraph(GraphState)
    builder.add_node("model", call_model)
    builder.add_node("tools", ToolNode(tools))
    builder.add_edge(START, "model")
    builder.add_conditional_edges("model", route)
    builder.add_edge("tools", "model")
    return builder.compile()


def transcript_to_messages(transcript: list[TranscriptEntry]) -> list[BaseMessage]:
    return [HumanMessage(t.text) if t.role == "candidate" else AIMessage(t.text) for t in transcript]


async def generate_report(state: InterviewState, transcript: list[TranscriptEntry]) -> InterviewReport:
    """Turn the finalized transcript and recorded answers into a validated report."""
    if not transcript:
        raise ValueError("Cannot generate a report: the transcript is empty")
    lines = "\n".join(f"{t.role.upper()}: {t.text}" for t in transcript)
    answers = "\n".join(f"- {a.field}: {a.answer}" for a in state.answers.values()) or "(none)"
    fields = "\n".join(f"- {f.name}: {f.question}" for f in state.fields)
    prompt = (
        "Write a structured report of this screening interview for a human reviewer.\n"
        "Use only information stated by the candidate in the transcript; never invent facts.\n"
        "Refer to the candidate by name or as 'the candidate', using they/them pronouns.\n"
        "List template fields that were not answered (or answered too vaguely) under missing_information.\n"
        "Rubric scores (1-5) are optional; use the configured skills as categories and include a score only\n"
        "with a direct supporting quote as evidence.\n\n"
        f"Role: {state.role}\nSkills assessed: {', '.join(state.skills)}\n\n"
        f"Template fields:\n{fields}\n\nAnswers recorded during the interview:\n{answers}\n\n"
        f"Transcript:\n{lines}"
    )
    content = await build_chat_model().with_structured_output(ReportContent, method="json_schema", strict=True).ainvoke(prompt)
    return InterviewReport(session_id=state.session_id, transcript=transcript, **content.model_dump())
