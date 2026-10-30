// Thin wrappers around the FastAPI endpoints. Types mirror backend/schemas.py.

export type TranscriptEntry = { role: "candidate" | "interviewer"; text: string; timestamp: string };
export type Report = {
  session_id: string;
  generated_at: string;
  requires_human_review: boolean;
  summary: string;
  questions_and_answers: { question: string; answer: string }[];
  key_strengths: string[];
  missing_information: string[];
  rubric_scores: { category: string; score: number; evidence: string }[];
  draft_final_answers: { field: string; answer: string }[];
  transcript: TranscriptEntry[];
};
export type Session =
  | { session_id: string; mode: "chat"; message: string }
  | { session_id: string; mode: "voice"; livekit_url: string; token: string };

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, { headers: { "Content-Type": "application/json" }, ...init });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail ?? `${res.status} ${res.statusText}`);
  }
  return res.json();
}

export type Config = { default_mode: "voice" | "chat"; voice_available: boolean; avatar: string };
export const getConfig = () => call<Config>("/api/config");
export type Mode = "voice" | "chat";
export type InterviewSetup = { role: string; skills: string[]; mode: Mode };
export const createSession = (setup: InterviewSetup) =>
  call<Session>("/api/sessions", { method: "POST", body: JSON.stringify(setup) });
export const sendMessage = (id: string, text: string) =>
  call<{ message: string }>(`/api/sessions/${id}/messages`, { method: "POST", body: JSON.stringify({ text }) });
export const finishSession = (id: string) => call<{ status: string }>(`/api/sessions/${id}/finish`, { method: "POST" });

// Voice reports are written by the worker after the room closes, so poll until ready (HTTP 200).
export async function waitForReport(id: string): Promise<Report> {
  for (;;) {
    const res = await fetch(`/api/sessions/${id}/report`);
    if (res.status === 200) return res.json();
    if (res.status !== 202) throw new Error((await res.json().catch(() => ({}))).detail ?? res.statusText);
    await new Promise((r) => setTimeout(r, 2000));
  }
}

export async function getTranscript(id: string) {
  const res = await fetch(`/api/sessions/${id}/transcript`);
  if (res.status === 202) throw new Error("The transcript will be available once the interview is finished.");
  if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail ?? res.statusText);
  return res.json() as Promise<{ role: string; created_at: string; transcript: TranscriptEntry[] }>;
}
