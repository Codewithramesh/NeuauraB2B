import logging
import shutil
import threading
from datetime import datetime, timedelta, timezone
from sqlalchemy import delete, select
from .models import (AudioFile, AuditEvent, Conversation, Evidence, Insight, Organization, ProcessingJob,
                     Task, Transcript, UploadSession, now)
from .audio import normalize_audio
from .providers import ProcessingError, TranscriptionResult

logger = logging.getLogger(__name__)


class Pipeline:
    """One durable database-backed worker. API, source adapters and ML providers are independent."""
    def __init__(self, settings, factory, transcriber, extractor, locks):
        self.settings, self.factory = settings, factory
        self.transcriber, self.extractor = transcriber, extractor
        self.stop_event, self.wake = threading.Event(), threading.Event()
        self.thread, self.locks = None, locks

    def start(self):
        with self.factory() as db:
            for job in db.scalars(select(ProcessingJob).where(ProcessingJob.status == "processing")):
                job.status = "queued"
                conversation = db.get(Conversation, job.conversation_id)
                conversation.status = "queued"
            db.commit()
        self.thread = threading.Thread(target=self.run, name="neuaura-pipeline", daemon=True)
        self.thread.start()

    def stop(self):
        self.stop_event.set()
        self.wake.set()
        if self.thread:
            self.thread.join(timeout=5)

    def run(self):
        last_retention = 0
        import time
        while not self.stop_event.is_set():
            try:
                if time.monotonic() - last_retention > 3600:
                    self.retention()
                    last_retention = time.monotonic()
                with self.factory() as db:
                    job = db.scalar(select(ProcessingJob).where(ProcessingJob.status == "queued")
                                    .order_by(ProcessingJob.updated_at).limit(1))
                    cid = job.conversation_id if job else None
                if cid:
                    self.process(cid)
                else:
                    self.wake.wait(2)
                    self.wake.clear()
            except Exception:
                logger.exception("Worker loop failed; persisted work remains recoverable")
                self.wake.wait(2)
                self.wake.clear()

    def process(self, cid):
        with self.locks[cid], self.factory() as db:
            conversation = db.get(Conversation, cid)
            job = db.scalar(select(ProcessingJob).where(ProcessingJob.conversation_id == cid))
            if not conversation or not job or job.status != "queued":
                return
            job.status, conversation.status = "processing", "processing"
            job.attempts += 1
            job.error_code = job.error_message = None
            job.updated_at = now()
            db.commit()
            try:
                audio = db.scalar(select(AudioFile).where(AudioFile.conversation_id == cid))
                transcript = db.get(Transcript, cid)
                if transcript is None:
                    job.stage = "normalize"
                    db.commit()
                    folder = self.settings.data_dir / "uploads" / cid
                    normalized = folder / "normalized.wav"
                    duration = normalize_audio(folder / "original", normalized, self.settings.max_duration_seconds)
                    audio.normalized_path = str(normalized)
                    audio.codec = "pcm_s16le"
                    conversation.duration = duration
                    job.stage = "transcribe"
                    db.commit()
                    result = self.transcriber.transcribe(normalized, conversation.language)
                    transcript = Transcript(conversation_id=cid, text=result.text, segments=result.segments,
                        provider=result.provider, model=result.model, language=result.language)
                    db.add(transcript)
                    if not self.settings.retain_audio:
                        (folder / "original").unlink(missing_ok=True)
                        normalized.unlink(missing_ok=True)
                        audio.original_path = audio.normalized_path = None
                    db.commit()
                else:
                    result = TranscriptionResult(transcript.text, transcript.segments, transcript.language,
                                                 transcript.provider, transcript.model)
                job.stage = "extract"
                db.commit()
                org = db.get(Organization, conversation.org_id)
                extraction = self.extractor.extract(result, org.industry, org.categories)
                # Validate even injected/custom providers at the trust boundary.
                from .providers import validate_evidence
                from .schemas import Extraction
                extraction = validate_evidence(Extraction.model_validate(extraction), result, org.categories)
                conversation.summary, conversation.topics, conversation.entities = extraction.summary, extraction.topics, extraction.entities
                insights = []
                for item in extraction.insights:
                    insight = Insight(conversation_id=cid, **item.model_dump(exclude={"evidence"}))
                    db.add(insight)
                    db.flush()
                    insights.append(insight)
                    for evidence in item.evidence:
                        segment = result.segments[evidence.segment_index] if evidence.segment_index is not None else {}
                        db.add(Evidence(insight_id=insight.id, quote=evidence.quote,
                                        start=segment.get("start"), end=segment.get("end")))
                for action in extraction.actions:
                    db.add(Task(org_id=conversation.org_id, conversation_id=cid,
                                insight_id=insights[action.insight_index].id,
                                description=action.description, priority=action.priority))
                job.status, job.stage, conversation.status = "succeeded", "complete", "complete"
                job.retryable, job.updated_at = False, now()
                db.add(AuditEvent(org_id=conversation.org_id, actor="pipeline", action="processing.succeeded", target_id=cid))
                db.commit()
            except Exception as exc:
                db.rollback()
                job = db.scalar(select(ProcessingJob).where(ProcessingJob.conversation_id == cid))
                conversation = db.get(Conversation, cid)
                if not job or not conversation:
                    return
                error = exc if isinstance(exc, ProcessingError) else ProcessingError("PROCESSING_FAILED", "Processing failed. Check local service logs, then retry.")
                if not isinstance(exc, ProcessingError):
                    logger.exception("Processing job failed: %s", cid)
                job.status, conversation.status = "failed", "failed"
                job.error_code, job.error_message, job.retryable = error.code, str(error), error.retryable
                job.updated_at = now()
                db.commit()

    def delete_conversation(self, db, conversation, actor):
        cid = conversation.id
        with self.locks[cid]:
            db.add(AuditEvent(org_id=conversation.org_id, actor=actor, action="conversation.deleted", target_id=cid))
            db.execute(delete(Conversation).where(Conversation.id == cid))
            db.commit()
            shutil.rmtree(self.settings.data_dir / "uploads" / cid, ignore_errors=True)

    def retention(self):
        now_utc = datetime.now(timezone.utc)
        cutoff = (now_utc - timedelta(days=self.settings.retention_days)).isoformat()
        abandoned = (now_utc - timedelta(hours=24)).isoformat()
        with self.factory() as db:
            conversations = list(db.scalars(select(Conversation).where(
                (Conversation.created_at < cutoff) |
                ((Conversation.status == "awaiting_audio") & (Conversation.created_at < abandoned)))))
            for conversation in conversations:
                self.delete_conversation(db, conversation, "retention")
