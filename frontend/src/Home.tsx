import { useState, type FormEvent } from "react";
import type { InterviewSetup, Mode } from "./api";

const SUGGESTED = ["DSA", "System design", "Python", "JavaScript", "SQL", "Communication"];

// Landing page: introduces SkillStream and lets the hiring team configure the interview.
export default function Home(props: {
  voiceAvailable: boolean;
  defaultMode: Mode;
  busy: boolean;
  onStart: (setup: InterviewSetup) => void;
}) {
  const [mode, setMode] = useState<Mode>(props.voiceAvailable ? props.defaultMode : "chat");
  const [role, setRole] = useState("");
  const [skills, setSkills] = useState<string[]>([]);
  const [draft, setDraft] = useState("");

  function add(skill: string) {
    const s = skill.trim();
    if (s && !skills.some((x) => x.toLowerCase() === s.toLowerCase()) && skills.length < 8) setSkills([...skills, s]);
  }
  function submitSkill(e: FormEvent) {
    e.preventDefault();
    add(draft);
    setDraft("");
  }

  const ready = role.trim() !== "" && skills.length > 0;

  return (
    <div className="home">
      <section className="hero">
        <p className="eyebrow">SkillStream</p>
        <h1>An agentic AI interviewer</h1>
        <p className="lead">
          Tell SkillStream what to assess. It runs a structured interview by voice or chat, adapts its follow-up
          questions to each answer, and writes an evidence-based report for your team to review.
        </p>
        <div className="features">
          <div><b>Structured</b><span>Introduction, background, technical round, wrap-up.</span></div>
          <div><b>Adaptive</b><span>Goes deeper on strong answers and never re-asks what it already knows.</span></div>
          <div><b>Reviewable</b><span>Full transcript, a summary and scores backed by quotes. A person makes the decision.</span></div>
        </div>
      </section>

      <section className="setup-card">
        <h2>Configure the interview</h2>

        <fieldset className="modes">
          <legend>Interview mode</legend>
          <label className={`mode ${mode === "voice" ? "selected" : ""} ${props.voiceAvailable ? "" : "disabled"}`}>
            <input type="radio" name="mode" checked={mode === "voice"} disabled={!props.voiceAvailable}
              onChange={() => setMode("voice")} />
            <b>🎙 Voice</b>
            <span>{props.voiceAvailable ? "The candidate talks with the AI interviewer." : "Not available: LiveKit is not configured."}</span>
          </label>
          <label className={`mode ${mode === "chat" ? "selected" : ""}`}>
            <input type="radio" name="mode" checked={mode === "chat"} onChange={() => setMode("chat")} />
            <b>💬 Chat</b>
            <span>The candidate types their answers.</span>
          </label>
        </fieldset>

        <label className="field">
          Role
          <input value={role} onChange={(e) => setRole(e.target.value)} placeholder="e.g. Software Engineer" />
        </label>

        <div className="field">
          Skills, topics or competencies to assess (up to 8)
          <form className="row" onSubmit={submitSkill}>
            <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Type a skill and press Enter" />
            <button type="submit" disabled={!draft.trim() || skills.length >= 8}>Add</button>
          </form>
          <div className="chips">
            {skills.map((s) => (
              <span key={s} className="chip">
                {s} <button aria-label={`Remove ${s}`} onClick={() => setSkills(skills.filter((x) => x !== s))}>×</button>
              </span>
            ))}
          </div>
          <div className="suggestions">
            {SUGGESTED.filter((s) => !skills.includes(s)).map((s) => (
              <button key={s} className="suggestion" onClick={() => add(s)}>+ {s}</button>
            ))}
          </div>
        </div>

        <div className="agenda">
          <b>Interview agenda</b>
          <ol>
            <li>Introduction: the AI interviewer introduces itself and the agenda</li>
            <li>Background: name, role, education and experience</li>
            <li>Technical round: {skills.length ? skills.join(", ") : "your selected skills"}</li>
            <li>Wrap-up: availability and closing</li>
          </ol>
        </div>

        <button className="primary big" disabled={!ready || props.busy}
          onClick={() => props.onStart({ role: role.trim(), skills, mode })}>
          {props.busy ? "Starting…" : `Start ${mode} interview`}
        </button>
      </section>
    </div>
  );
}
