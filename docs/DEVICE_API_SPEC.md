# Device API v1

Base: `https://YOUR_TRUSTED_HOST/api/v1`; loopback HTTP is allowed only for local development. This is a recorded-upload protocol, not streaming, Bluetooth pairing or a board-specific SDK. The live `/docs` and `shared/api-contracts/openapi.json` define request/response schemas.

## Authentication and provisioning

Workspace creation uses a one-time local setup token. An authenticated workspace admin provisions a device through `POST /devices/register` with cookie session + `X-CSRF-Token`. Request: `{"name":"Store wearable","device_type":"wearable","model":"prototype-v1","simulated":false,"firmware":"0.1"}`. Response 201 includes `id`, `org_id`, registry metadata and **one-time** `credential`. Only its SHA256 is persisted. Subsequent registry reads never return credentials.

The device sends `Authorization: Bearer <per-device credential>` on every device/session request. No master backend secret exists in firmware. The credential itself authenticates; no secondary token exchange is required. Admin register/list/revoke and business-intelligence routes cannot be called using device credentials. Device credentials are scoped to the device's organization AND its own sessions.

| Method | Path | Authentication | Behavior |
|---|---|---|---|
| POST | `/devices/register` | Admin cookie + CSRF | Provision, return credential once |
| GET | `/devices` | Admin cookie | Own organization's registry |
| GET | `/devices/{id}` | Admin or matching device | Registry and measured last-seen state |
| POST | `/devices/{id}/revoke` | Admin cookie + CSRF | Immediately reject subsequent credential use |
| POST | `/devices/{id}/sessions` | Matching device | Create session, associate conversation |
| POST | `/sessions` | Admin cookie + CSRF or device | Common browser/file/device boundary |
| POST | `/sessions/{id}/audio?sequence=N` | Session owner | Raw encoded bytes; supports single file or chunks |
| POST | `/sessions/{id}/complete` | Session owner | Validate order/integrity and enqueue |
| GET | `/sessions/{id}/status` | Session owner | Received chunks, conversation and job stage/error |
| DELETE | `/sessions/{id}` | Session owner | Cancel an open upload and remove its data |
| POST | `/devices/{id}/heartbeat` | Matching device | Optional measured or labeled simulated health |
| POST | `/devices/{id}/errors` | Matching device | Record bounded error code/message (no transcript) |

## Create a session

Header `Idempotency-Key`: 8–128 ASCII letters/digits/`_.:-`. Use a new UUID per recording. Persist it on the device until completion.

```json
{"title":"Authorized interaction","source_type":"device","consent_attested":true,"language":"en"}
```

An optional timezone-aware `captured_at` ISO timestamp can report when an offline recording was captured. It is stored separately from trusted server creation/ingestion clocks and is never used for retention.

Response 201 contains `id` (upload session ID), `conversation_id`, `org_id`, `device_id`, server `created_at`, `status:"open"` and `chunks:{}`. The organization comes from authentication, never the request body. Creating a session records a versioned consent attestation; it does not prove every participant has consented.

Same key + identical normalized payload + same actor returns the original session; a changed title/language/source/actor with the same key returns 409 `IDEMPOTENCY_CONFLICT`. A device must submit `source_type:"device"`; an admin cannot impersonate a device through browser routes.

## Upload bytes

For one file, POST the entire encoded file as sequence `0`. For resumable transfers, split **one encoded file into contiguous byte slices**; chunks are not separately encoded audio files and need not be independently decodable.

- `Content-Type`: `audio/wav`, `audio/webm`, `audio/mp4`, `audio/mpeg`, `audio/ogg`, `audio/flac`, `audio/aac`, supported aliases, or `application/octet-stream`.
- `X-Chunk-SHA256`: lowercase SHA256 of that exact chunk.
- `sequence`: integer 0–999. All chunks must share a content type.
- Default combined encoded limit: 50 MB. Client default: 4 MiB slices. Server validates decoded duration separately (default 600 seconds).
- Response: `{"sequence":0,"sha256":"...","duplicate":false}`.
- Out-of-order chunks are accepted. Repeating identical sequence+bytes returns `duplicate:true`; different bytes for an existing sequence return 409 `CHUNK_CONFLICT`.
- Interrupted clients GET status and resend missing chunks using the same session. Credentials must still be valid. Unfinished sessions expire after 24 hours under hourly retention cleanup.
- Retries: retry network errors and transient 5xx with bounded exponential backoff. A 429 response includes Retry-After. Do not retry authentication/validation failures without fixing the cause.

## Complete

```json
{"sha256":"LOWERCASE_SHA256_OF_ENTIRE_ORIGINAL_FILE","total_chunks":3}
```

All sequences `0..total_chunks-1` must exist; missing/unexpected sequences return 409 `MISSING_CHUNKS`. Server rechecks each stored chunk, concatenates in order, verifies whole SHA256 and atomically persists audio metadata + job. Response: `{"conversation_id":"...","status":"accepted","duplicate":false}`. This acknowledges ingestion, **not successful transcription/extraction**. Repeat completion with the same digest/count is idempotent. Different completion metadata returns 409.

Duplicate audio across **different** session keys is treated as distinct conversations; only retries of the same session are deduplicated.

## Status, heartbeat and error reporting

Status includes `upload_status`, `received_chunks`, `status` (`awaiting_audio`, `queued`, `processing`, `complete`, `failed`), `job.stage`, `job.attempts`, `job.retryable`, `job.error_code`, `job.error_message`. Devices do not receive the transcript/insights via status; a workspace user inspects them in the dashboard. Current status includes a summary after successful extraction.

Heartbeat: `{"firmware":"0.1","battery":82,"health":{"wifi_rssi":-64}}`. Omit battery when unmeasured. A simulated device always returns `simulated:true`. `recently_seen` means authenticated activity in the last 120 seconds; it is not proof of a persistent connection.

Error report: `{"code":"MIC_FAILURE","message":"I2S input unavailable"}`; each value ≤500 characters. Never send private conversation content in telemetry/errors.

Errors use `{"detail":{"code":"...","message":"..."}}`, while Pydantic validation failures use the standard FastAPI `detail` array. Statuses: 401 invalid/revoked credentials, 403 forbidden origin/CSRF/device mismatch, 404 missing or unauthorized record, 409 idempotency/state conflict, 413 size limit, 415 media type, 422 invalid metadata/checksum, 429 rate limit. Corrupt/silent/overlong media is detected asynchronously by decoding and yields a failed job. These failures do not become transcripts.

## Future protocol extensions

No live streaming, signed firmware, mutual TLS, credential rotation, Bluetooth GATT or physical provisioning flow is implemented. Rotate today by provisioning a replacement device and revoking the previous credential. A future Bluetooth bridge must hold/use the provisioned device credential and use this same upload protocol; Bluetooth connectivity alone never authorizes a request.
