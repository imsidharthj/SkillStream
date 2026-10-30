import { useEffect, useRef, useState } from "react";

// The candidate's own camera, shown locally only. It is never uploaded or recorded.
export default function CameraPreview() {
  const video = useRef<HTMLVideoElement>(null);
  const [error, setError] = useState<string>();

  useEffect(() => {
    let stream: MediaStream | undefined;
    navigator.mediaDevices
      .getUserMedia({ video: true, audio: false })
      .then((s) => {
        stream = s;
        if (video.current) video.current.srcObject = s;
      })
      .catch((e) => setError(`Camera unavailable (${e.name}). The interview works without it.`));
    return () => stream?.getTracks().forEach((t) => t.stop());
  }, []);

  return (
    <div className="tile camera">
      {error ? <p className="muted">{error}</p> : <video ref={video} autoPlay muted playsInline />}
      <span className="tile-label">You</span>
    </div>
  );
}
