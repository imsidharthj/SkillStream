import { useEffect, useState, type FormEvent } from "react";
import { sendMessage } from "./api";
import Avatar from "./Avatar";
import InterviewLayout, { type Line } from "./InterviewLayout";

export default function ChatInterview(props: { sessionId: string; greeting: string; onFinish: () => void }) {
  const [lines, setLines] = useState<Line[]>([{ id: "0", role: "interviewer", text: props.greeting }]);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string>();
  const [speaking, setSpeaking] = useState(false);

  // Animate the avatar "speaking" for roughly the time it takes to read the newest reply.
  const last = lines[lines.length - 1];
  useEffect(() => {
    if (last.role !== "interviewer") return;
    setSpeaking(true);
    const t = setTimeout(() => setSpeaking(false), Math.min(8000, 1000 + last.text.length * 45));
    return () => clearTimeout(t);
  }, [last]);

  async function submit(e: FormEvent) {
    e.preventDefault();
    const text = draft.trim();
    if (!text || busy) return;
    setDraft("");
    setBusy(true);
    setError(undefined);
    setLines((l) => [...l, { id: String(l.length), role: "candidate", text }]);
    try {
      const { message } = await sendMessage(props.sessionId, text);
      setLines((l) => [...l, { id: String(l.length), role: "interviewer", text: message }]);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setBusy(false);
    }
  }

  const state = busy ? "thinking" : speaking ? "speaking" : "listening";
  return (
    <InterviewLayout
      interviewer={<Avatar state={state} />}
      status={<span className={`pill ${state}`}>{state === "listening" ? "Waiting for your answer" : state}</span>}
      lines={lines}
      pending={busy ? "Interviewer is typing…" : undefined}
      onFinish={props.onFinish}
      finishDisabled={busy}
      composer={
        <form onSubmit={submit} className="composer">
          {error && <p className="error">{error}</p>}
          <div className="row">
            <input value={draft} onChange={(e) => setDraft(e.target.value)} placeholder="Type your answer" autoFocus />
            <button className="primary" disabled={busy || !draft.trim()}>Send</button>
          </div>
        </form>
      }
    />
  );
}
