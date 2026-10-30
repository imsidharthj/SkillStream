import { useEffect, useRef, type ReactNode } from "react";
import CameraPreview from "./CameraPreview";

export type Line = { id: string; role: "candidate" | "interviewer"; text: string };

// Split screen: interviewer + candidate camera on the left, the conversation on the right.
export default function InterviewLayout(props: {
  interviewer: ReactNode;
  status: ReactNode;
  lines: Line[];
  pending?: string;
  composer?: ReactNode;
  onFinish: () => void;
  finishDisabled?: boolean;
}) {
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => end.current?.scrollIntoView({ behavior: "smooth", block: "end" }), [props.lines, props.pending]);

  return (
    <div className="split">
      <div className="stage">
        <div className="tile interviewer-tile">
          {props.interviewer}
          <span className="tile-label">SkillStream interviewer</span>
          <div className="tile-status">{props.status}</div>
        </div>
        <CameraPreview />
      </div>
      <div className="conversation">
        <div className="conversation-head">
          <b>Conversation</b>
          <button className="finish" onClick={props.onFinish} disabled={props.finishDisabled}>Finish Interview</button>
        </div>
        <div className="messages">
          {props.lines.map((l) => (
            <div key={l.id} className={`bubble ${l.role}`}>
              <span className="who">{l.role === "interviewer" ? "Interviewer" : "You"}</span>
              {l.text}
            </div>
          ))}
          {props.pending && <div className="bubble interviewer muted">{props.pending}</div>}
          <div ref={end} />
        </div>
        {props.composer}
      </div>
    </div>
  );
}
