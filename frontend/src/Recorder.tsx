import { useState, useRef, useEffect, useCallback } from "react";
import {
  X,
  Loader2,
  ShieldCheck,
  Pause,
  Mic,
  Play,
  Square,
  Upload,
  FileAudio,
  Sparkles,
} from "lucide-react";
import { useDialog } from "./useDialog";
import { ErrorNotice } from "./ui";
import { durationLabel } from "./api";
import {
  BrowserMicrophoneAdapter,
  UploadedAudioAdapter,
  uploadAudio,
} from "./audio";
import type { AudioSubmission } from "./audio";
import type { Settings } from "./types";

export function Recorder({
  settings,
  onClose,
  onComplete,
}: {
  settings: Settings | null;
  onClose: () => void;
  onComplete: (id: string) => void;
}) {
  const dialogRef = useDialog();
  const adapter = useRef(new BrowserMicrophoneAdapter());
  const [state, setState] = useState<
      "idle" | "recording" | "paused" | "preview" | "uploading"
    >("idle"),
    [input, setInput] = useState<AudioSubmission | null>(null),
    [consent, setConsent] = useState(false),
    [seconds, setSeconds] = useState(0),
    [error, setError] = useState(""),
    [progress, setProgress] = useState(0),
    [url, setURL] = useState(""),
    [devices, setDevices] = useState<MediaDeviceInfo[]>([]),
    [deviceId, setDeviceId] = useState(""),
    [mode, setMode] = useState<"record" | "upload">("record"),
    [title, setTitle] = useState(""),
    [starting, setStarting] = useState(false),
    [uploadStarted, setUploadStarted] = useState(false);
  const key = useRef(crypto.randomUUID());
  const inputRef = useRef<HTMLInputElement>(null);
  const limit = settings?.max_duration_seconds || 600;
  useEffect(() => () => adapter.current.cancel(), []);
  useEffect(() => {
    if (!input) return;
    const objectURL = URL.createObjectURL(input.blob);
    setURL(objectURL);
    return () => URL.revokeObjectURL(objectURL);
  }, [input]);
  const stop = useCallback(async () => {
    try {
      setInput(await adapter.current.stop());
      setState("preview");
    } catch (e) {
      setError((e as Error).message);
      setState("idle");
    }
  }, []);
  useEffect(() => {
    if (state !== "recording") return;
    const interval = setInterval(() => setSeconds((x) => x + 1), 1000);
    return () => clearInterval(interval);
  }, [state]);
  useEffect(() => {
    if (seconds >= limit && state === "recording") void stop();
  }, [seconds, state, limit, stop]);
  useEffect(() => {
    const before = (e: BeforeUnloadEvent) => {
      if (["recording", "paused", "uploading"].includes(state)) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", before);
    return () => window.removeEventListener("beforeunload", before);
  }, [state]);
  async function start() {
    setError("");
    setStarting(true);
    try {
      await adapter.current.start(deviceId || undefined);
      adapter.current.onError((message) => {
        setError(message);
        adapter.current.cancel();
        setState("idle");
      });
      setSeconds(0);
      setState("recording");
      const list = await navigator.mediaDevices.enumerateDevices();
      setDevices(list.filter((d) => d.kind === "audioinput"));
    } catch (e) {
      const name = (e as DOMException).name;
      setError(
        name === "NotAllowedError"
          ? "Microphone access was denied. Allow microphone access in browser settings, then try again."
          : (e as Error).message,
      );
    } finally {
      setStarting(false);
    }
  }
  const active = ["recording", "paused"].includes(state);
  return (
    <div className="modal-backdrop">
      <section
        ref={dialogRef}
        className="modal recorder-modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="record-title"
      >
        <div className="modal-heading">
          <div>
            <span className="eyebrow">CAPTURE WITH CONFIDENCE</span>
            <h2 id="record-title">New conversation</h2>
          </div>
          <button
            className="icon-button"
            aria-label="Close recorder"
            disabled={state === "uploading" || starting}
            onClick={() => {
              if (active && !confirm("Discard this recording?")) return;
              onClose();
            }}
          >
            <X size={20} />
          </button>
        </div>
        <div className="tabs">
          <button
            disabled={active || state === "uploading"}
            className={mode === "record" ? "selected" : ""}
            onClick={() => {
              setMode("record");
              setInput(null);
              setState("idle");
              key.current = crypto.randomUUID();
            }}
          >
            Record audio
          </button>
          <button
            disabled={active || state === "uploading"}
            className={mode === "upload" ? "selected" : ""}
            onClick={() => {
              setMode("upload");
              setInput(null);
              setState("idle");
              key.current = crypto.randomUUID();
            }}
          >
            Upload a file
          </button>
        </div>
        <label>
          Conversation title
          <input
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={160}
            placeholder="e.g. Lunch service feedback"
            disabled={state === "uploading" || uploadStarted}
          />
        </label>
        <label className="consent-box">
          <input
            type="checkbox"
            checked={consent}
            disabled={active || state === "uploading" || starting}
            onChange={(e) => setConsent(e.target.checked)}
          />
          <span>
            <strong>
              I have the required permission to record and process this
              conversation.
            </strong>
            <small>
              All participants must be appropriately informed. Starting a
              recording does not establish everyone’s consent.
            </small>
          </span>
        </label>
        {mode === "record" ? (
          <>
            <div className={`record-surface ${active ? "is-recording" : ""}`}>
              <div className="record-status">
                {state === "recording" ? (
                  <>
                    <i className="record-dot" /> RECORDING
                  </>
                ) : state === "paused" ? (
                  <>
                    <Pause size={12} /> PAUSED
                  </>
                ) : (
                  <>
                    <ShieldCheck size={12} /> YOU’RE IN CONTROL
                  </>
                )}
              </div>
              <div className="record-wave">
                {Array.from({ length: 31 }, (_, i) => (
                  <span
                    key={i}
                    style={{
                      height: active
                        ? `${12 + ((i * 13 + i * i) % 39)}px`
                        : "5px",
                      animationDelay: `${i * 0.07}s`,
                    }}
                  />
                ))}
              </div>
              <strong className="record-time">{durationLabel(seconds)}</strong>
              <span className="record-format">
                {input
                  ? input.mime
                  : `Up to ${limit / 60} minutes · Microphone stays off until you start`}
              </span>
              <div className="record-controls">
                {!active && state === "idle" && (
                  <button
                    className="button primary"
                    disabled={!consent || starting}
                    onClick={() => void start()}
                  >
                    {starting ? (
                      <Loader2 className="spin" size={17} />
                    ) : (
                      <Mic size={17} />
                    )}{" "}
                    Start recording
                  </button>
                )}
                {active && (
                  <>
                    <button
                      className="button secondary"
                      onClick={() => {
                        if (state === "recording") {
                          adapter.current.pause();
                          setState("paused");
                        } else {
                          adapter.current.resume();
                          setState("recording");
                        }
                      }}
                    >
                      {state === "recording" ? (
                        <>
                          <Pause size={16} /> Pause
                        </>
                      ) : (
                        <>
                          <Play size={16} /> Resume
                        </>
                      )}
                    </button>
                    <button className="button dark" onClick={() => void stop()}>
                      <Square size={14} /> Stop recording
                    </button>
                  </>
                )}
              </div>
            </div>
            {state === "idle" && (
              <label>
                Microphone
                <select
                  value={deviceId}
                  onChange={(e) => setDeviceId(e.target.value)}
                >
                  <option value="">System default</option>
                  {devices.map((d) => (
                    <option key={d.deviceId} value={d.deviceId}>
                      {d.label || "Microphone"}
                    </option>
                  ))}
                </select>
              </label>
            )}
          </>
        ) : (
          <div className="upload-zone">
            <Upload size={29} />
            <h3>Bring a conversation with you</h3>
            <p>
              WAV, WebM, MP3, MP4/M4A, Ogg or FLAC
              <br />
              Up to {settings?.max_upload_mb || 50} MB
            </p>
            <input
              ref={inputRef}
              aria-label="Choose audio file"
              type="file"
              accept="audio/*,.webm,.m4a,.mp4,.wav,.mp3,.ogg,.flac"
              disabled={!consent || state === "uploading"}
              onChange={(e) => {
                const file = e.target.files?.[0];
                if (!file) return;
                setError("");
                if (file.size > (settings?.max_upload_mb || 50) * 1024 * 1024) {
                  setError("This file exceeds the upload limit.");
                  return;
                }
                if (!file.size) {
                  setError("The selected file is empty.");
                  return;
                }
                setInput(new UploadedAudioAdapter(file).submission());
                setState("preview");
                key.current = crypto.randomUUID();
                if (!title) setTitle(file.name.replace(/\.[^.]+$/, ""));
              }}
            />
          </div>
        )}
        {input && (
          <div className="audio-preview">
            <div>
              <FileAudio size={17} />
              <strong>Review your audio</strong>
              <span>{(input.blob.size / 1024 / 1024).toFixed(2)} MB</span>
            </div>
            <audio controls src={url} preload="metadata" />
          </div>
        )}
        <ErrorNotice message={error} />
        {state === "uploading" && (
          <div className="upload-progress" role="status">
            <span>Uploading securely… {progress}%</span>
            <progress value={progress} max={100} />
          </div>
        )}
        <div className="modal-footer">
          <button
            className="text-button muted"
            disabled={state === "uploading" || starting}
            onClick={() => {
              adapter.current.cancel();
              setState("idle");
              setInput(null);
              setSeconds(0);
              setError("");
              setUploadStarted(false);
              key.current = crypto.randomUUID();
            }}
          >
            Discard
          </button>
          <button
            className="button primary"
            disabled={!input || !consent || state === "uploading"}
            onClick={async () => {
              if (!input) return;
              setUploadStarted(true);
              setState("uploading");
              setError("");
              try {
                const id = await uploadAudio(
                  input,
                  title.trim() || "Untitled conversation",
                  settings?.language || "en",
                  key.current,
                  setProgress,
                );
                onComplete(id);
              } catch (e) {
                setError((e as Error).message);
                setState("preview");
              }
            }}
          >
            {state === "uploading" ? (
              <Loader2 className="spin" size={16} />
            ) : (
              <Sparkles size={16} />
            )}{" "}
            Analyze conversation
          </button>
        </div>
        <p className="record-privacy">
          <ShieldCheck size={13} />
          {settings?.retain_audio
            ? "Audio retained under your workspace policy."
            : "Audio removed after transcription. Pending audio is retained for retries."}
        </p>
      </section>
    </div>
  );
}
