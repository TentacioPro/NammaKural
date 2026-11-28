# Voice V1 streaming scaffold

This branch adds an isolated, observable scaffold for the proposed NammaKural voice architecture. It does **not** claim to deliver sub-500 ms end-to-end voice yet. Its test endpoint injects text directly into the existing civic workflow; it intentionally reports `voice_ttfa_ms: null` because microphone capture, VAD/endpointing, streaming ASR, TTS audio, network delivery, and browser playback are not exercised by that endpoint.

## Start the scaffold

From the repository root:

```bash
docker compose -f docker-compose.voice.yml up --build
```

The core command starts the text/test API, Prometheus, and Jaeger. The optional media fragment declares LiveKit and Coturn, but its worker remains an adapter gate and is not a working streaming agent. Review placeholders, TURN credentials, public IP/port mapping, firewall rules, and TLS before enabling it:

```bash
export LIVEKIT_API_KEY='use-a-secret-manager-value'
export LIVEKIT_API_SECRET='use-a-long-random-secret'
export TURN_REALM='your-reachable-turn-domain'
export TURN_USERNAME='short-lived-credential-user'
export TURN_PASSWORD='short-lived-credential-secret'
export TURN_PUBLIC_IP='your-public-ip'
docker compose -f docker-compose.voice.yml -f ops/livekit.voice.yml up livekit coturn
```

Those TURN values are illustrative environment variables, not production credential issuance. The browser ICE configuration and short-lived TURN credential service still need to be implemented; do not expose the sample/static values to public clients.

An optional PostGIS service can initialize the included schema on its first volume creation. Set a strong local `NK_PG_PASSWORD` first:

```bash
export NK_PG_PASSWORD='local-development-secret'
docker compose -f docker-compose.voice.yml --profile database up -d postgis
```

The application does not connect to this database yet. The SQL init mount runs only when PostgreSQL initializes an empty data volume; schema changes later require reviewed migrations.

Endpoints:

- API docs: <http://localhost:8000/docs>
- Health: <http://localhost:8000/healthz>
- Readiness/provider selection: <http://localhost:8000/readyz> and <http://localhost:8000/v1/providers>
- Prometheus metrics: <http://localhost:8000/metrics>
- Prometheus UI: <http://localhost:9090>
- Jaeger traces: <http://localhost:16686>

The API writes OTLP/HTTP traces to Jaeger. If you run the app outside Compose and leave `OTEL_EXPORTER_OTLP_ENDPOINT` empty, spans are still created in-process but are not exported. The app attempts a bounded trace flush on shutdown. Prometheus histograms are exposed directly by the API.

Exercise the actual existing civic FSM through the text harness:

```bash
curl -sS http://localhost:8000/v1/test/turn \
  -H 'content-type: application/json' \
  -H 'x-request-id: local-check-001' \
  -d '{"utterance":"Anna Nagar-la streetlight eriyala","session_id":"demo-session-001","lang":"tanglish","llm_mode":"offline"}'
```

The response carries `request_id`, `session_id`, and `turn_id`, plus `workflow_ms`. `voice_ttfa_ms` must remain null for this endpoint. Do not use this text-only measurement as voice latency evidence.

When a real audio client is wired, it can report the user-perceived playback start to `/v1/telemetry/playback`:

```bash
curl -sS http://localhost:8000/v1/telemetry/playback \
  -H 'content-type: application/json' \
  -d '{"turn_id":"turn-demo-1","event":"playback_started","clock_origin":"browser-performance.now","end_of_speech_ms":1000,"playback_started_ms":1460}'
```

Both timestamps must come from the same client monotonic clock. Never subtract a server wall-clock timestamp from `performance.now()`. The endpoint rejects negative or over-60-second intervals and returns a typed success response. Its metric is client-reported and must not be treated as an SLO until the actual end-of-speech and first-playable-audio event semantics have been verified. Prometheus request labels use route templates rather than arbitrary URL paths (unmatched 404s use the fixed `unmatched` label).

Run tests:

```bash
# Preferred isolated environment (Python 3.11 or newer)
conda create -n nk-voice python=3.11 -y
conda activate nk-voice
pip install -r requirements.txt
pytest -q tests/test_voice_v1_scaffold.py
pytest -q tests/test_voice_v1_*.py
```

Inspect a PCM16 WAV fixture without resampling or losing its true input sample rate:

