from datetime import datetime, timezone
from uuid import uuid4
from sqlalchemy import JSON, Boolean, Column, Float, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import declarative_base

Base = declarative_base()


def uid():
    return str(uuid4())


def now():
    return datetime.now(timezone.utc).isoformat()


class Organization(Base):
    __tablename__ = "organizations"
    id = Column(String, primary_key=True, default=uid)
    name = Column(String(120), nullable=False)
    industry = Column(String(30), nullable=False, default="restaurant")
    categories = Column(JSON, nullable=False, default=list)
    created_at = Column(String, default=now, nullable=False)


class User(Base):
    __tablename__ = "users"
    id = Column(String, primary_key=True, default=uid)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    email = Column(String(254), unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    role = Column(String, nullable=False, default="admin")


class AuthSession(Base):
    __tablename__ = "auth_sessions"
    token_hash = Column(String, primary_key=True)
    user_id = Column(String, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    csrf = Column(String, nullable=False)
    expires_at = Column(String, nullable=False)


class Device(Base):
    __tablename__ = "devices"
    id = Column(String, primary_key=True, default=uid)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    device_type = Column(String, nullable=False)
    model = Column(String(100), nullable=False)
    firmware = Column(String(80))
    credential_hash = Column(String, nullable=False, unique=True)
    status = Column(String, default="authorized", nullable=False)
    simulated = Column(Boolean, default=False, nullable=False)
    last_seen = Column(String)
    battery = Column(Float)
    health = Column(JSON, default=dict, nullable=False)
    created_at = Column(String, default=now, nullable=False)


class Conversation(Base):
    __tablename__ = "conversations"
    id = Column(String, primary_key=True, default=uid)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    device_id = Column(String, ForeignKey("devices.id", ondelete="SET NULL"))
    title = Column(String(160), nullable=False)
    source_type = Column(String, nullable=False)
    language = Column(String, default="en", nullable=False)
    status = Column(String, default="awaiting_audio", nullable=False, index=True)
    duration = Column(Float)
    summary = Column(Text)
    topics = Column(JSON, default=list, nullable=False)
    entities = Column(JSON, default=list, nullable=False)
    created_at = Column(String, default=now, nullable=False, index=True)
    ingested_at = Column(String)
    captured_at = Column(String)


class UploadSession(Base):
    __tablename__ = "upload_sessions"
    __table_args__ = (UniqueConstraint("org_id", "idempotency_key"),)
    id = Column(String, primary_key=True, default=uid)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), unique=True, nullable=False)
    device_id = Column(String, ForeignKey("devices.id", ondelete="SET NULL"))
    idempotency_key = Column(String(128), nullable=False)
    request_hash = Column(String, nullable=False)
    status = Column(String, default="open", nullable=False)
    chunks = Column(JSON, default=dict, nullable=False)
    mime = Column(String(100))
    error = Column(String(500))
    created_at = Column(String, default=now, nullable=False)


class AudioFile(Base):
    __tablename__ = "audio_files"
    id = Column(String, primary_key=True, default=uid)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, unique=True)
    sha256 = Column(String(64), nullable=False)
    bytes = Column(Integer, nullable=False)
    mime = Column(String, nullable=False)
    original_path = Column(String)
    normalized_path = Column(String)
    codec = Column(String)
    sample_rate = Column(Integer, default=16000, nullable=False)
    created_at = Column(String, default=now, nullable=False)


class Transcript(Base):
    __tablename__ = "transcripts"
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True)
    text = Column(Text, nullable=False)
    segments = Column(JSON, default=list, nullable=False)
    provider = Column(String, nullable=False)
    model = Column(String, nullable=False)
    language = Column(String, nullable=False)
    created_at = Column(String, default=now, nullable=False)


class Insight(Base):
    __tablename__ = "insights"
    id = Column(String, primary_key=True, default=uid)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    category = Column(String(80), nullable=False)
    topic = Column(String(120), nullable=False)
    title = Column(String(180), nullable=False)
    description = Column(Text, nullable=False)
    sentiment = Column(String, nullable=False)
    basis = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    uncertainty = Column(Text, nullable=False)
    created_at = Column(String, default=now, nullable=False)


class Evidence(Base):
    __tablename__ = "evidence"
    id = Column(String, primary_key=True, default=uid)
    insight_id = Column(String, ForeignKey("insights.id", ondelete="CASCADE"), nullable=False, index=True)
    quote = Column(Text, nullable=False)
    start = Column(Float)
    end = Column(Float)


class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True, default=uid)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    insight_id = Column(String, ForeignKey("insights.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=False)
    priority = Column(String, nullable=False, default="medium")
    owner = Column(String(100))
    due_date = Column(String)
    status = Column(String, nullable=False, default="suggested")
    created_at = Column(String, default=now, nullable=False)


class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    id = Column(String, primary_key=True, default=uid)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), unique=True, nullable=False)
    status = Column(String, default="queued", nullable=False, index=True)
    stage = Column(String, default="normalize", nullable=False)
    attempts = Column(Integer, default=0, nullable=False)
    error_code = Column(String)
    error_message = Column(Text)
    retryable = Column(Boolean, default=False, nullable=False)
    updated_at = Column(String, default=now, nullable=False)


class Consent(Base):
    __tablename__ = "consents"
    id = Column(String, primary_key=True, default=uid)
    conversation_id = Column(String, ForeignKey("conversations.id", ondelete="CASCADE"), unique=True, nullable=False)
    attested = Column(Boolean, nullable=False)
    actor = Column(String, nullable=False)
    notice_version = Column(String, default="2026-10-27", nullable=False)
    created_at = Column(String, default=now, nullable=False)


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id = Column(String, primary_key=True, default=uid)
    org_id = Column(String, ForeignKey("organizations.id", ondelete="CASCADE"), nullable=False, index=True)
    actor = Column(String, nullable=False)
    action = Column(String, nullable=False)
    target_id = Column(String, nullable=False)
    created_at = Column(String, default=now, nullable=False)
