import { useEffect, useState } from "react";
import { getTranscript, type TranscriptEntry } from "./api";

// Candidate-facing page opened from the share link: /?transcript=<session_id>
export default function TranscriptPage({ sessionId }: { sessionId: string }) {
  const [data, setData] = useState<{ role: string; created_at: string; transcript: TranscriptEntry[] }>();
  const [error, setError] = useState<string>();

  useEffect(() => {
    getTranscript(sessionId).then(setData).catch((e) => setError(e.message));
  }, [sessionId]);

  if (error) return <p className="error">{error}</p>;
  if (!data) return <p>Loading transcript…</p>;
  return (
    <section className="panel">
      <h2>Your interview transcript</h2>
      <p className="muted">{data.role} · {new Date(data.created_at).toLocaleString()}</p>
      <div className="transcript tall">
        {data.transcript.map((t, i) => <p key={i} className={t.role}><b>{t.role}:</b> {t.text}</p>)}
      </div>
      <button onClick={() => window.print()}>Print / save as PDF</button>
    </section>
  );
}
