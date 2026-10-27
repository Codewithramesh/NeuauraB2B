import { useState } from "react";
import {
  X,
  Loader2,
  Sparkles,
  MessageSquareText,
  Lightbulb,
  ListTodo,
  ShieldCheck,
  Trash2,
} from "lucide-react";
import { useDialog } from "./useDialog";
import { useResource } from "./useResource";
import { Badge, ErrorNotice, InsightCard } from "./ui";
import { TaskRow } from "./Tasks";
import { api, human, dateLabel, durationLabel } from "./api";
import type { ConversationDetail } from "./types";

export function ConversationPanel({
  id,
  onClose,
  onDeleted,
}: {
  id: string;
  onClose: () => void;
  onDeleted: () => void;
}) {
  const dialogRef = useDialog();
  const { data, error, refresh } = useResource<ConversationDetail>(
    "/conversations/" + id,
    2500,
  );
  const [actionError, setActionError] = useState(""),
    [busy, setBusy] = useState(false);
  return (
    <div className="modal-backdrop detail-backdrop">
      <section
        ref={dialogRef}
        className="detail-panel"
        role="dialog"
        aria-modal="true"
        aria-labelledby="detail-title"
      >
        <div className="modal-heading">
          <div>
            <span className="eyebrow">SOURCE CONVERSATION</span>
            <h2 id="detail-title">{data?.title || "Loading conversation…"}</h2>
          </div>
          <button
            className="icon-button"
            aria-label="Close conversation"
            onClick={onClose}
          >
            <X size={21} />
          </button>
        </div>
        <ErrorNotice message={error || actionError} />
        {data && (
          <>
            <div className="detail-meta">
              <Badge status={data.status} />
              <span>{human(data.source_type)}</span>
              <span>{dateLabel(data.created_at)}</span>
              {data.duration && <span>{durationLabel(data.duration)}</span>}
            </div>
            {data.job && ["queued", "processing"].includes(data.status) && (
              <div className="processing-notice" role="status">
                <Loader2 size={20} className="spin" />
                <div>
                  <strong>
                    {data.status === "queued"
                      ? "In the processing queue"
                      : human(data.job.stage) + " audio"}
                  </strong>
                  <p>
                    This page updates automatically as your conversation is
                    processed.
                  </p>
                </div>
              </div>
            )}
            {data.job?.error_message && data.status === "failed" && (
              <div className="failed-job">
                <strong>
                  {human(data.job.error_code || "Processing failed")}
                </strong>
                <p>{data.job.error_message}</p>
                {data.job.retryable && data.job.attempts < 5 && (
                  <button
                    className="button small secondary"
                    disabled={busy}
                    onClick={async () => {
                      setBusy(true);
                      try {
                        await api(`/conversations/${id}/retry`, {
                          method: "POST",
                        });
                        await refresh();
                      } catch (e) {
                        setActionError((e as Error).message);
                      } finally {
                        setBusy(false);
                      }
                    }}
                  >
                    Retry processing · attempt {data.job.attempts + 1}/5
                  </button>
                )}
              </div>
            )}
            {data.summary && (
              <section className="detail-section">
                <h3>
                  <Sparkles size={17} /> Conversation summary
                </h3>
                <p>{data.summary}</p>
                <div className="inline-tags">
                  {data.topics.map((t) => (
                    <span className="subtle-tag" key={t}>
                      {t}
                    </span>
                  ))}
                </div>
              </section>
            )}
            <section className="detail-section">
              <h3>
                <MessageSquareText size={17} /> Transcript
              </h3>
              {data.transcript ? (
                <>
                  <div className="transcript">
                    {data.transcript.segments.length ? (
                      data.transcript.segments.map((s, i) => (
                        <div key={i}>
                          <span>{durationLabel(s.start)}</span>
                          <p>{s.text}</p>
                        </div>
                      ))
                    ) : (
                      <p>{data.transcript.text}</p>
                    )}
                  </div>
                  <p className="field-help">
                    Transcribed locally with {data.transcript.provider} ·{" "}
                    {data.transcript.model}. Speech recognition may contain
                    errors.
                  </p>
                </>
              ) : (
                <p className="muted">
                  A transcript will appear after successful speech recognition.
                </p>
              )}
              {data.audio_retained && (
                <audio controls src={`/api/v1/conversations/${id}/audio`} />
              )}
            </section>
            <section className="detail-section">
              <h3>
                <Lightbulb size={17} /> Evidence-linked insights
              </h3>
              {data.insights.length ? (
                data.insights.map((i) => (
                  <InsightCard key={i.id} insight={i} onOpen={() => {}} />
                ))
              ) : (
                <p className="muted">No validated insights yet.</p>
              )}
            </section>
            {data.tasks.length > 0 && (
              <section className="detail-section">
                <h3>
                  <ListTodo size={17} /> Suggested follow-ups
                </h3>
                {data.tasks.map((t) => (
                  <TaskRow
                    key={t.id}
                    task={t}
                    onRefresh={refresh}
                    onOpen={() => {}}
                  />
                ))}
              </section>
            )}
            <div className="detail-footer">
              <span>
                <ShieldCheck size={14} />
                {data.consent?.attested
                  ? "Consent attestation recorded"
                  : "No consent record"}
              </span>
              <button
                className="text-button danger"
                disabled={busy}
                onClick={async () => {
                  if (
                    !confirm(
                      "Delete this conversation, audio, transcript, insights, and linked tasks? This cannot be undone.",
                    )
                  )
                    return;
                  setBusy(true);
                  try {
                    await api("/conversations/" + id, { method: "DELETE" });
                    onDeleted();
                  } catch (e) {
                    setActionError((e as Error).message);
                  } finally {
                    setBusy(false);
                  }
                }}
              >
                <Trash2 size={14} /> Delete conversation
              </button>
            </div>
          </>
        )}
      </section>
    </div>
  );
}
