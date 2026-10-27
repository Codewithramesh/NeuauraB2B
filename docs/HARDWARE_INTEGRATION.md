# Hardware integration

The MVP implements the hardware-facing contract today, with a real HTTP simulator. No ESP32, Raspberry Pi, microphone chipset or wearable form factor is assumed. Physical hardware has NOT been tested.

## Required prototype capabilities

1. Record authorized speech into a supported container/codec (PCM WAV is the simplest initial prototype).
2. Reach the backend over HTTPS, directly or through a trusted phone/desktop bridge.
3. Store a distinct provisioned device credential in secure storage, protect it from logs, and stop using revoked credentials.
4. Generate/persist a session idempotency key, send JSON, compute SHA256, upload bytes, and poll status.
5. Provide a visible recording indicator and implement the human consent procedure before capturing audio.
6. Bound audio duration/size, preserve the original byte sequence during retries and handle a failed/revoked session.

Optional: battery, firmware version, health, Wi-Fi strength, local retry queue, clock metadata and chunking. No camera, GPS, speaker identity or live connectivity is required. Battery and telemetry remain null/absent when unreported; the UI never invents measurements.

## Connection sequence

The administrator registers the device in its business workspace and securely transfers the one-time credential. Device authorization is determined by the server's registry, not an embedded shared secret. A physical device should use hardware-backed storage when available.

The device creates a session via `/api/v1/devices/{id}/sessions` with its own bearer credential and consent attestation. It submits the original recording as one upload or ordered byte chunks; upload completion verifies SHA256 and creates a processing job. Poll status every 2–5 seconds, backing off during failures. See [exact contract](DEVICE_API_SPEC.md).

The transport boundary sets source/device/org metadata. PyAV decodes browser WebM, mobile MP4 or wearable WAV to the same PCM16 mono 16 kHz representation. From there, the same transcription provider, extraction provider, Pydantic evidence validation, database, tasks and aggregation APIs run unchanged. A new codec may need a decoder or adapter; it does not need a new dashboard or intelligence pipeline.

## Simulator

Use `.venv/bin/python device-simulator/submit.py --help`. The simulator requires an explicitly simulated registry entry and genuine audio bytes. It simulates transport identity, not speech or business results. Its status output labels simulated identity. It does not report fabricated battery readings.

Test single upload, chunks, resend duplicate sequence, reconnect after interruption, final hash mismatch, missing sequence, revoked credential, wrong organization, silent/corrupt audio, missing model and missing extraction provider. Automated integration tests cover these contracts; real speech processing was checked with both source types. Running physical radios, mic gain, battery life, flash encryption, TLS roots, clock behavior and noisy-room audio remains hardware validation work.

## Production hardening before a fleet

Secure device enrollment and recovery, credential rotation, certificate trust, TLS termination, firmware updates, local queue encryption, shared rate limits, storage quotas, monitoring and fleet lifecycle need implementation/evaluation before public production exposure. The present registry uses one revocable bearer credential per device and process-local request limits.
