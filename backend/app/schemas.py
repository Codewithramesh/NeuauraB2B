import re
from datetime import date, datetime
from typing import Literal
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Login(StrictModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=256)


class Bootstrap(Login):
    name: str = Field(min_length=1, max_length=120)
    industry: Literal["restaurant", "retail", "hospitality", "service"] = "restaurant"

    @field_validator("password")
    @classmethod
    def strong_password(cls, value):
        if len(value) < 12:
            raise ValueError("Use at least 12 characters")
        return value


class SessionCreate(StrictModel):
    title: str = Field(min_length=1, max_length=160)
    source_type: Literal["browser", "upload", "device"] = "browser"
    consent_attested: Literal[True]
    language: str = Field(default="en", pattern=r"^[a-z]{2}$")
    captured_at: datetime | None = None

    @field_validator("captured_at")
    @classmethod
    def aware_capture_time(cls, value):
        if value is not None and value.tzinfo is None:
            raise ValueError("Capture timestamps must include a UTC offset")
        return value


class CompleteUpload(StrictModel):
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    total_chunks: int = Field(ge=1, le=1000)


class DeviceRegister(StrictModel):
    name: str = Field(min_length=1, max_length=100)
    device_type: str = Field(default="wearable", min_length=1, max_length=50)
    model: str = Field(min_length=1, max_length=100)
    simulated: bool = False
    firmware: str | None = Field(default=None, max_length=80)


class Heartbeat(StrictModel):
    battery: float | None = Field(default=None, ge=0, le=100)
    firmware: str | None = Field(default=None, max_length=80)
    health: dict[str, str | int | float | bool] = Field(default_factory=dict, max_length=20)


class TaskUpdate(StrictModel):
    description: str | None = Field(default=None, min_length=1, max_length=2000)
    status: Literal["approved", "dismissed", "completed", "suggested"] | None = None
    priority: Literal["low", "medium", "high"] | None = None
    owner: str | None = Field(default=None, max_length=100)
    due_date: date | None = None


class ProfileUpdate(StrictModel):
    name: str = Field(min_length=1, max_length=120)
    industry: Literal["restaurant", "retail", "hospitality", "service"]
    categories: list[str] = Field(default_factory=list, max_length=30)

    @field_validator("categories")
    @classmethod
    def valid_categories(cls, values):
        if any(not re.fullmatch(r"[a-z][a-z0-9_]{1,59}", x) for x in values):
            raise ValueError("Categories must be lowercase snake_case")
        return list(dict.fromkeys(values))


class EvidenceInput(StrictModel):
    quote: str = Field(min_length=3, max_length=3000)
    segment_index: int | None = Field(default=None, ge=0)


class InsightInput(StrictModel):
    category: str = Field(min_length=2, max_length=80)
    topic: str = Field(min_length=2, max_length=120)
    title: str = Field(min_length=3, max_length=180)
    description: str = Field(min_length=3, max_length=2000)
    sentiment: Literal["positive", "negative", "neutral"]
    basis: Literal["stated", "inferred"]
    confidence: float = Field(ge=0, le=1)
    uncertainty: str = Field(max_length=1000)
    evidence: list[EvidenceInput] = Field(min_length=1, max_length=10)


class ActionInput(StrictModel):
    insight_index: int = Field(ge=0)
    description: str = Field(min_length=3, max_length=2000)
    priority: Literal["low", "medium", "high"]


class Extraction(StrictModel):
    summary: str = Field(min_length=3, max_length=3000)
    topics: list[str] = Field(max_length=30)
    entities: list[str] = Field(max_length=30)
    insights: list[InsightInput] = Field(max_length=50)
    actions: list[ActionInput] = Field(max_length=30)

    @model_validator(mode="after")
    def linked_actions(self):
        if any(a.insight_index >= len(self.insights) for a in self.actions):
            raise ValueError("Action references a missing insight")
        return self


class DeviceResponse(BaseModel):
    id: str
    org_id: str
    name: str
    device_type: str
    model: str
    firmware: str | None
    status: str
    simulated: bool
    last_seen: str | None
    battery: float | None
    health: dict
    created_at: str
    connection: str


class DeviceProvisioned(DeviceResponse):
    credential: str


class SessionResponse(BaseModel):
    id: str
    org_id: str
    conversation_id: str
    device_id: str | None
    idempotency_key: str
    request_hash: str
    status: str
    chunks: dict
    mime: str | None
    error: str | None
    created_at: str


class ChunkResponse(BaseModel):
    sequence: int
    sha256: str
    duplicate: bool


class CompletionResponse(BaseModel):
    conversation_id: str
    status: str
    duplicate: bool


class StatusJob(BaseModel):
    id: str
    conversation_id: str
    status: str
    stage: str
    attempts: int
    error_code: str | None
    error_message: str | None
    retryable: bool
    updated_at: str


class SessionStatusResponse(BaseModel):
    session_id: str
    conversation_id: str
    upload_status: str
    received_chunks: list[int]
    id: str
    org_id: str
    device_id: str | None
    title: str
    source_type: str
    language: str
    status: str
    duration: float | None
    summary: str | None
    topics: list[str]
    entities: list[str]
    created_at: str
    ingested_at: str | None
    captured_at: str | None
    job: StatusJob | None
