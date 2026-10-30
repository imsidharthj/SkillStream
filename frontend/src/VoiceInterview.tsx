import {
  BarVisualizer,
  LiveKitRoom,
  RoomAudioRenderer,
  VideoTrack,
  useConnectionState,
  useTranscriptions,
  useVoiceAssistant,
} from "@livekit/components-react";
import Avatar, { type AvatarState } from "./Avatar";
import InterviewLayout from "./InterviewLayout";

export default function VoiceInterview(props: {
  url: string;
  token: string;
  onFinish: () => void;
  onError: (message: string) => void;
}) {
  return (
    <LiveKitRoom serverUrl={props.url} token={props.token} connect audio video={false}
      onError={(e) => props.onError(`LiveKit: ${e.message}`)}>
      <RoomAudioRenderer />
      <Stage onFinish={props.onFinish} />
    </LiveKitRoom>
  );
}

function Stage({ onFinish }: { onFinish: () => void }) {
  const connection = useConnectionState();
  const { state, audioTrack, videoTrack, agent } = useVoiceAssistant();
  // Live text of both sides' speech; the saved transcript is built by the worker.
  const lines = useTranscriptions().map((l) => ({
    id: l.streamInfo.id,
    role: l.participantInfo.identity === agent?.identity ? ("interviewer" as const) : ("candidate" as const),
    text: l.text,
  }));
  const avatarState = toAvatarState(state);

  return (
    <InterviewLayout
      interviewer={
        videoTrack ? (
          <VideoTrack trackRef={videoTrack} />
        ) : (
          // Illustrated avatar (AVATAR_PROVIDER=static, or LiveAvatar video not published yet).
          <Avatar state={avatarState} />
        )
      }
      status={
        <>
          <span className={`pill ${avatarState}`}>
            {connection !== "connected" ? connection : !agent ? "Interviewer joining…" : state === "listening" ? "Listening to you" : state}
          </span>
          {audioTrack && <BarVisualizer state={state} trackRef={audioTrack} barCount={7} className="bars" />}
        </>
      }
      lines={lines}
      pending={agent && state === "thinking" ? "Interviewer is thinking…" : undefined}
      onFinish={onFinish}
    />
  );
}

function toAvatarState(state: string): AvatarState {
  if (state === "speaking" || state === "listening" || state === "thinking") return state;
  return "idle";
}