```bash
python -m backend.voice_v1.media.replay path/to/consented-fixture-8khz.wav --frame-ms 20
```

## Telemetry contract

Metrics are low-cardinality and never use session/turn IDs as labels:

- `nk_voice_requests_total{route,status}`
- `nk_voice_stage_duration_seconds{stage,provider,outcome}`
- `nk_voice_end_of_speech_to_first_audio_seconds` — reserved for real audio sessions, not populated by text tests
- `nk_voice_pipeline_errors_total{stage,error_type}`

OTel spans are correlated by trace context and record opaque request/session/turn IDs as attributes. Never attach raw audio, full transcripts, OTPs, phone numbers, or other PII to spans. Add explicit retention/access controls before using an exported trace backend with real calls.

## Provider integration status

`backend/voice_v1/contracts.py` defines timestamped audio frames (rate, channels, format, codec, monotonic capture time), ASR partial/final transcript timing, separate `display_text` and `tts_text`, voice/rate controls, and incremental TTS chunks. The default app uses the existing deterministic NammaKural workflow only. `/v1/providers` and `/readyz` intentionally show that realtime transport/ASR/TTS are not configured.

`backend/voice_v1/session.py` composes injected ASR, workflow, normalization, and TTS adapters as an async event stream, propagates session/turn/epoch identifiers, rejects stale output, and cancels the active pipeline on a committed interruption or disconnected consumer. Backchannels can resume a temporarily paused turn. This session core is tested with fakes but is **not wired to the FastAPI text harness, LiveKit, a browser playback queue, or real adapters**; provider cancellation cannot roll back an external mutation, which still requires durable idempotency and postcondition reconciliation.

`backend/voice_v1/turn_policy.py` provides testable initial endpointing windows by active slot, conservative backchannel classification, pause/resume state, explicit turn completion, and epoch tags so adapters can ignore stale completions after a committed interruption. The session core propagates cancellation through awaited adapter calls; it does not implement the actual 250–350 ms classifier timer, incoming media queue, provider-specific task cancellation, or playback queue flush. The endpoint windows are starting hypotheses and require replay evaluation.

The next implementation gates are:

1. Connect the browser to a real LiveKit room and a dedicated worker; add Coturn with deployment-specific public IP, ports, auth, and firewall configuration; verify direct and TURN media paths.
2. Implement decode/resample and frame timestamp preservation, then VAD and per-slot endpointing on real input. Confirm exact units and sampling behavior for each model.
3. Implement a real ASR adapter that consumes timestamped audio frames and emits partial/final Tamil/Tanglish hypotheses. IndicConformer or SraVaani must be selected based on the exact streaming API/runtime and tested; batch REST upload is not sufficient for the fast path.
4. Connect ASR, workflow, tool policy, local streaming LLM, and incremental TTS through a session orchestrator. Preserve `session_id`/`turn_id`; normalize speech output and make provider calls cancellable. Add warm-model and prefix-cache behavior only for runtimes that support it.
5. Wire pause/resume, explicit stop detection, context-aware backchannels, epoch-tagged tool operations, and verified audio queue flushes. Speculative generation/prefetch must be side-effect-free until intent is stable; comfort noise must be opt-in, tested, and not mask important audio.
6. Add headless multi-turn WAV/PCM replay; evaluate Tamil script, Tanglish, code-switching, dialects, 8 kHz telephony, noise, negation, names, numbers, interruption, and silence.
7. Add PostgreSQL/PostGIS schema and migrations, durable case state, idempotency and transactional outbox only after authorized grievance channels and data contracts are confirmed. Build authenticated HITL staff access with a real identity provider, roles, audit, and security review.
8. Populate `nk_voice_end_of_speech_to_first_audio_seconds` only when both timestamps are measured on a real audio session. Include clock-origin metadata and do not subtract unsynchronized device/server wall clocks.

For all production reports, publish p50/p90/p95/p99, identify warm/cold state, hardware, model/checkpoint, language, codec, region, and TURN use. Sub-500 ms is a target to measure, not a promise from the scaffold. The existing branch remains unchanged except for added files and dependencies; the existing `backend.main:app` deployment is untouched.

See [VOICE_V1_REQUIREMENTS_STATUS.md](VOICE_V1_REQUIREMENTS_STATUS.md) for a point-by-point coverage matrix and explicit production gates.
