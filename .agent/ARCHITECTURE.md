# TalkSense AI — Architecture Rules & Decisions

> This file captures locked architecture decisions.
> **These are NOT up for debate.** Do not propose changes to these without explicit user approval.

---

## ✅ Locked Decisions

### Infrastructure

| Decision | Choice | Why |
|----------|--------|-----|
| Database | PostgreSQL 16+ on localhost:5432 | CI tests against postgres:16. Local dev uses 16 or 17. |
| DB ORM | SQLAlchemy 2.x async + asyncpg | Async FastAPI compatibility |
| Migrations | Alembic (`alembic upgrade head`) | Production schema management. `create_all()` is NOT used. |
| Auth | JWT for WebSocket subscription channels only | REST endpoints are unauthenticated. Session_id is the primary key. |
| GPU | RTX 3050 Laptop, 4GB VRAM (development target) | CUDA capable, tight budget |
| PyTorch | CUDA 12.x build | Required for GPU-accelerated inference |

### AI Stack

| Decision | Choice | Why |
|----------|--------|-----|
| Transcription | Faster-Whisper `small`, int8, CUDA | Saves VRAM vs float16. Configurable via `WHISPER_MODEL` env var. |
| VAD | Silero VAD | CPU, lightweight, reliable |
| Sentiment | tabularisai/multilingual-sentiment-analysis | Already integrated, production-proven |
| Post-Session AI | Google Gemini 1.5 Flash | Speaker attribution, role classification, executive summaries |

> **Note:** Pyannote speaker diarization is NOT in the production pipeline. It exists only as experimental code in `experimental/diart/`. The production system uses Gemini for post-session speaker attribution.

### Architecture

| Decision | Choice | Why |
|----------|--------|-----|
| Session Modes | Meeting + Sales + Interview | Three analysis modes with mode-specific scoring |
| Real-time first | Dashboard is product, report is byproduct | Vision statement |
| Batch mode | Keep POST /analyze forever | Backward compat with UploadPage flow |
| WebSocket channels | 4 outbound + 1 inbound | Transcript, Metrics, Alerts, Status + Audio |
| Backpressure | Drop old metrics, always deliver alerts | Alerts are critical, metrics are stateful |
| Session persistence | Flush every 5s, restore on crash | Resilience via PostgreSQL |
| Post-session AI | Gemini prompt bundle + response validation | Pydantic-validated structured output |

---

## 🔒 Locked Code (DO NOT MODIFY)

### `backend/services/context_analyzer.py`

These 3 functions are locked. They were fixed after extensive debugging:

1. **`compute_meeting_quality_v2()`** — Meeting quality from signals ONLY
   - Formula: `ownership=True AND execution=True → High`, `XOR → Medium`, `both False → Low`
   - PROHIBITED: Adding sentiment, issues, blockers, topics, transcript scanning

2. **`compose_executive_summary_v2()`** — Pure quality-to-text mapping
   - Deterministic, non-interpretive
   - Output always matches quality label

3. **`generate_key_insights_v2()`** — Max 3 insights, no duplicates, signal-driven
   - Only adds "Ownership Gap" if `ownership == False`
   - Only adds "Decision Ambiguity" if `execution_decision == False`
   - Never adds contradictory insights for High quality

### Singletons — Load Once, Never Reload

All AI models are singleton instances loaded once at startup:
- `audio.vad.get_vad()` — Silero VAD (CPU)
- `audio.transcriber.get_transcriber()` — Faster-Whisper (GPU)
- `services.nlp_engine.NLPEngine()` — Sentiment model (GPU)

**NEVER** reload these mid-request. VRAM is tight.

---

## 🚫 Prohibited Patterns

1. **Do not queue metrics indefinitely.** Drop old metric updates when client lags.
2. **Do not downgrade meeting quality in a try/except.** Fix logic upstream.
3. **Do not hardcode scoring profile weights.** Load from `scoring_profiles.py` JSON.
4. **Do not delete the `/analyze` batch endpoint.** It powers the UploadPage flow.
5. **Do not rewrite context_analyzer.py.** Adapt it, extend it, but never wholesale rewrite.
6. **Do not use `create_all()` for database schema.** Use Alembic migrations.

---

## 📐 Design Patterns

### Real-Time Pipeline Flow
```
Browser mic
    ↓ binary PCM (250ms chunks)
/ws/audio/{session_id}        ← audio_handler.py
    ↓ validated chunks
vad.py                        ← is_speech() → True/False
    ↓ speech chunks only
buffer.py                     ← accumulate until ~2000ms (TARGET_DURATION_MS)
    ↓ ~2000ms buffer
transcriber.py                ← faster-whisper → list[Segment]
    ↓ {start, end, text}
conversation_engine.py        ← update session state, compute metrics
    ↓ ConversationState
alert_engine.py               ← evaluate for alert conditions
    ↓ 0-3 alerts
broadcast.py                  ← emit to /ws/transcript, /ws/metrics, /ws/alerts
    ↓
Browser dashboard
```

### Post-Session Pipeline Flow
```
Session marked COMPLETED
    ↓
post_session_pipeline.py      ← orchestrator
    ↓
prompt_loader.py              ← load versioned prompt bundle
    ↓
llm_engine.py                 ← send transcript + prompt to Gemini
    ↓
response_validator.py         ← Pydantic validation of LLM output
    ↓
PostgreSQL                    ← persist analysis_results
    ↓
Dashboard                     ← retrieve via REST
```

### Session State Machine
```
Created → Connecting → Active → Processing → Completed
                                           → Failed
                                           → Interrupted
                                           → Expired
```
State is managed in `ws/session_manager.py`. Active state is in-memory with 5s PostgreSQL flush.

### Conversation Engine Contract
Input: `new_segments: list[Segment]`, `session_state: ConversationState`, `mode: str`
Output: updated `ConversationState` + list of new alerts

### Alert Engine Contract
Input: `ConversationState`, `mode: str`, `last_alerts: dict` (cooldown tracking)
Output: list of `Alert(level, message, timestamp)`

---

## 🔑 Environment Variables Reference

```
DATABASE_URL=postgresql+asyncpg://postgres:<pw>@localhost:5432/talksense
WHISPER_MODEL=small                      # tiny, base, small, medium, large-v3
WHISPER_COMPUTE_TYPE=int8               # int8 or float16
WHISPER_DEVICE=cuda                     # cuda or cpu
GEMINI_API_KEY=<google_ai_studio_key>   # Required for post-session AI
ENABLE_POST_SESSION_AI=true             # Enable post-session pipeline
POST_SESSION_PROVIDER=gemini
POST_SESSION_MODEL=gemini-1.5-flash
HF_TOKEN=                               # Optional: Hugging Face token (experimental Pyannote only)
JWT_SECRET_KEY=<generated_32_byte_hex>  # python -c "import secrets; print(secrets.token_hex(32))"
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
ENV=development
CORS_ORIGINS=http://localhost:5173
```

---

## 📊 Quality Logic Matrix (LOCKED)

| Signals | Quality | Primary Insight | Ownership Gap? |
|---------|---------|-----------------|----------------|
| ownership=✓, execution=✓ | **High** | Positive Momentum | ❌ Never |
| ownership=✓, execution=✗ | **Medium** | Decision Ambiguity | ❌ No |
| ownership=✗, execution=✓ | **Medium** | Decision Ambiguity | ✅ Yes |
| ownership=✗, execution=✗ | **Low** | Execution Risk | ❌ No (redundant) |
