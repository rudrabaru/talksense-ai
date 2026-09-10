# Backend Agent Specialist

## Authoritative References

Read [`.agent/SPECIALIST_PREAMBLE.md`](../SPECIALIST_PREAMBLE.md) first — shared control
documents, cross-cutting invariants, and the verification ladder.

Most relevant control files for backend work: `.agent/API_CONTRACT.md` (payload shapes),
`.agent/ARCHITECTURE.md` (pipeline design, GPU sequencing), `.agent/ACTIVE_FILES.md`
(current locks), `.agent/TESTING_CHECKLIST.md` (what is and is not verified).

---

## Scope of Responsibility

The backend agent owns the FastAPI application, audio processing pipeline, conversation/alert engines, session lifecycle, and all services under `backend/`.

**Does NOT own:**
- Database schema or migrations → Database Agent
- Frontend React application → Frontend Agent
- CI/CD workflows → outside specialist scope
- Security policy → Security Agent

---

## Directory Ownership

```
backend/
├── main.py                      ← FastAPI app, all REST routes, startup lifespan
├── audio/
│   ├── vad.py                   ← Silero VAD (CPU) — speech/silence classifier
│   ├── buffer.py                ← PCM accumulation, WAV writing, flush logic
│   └── transcriber.py           ← faster-whisper wrapper (async, thread-pool)
├── engine/
│   ├── conversation_engine.py   ← per-segment processing, metrics, scoring
│   └── alert_engine.py          ← real-time alert evaluation and cooldowns
├── services/
│   ├── nlp_engine.py            ← sentiment Transformer (LOCKED — do not modify init)
│   ├── context_analyzer.py      ← meeting quality, insights (LOCKED functions)
│   ├── post_session_pipeline.py ← Gemini post-session analysis
│   ├── llm_engine.py            ← LLM abstraction layer
│   ├── prompt_loader.py         ← versioned prompt loading
│   └── response_validator.py    ← LLM response JSON validation
├── ws/
│   ├── audio_handler.py         ← /ws/audio/{session_id} — PCM ingest, pipeline
│   ├── subscriptions.py         ← 4 read-only WS channels (transcript/metrics/alerts/status)
│   ├── session_manager.py       ← SessionState, SessionManager, background flusher
│   └── broadcast.py             ← push events to connected WS clients
├── core/
│   ├── config.py                ← pydantic-settings; all env-var defaults
│   └── security.py              ← JWT token creation/verification (ws_token only)
└── utils/
    └── profiler.py              ← stage timing context manager
```

---

## Backend-Specific Invariants

### Audio Pipeline
- VAD processes 100–250ms PCM chunks (CPU, Silero).
- AudioBuffer flushes at `TARGET_DURATION_MS = 2000ms` of speech audio (not 1000ms).
- Silence-gap flush fires at `SILENCE_GAP_MS = 600ms` after speech ends.
- Minimum flush threshold: `MIN_FLUSH_MS = 800ms` — chunks below this are discarded.
- Overlap retention: `OVERLAP_MS = 1000ms` kept on partial flushes.
- All PCM (speech + silence) is written to session WAV file for post-session use.
- Whisper runs via `run_in_executor` — never block the event loop with Whisper.

### Transcription
- Model: `faster-whisper`, default `small`, `int8`, device from `WHISPER_DEVICE` env var.
- `initial_prompt` is currently set to `prev_text[-200:]` (last confirmed segment text).
- **UNRESOLVED:** Whether this should be `None` or retain context conditioning is disputed. Do not change `initial_prompt` behavior without explicit team decision. See `.agent/DECISION_LOG.md`.
- `condition_on_previous_text=True` is preserved.

### Speaker Diarization
- `diarizer = None` in the live pipeline. All live segments are assigned "Speaker 1".
- This is a known architectural gap, not a bug to silently fix.
- Post-session speaker attribution is done by the Gemini LLM from text only.
- Do NOT introduce Pyannote or diart into the live pipeline without team approval.
- There is no `audio/diarizer.py`. Do not create one without a design decision.

### Session Lifecycle
- Sessions transition: `created → active → recording → completed/failed/interrupted/expired`
- `SessionManager.end()` must be the only path to terminal state.
- `FLUSH_INTERVAL_SECONDS = 5.0` — background flusher persists telemetry every 5s.
- `_FLUSH_SEMAPHORE` gates concurrent flush workers.
- `session.remove()` is called after persistence completes — in-memory state is gone after this point.

### Engines
- `ConversationEngine.process_segments()` is the single entry point for all metric updates.
- Alert cooldown: `COOLDOWN_SECONDS = 30` — applies uniformly to all alert types.
- Max active alerts: `MAX_ACTIVE_ALERTS = 3`.
- Do NOT alter locked functions in `context_analyzer.py`:
  - `compute_meeting_quality_v2()`
  - `compose_executive_summary_v2()`
  - `generate_key_insights_v2()`
- Do NOT modify sentiment classifier initialization in `nlp_engine.py`.

### Post-Session AI
- Controlled by `ENABLE_POST_SESSION_AI` env var (default: `false`).
- Only triggered on `SessionStatus.COMPLETED`, never on FAILED/INTERRUPTED.
- Pipeline: `post_session_pipeline.py → prompt_loader.py → llm_engine.py → response_validator.py`
- LLM: Google Gemini (`gemini-1.5-flash` default) via `google-genai` package.
- `test_llm_engine.py` and `test_post_session_pipeline.py` require `google-genai` installed — this is NOT in standard `requirements.txt`.

---

## Required Checks Before Merging Backend Changes

- [ ] Payload shapes match `.agent/API_CONTRACT.md`
- [ ] GPU model loads remain singleton and sequential
- [ ] Database writes are non-blocking (async, background tasks)
- [ ] Schema changes use Alembic — never `create_all()`
- [ ] Alert cooldown (`COOLDOWN_SECONDS = 30`) and cap (`MAX_ACTIVE_ALERTS = 3`) unchanged
- [ ] `process_segments()` watermark logic not broken
- [ ] `session_manager.end()` final flush sequence not bypassed
- [ ] No Pyannote import introduced in live pipeline

---

## Forbidden Changes

- Do not use `Base.metadata.create_all()` anywhere.
- Do not run Whisper and sentiment models concurrently on the GPU.
- Do not block the WebSocket audio ingest loop with synchronous I/O.
- Do not introduce root-level folders without architecture approval.
- Do not modify `context_analyzer.py` locked functions.
- Do not modify `nlp_engine.py` singleton initialization.
- Do not delete session WAV files before `flush_remaining()` completes.

---

## Escalation Conditions

Escalate to team review before making changes that:

- Alter the buffer flush thresholds or overlap strategy
- Change `initial_prompt` behavior in transcription
- Introduce real-time speaker diarization
- Modify the post-session pipeline prompt or response schema
- Add new ML models to the startup sequence
- Change scoring profile weights (meeting/sales/interview)
