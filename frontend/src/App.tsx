import { useEffect, useState } from "react";
import { createSession, finishSession, getConfig, waitForReport, type Config, type InterviewSetup, type Report, type Session } from "./api";
import ChatInterview from "./ChatInterview";
import VoiceInterview from "./VoiceInterview";
import ReportView from "./ReportView";
import Home from "./Home";
import TranscriptPage from "./TranscriptPage";

const sharedTranscriptId = new URLSearchParams(window.location.search).get("transcript");

type Stage = "idle" | "interview" | "generating" | "report";

export default function App() {
  const [config, setConfig] = useState<Config>();
  const [stage, setStage] = useState<Stage>("idle");
  const [session, setSession] = useState<Session>();
  const [report, setReport] = useState<Report>();
  const [error, setError] = useState<string>();
  const [starting, setStarting] = useState(false);

  useEffect(() => {
    getConfig().then(setConfig).catch((e) => setError(`Backend unreachable: ${e.message}`));
  }, []);

  async function start(setup: InterviewSetup) {
    setError(undefined);
    setStarting(true);
    try {
      setSession(await createSession(setup));
      setStage("interview");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setStarting(false);
    }
  }

  async function finish() {
    if (!session) return;
    setStage("generating");
    try {
      await finishSession(session.session_id);
      setReport(await waitForReport(session.session_id));
      setStage("report");
    } catch (e) {
      setError((e as Error).message);
      setStage("idle");
    }
  }

  if (sharedTranscriptId) {
    return <main><header><span className="logo">SkillStream</span></header><TranscriptPage sessionId={sharedTranscriptId} /></main>;
  }

  return (
    <main className={stage === "interview" ? "wide" : ""}>
      <header>
        <span className="logo">SkillStream</span>
        {session && stage === "interview" && <span className="badge">{session.mode} interview</span>}
      </header>
      {error && <p className="error">{error}</p>}
      {stage === "idle" && config && (
        <Home voiceAvailable={config.voice_available} defaultMode={config.default_mode} busy={starting} onStart={start} />
      )}
      {stage === "interview" && session?.mode === "chat" && (
        <ChatInterview sessionId={session.session_id} greeting={session.message} onFinish={finish} />
      )}
      {stage === "interview" && session?.mode === "voice" && (
        <VoiceInterview url={session.livekit_url} token={session.token} onFinish={finish}
          onError={(m) => setError(m)} />
      )}
      {stage === "generating" && <p>Finishing the interview and generating the report…</p>}
      {stage === "report" && report && <ReportView report={report} />}
    </main>
  );
}
