// Illustrated interviewer used when no LiveAvatar video track is available
// (AVATAR_PROVIDER=static, or chat mode). It reacts to the interviewer's state:
// the mouth moves while speaking, the eyes look up while thinking, and it blinks.

export type AvatarState = "speaking" | "listening" | "thinking" | "idle";

export default function Avatar({ state }: { state: AvatarState }) {
  return (
    <div className={`avatar-figure ${state}`}>
      <svg viewBox="0 0 200 220" role="img" aria-label={`Interviewer is ${state}`}>
        <defs>
          <clipPath id="frame"><circle cx="100" cy="110" r="100" /></clipPath>
        </defs>
        <g clipPath="url(#frame)">
          <circle cx="100" cy="110" r="100" className="bg" />
          {/* shoulders and shirt */}
          <path d="M20 230 Q30 165 100 160 Q170 165 180 230 Z" className="jacket" />
          <path d="M80 162 L100 195 L120 162 Z" className="shirt" />
          <rect x="88" y="140" width="24" height="26" rx="8" className="skin" />
          <g className="head">
            {/* hair, face, ears */}
            <ellipse cx="100" cy="88" rx="46" ry="52" className="hair" />
            <ellipse cx="55" cy="98" rx="8" ry="12" className="skin" />
            <ellipse cx="145" cy="98" rx="8" ry="12" className="skin" />
            <ellipse cx="100" cy="100" rx="42" ry="48" className="skin" />
            <path d="M58 82 Q70 46 100 50 Q132 46 142 82 Q120 64 100 66 Q76 64 58 82 Z" className="hair" />
            {/* eyes */}
            <g className="eyes">
              <ellipse cx="83" cy="96" rx="5" ry="6" className="eye" />
              <ellipse cx="117" cy="96" rx="5" ry="6" className="eye" />
            </g>
            <path d="M74 84 Q83 79 92 84" className="brow" />
            <path d="M108 84 Q117 79 126 84" className="brow" />
            <path d="M100 100 Q96 112 101 114" className="nose" />
            <ellipse cx="100" cy="128" rx="11" ry="3" className="mouth" />
          </g>
        </g>
      </svg>
      <span className="avatar-label">
        {state === "speaking" ? "Speaking" : state === "thinking" ? "Thinking…" : state === "listening" ? "Listening" : "Ready"}
      </span>
    </div>
  );
}
