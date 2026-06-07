# TalkSense AI v4 — Architecture Rules & Decisions

> This file captures locked architecture decisions.
> **These are NOT up for debate.** Do not propose changes to these without explicit user approval.

---

## ✅ Locked Decisions

### Infrastructure

| Decision | Choice | Why |
|----------|--------|-----|
| Database | PostgreSQL 17.5 on localhost:5432 | Already installed, running |
| DB ORM | SQLAlchemy 2.x async + asyncpg | Async FastAPI compatibility |
| Auth | JWT + bcrypt, minimal scope | Deferred for now; session_id is the key |
| GPU | RTX 3050 Laptop, 4GB VRAM | CUDA capable, tight budget |
| PyTorch | CUDA 12.x build | Current CPU build must be replaced |

### AI Stack

| Decision | Choice | Why |
|----------|--------|-----|
| Transcription | faster-whisper small (or medium), int8, CUDA | Saves VRAM vs float16 |
| Diarization | pyannote/speaker-diarization-3.1 | Best quality, HF-gated |
| VAD | Silero VAD | CPU, lightweight, reliable |
| Sentiment | tabularisai/multilingual-sentiment-analysis | Already integrated, keep it |

### Architecture

| Decision | Choice | Why |
|----------|--------|-----|
| Modes V1 | Meeting + Sales only | Interview added in Phase 6 |
| Real-time first | Dashboard is product, report is byproduct | Vision statement |
| Batch mode | Keep POST /analyze forever | Backward compat with old frontend |
| WebSocket channels | 4 outbound + 1 inbound | Transcript, Metrics, Alerts, Status |
| Backpressure | Drop old metrics, always deliver alerts | Alerts are critical, metrics are stateful |
| Session persistence | Flush every 5s, restore on crash | Resilience |
| VRAM safety fallback | Pause Pyannote if VRAM < 500MB | GPU safety |

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
- `audio.vad.get_vad()` — Silero VAD
- `audio.transcriber.get_transcriber()` — Faster Whisper
- `audio.diarizer.get_diarizer()` — Pyannote
- `services.nlp_engine.NLPEngine()` — Sentiment model

**NEVER** reload these mid-request. VRAM is tight.

---

## 🚫 Prohibited Patterns

1. **Do not run Whisper + Pyannote simultaneously on the GPU.** Pyannote runs on a delayed rolling window.
2. **Do not queue metrics indefinitely.** Drop old metric updates when client lags.
3. **Do not downgrade meeting quality in a try/except.** Fix logic upstream.
4. **Do not hardcode scoring profile weights.** Load from `scoring_profiles.py` JSON.
5. **Do not delete the `/analyze` batch endpoint.** It powers the old UploadPage flow.
6. **Do not rewrite context_analyzer.py.** Adapt it, extend it, but never wholesale rewrite.

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
buffer.py                     ← accumulate until ~1000ms
    ↓ 1000ms buffer
transcriber.py                ← faster-whisper → list[Segment]
    ↓ {start, end, text, speaker=None}
diarizer.py                   ← assign speaker_id by time overlap
    ↓ {start, end, text, speaker}
conversation_engine.py        ← update session state, compute metrics
    ↓ ConversationState
alert_engine.py               ← evaluate for alert conditions
    ↓ 0-3 alerts
broadcast.py                  ← emit to /ws/transcript, /ws/metrics, /ws/alerts
    ↓
Browser dashboard
```

### Session State Machine
```
Created → Connecting → Active → Processing → Completed
                                           → Failed
                                           → Interrupted
                                           → Expired
```
State is managed in `ws/session_manager.py`. All state is currently in-memory (pending Phase 3 DB).

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
HF_TOKEN=<huggingface_token>            # Required for Pyannote
WHISPER_MODEL=small                      # or medium (uses more VRAM)
WHISPER_COMPUTE_TYPE=int8               # float16 if VRAM allows
WHISPER_DEVICE=cuda                     # or cpu as fallback
PYANNOTE_ENABLED=true                   # false = heuristic speaker labeling
PYANNOTE_DEVICE=cuda
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

---

## 🏗 Phase 3 DB Implementation Guide

When building Phase 3, follow this order:

1. Create `backend/db/__init__.py` (empty)
2. Create `backend/db/models.py` — all 8 SQLAlchemy models with indexes
3. Create `backend/db/database.py` — async engine, `get_db()` dependency
4. Create `backend/db/crud.py` — CRUD for sessions, clients, transcripts, metrics, alerts, reports, snapshots
5. Add DB init (create_all) to `main.py` lifespan startup
6. Wire session_manager to flush to DB every 5s
7. Wire session end → write analysis_results + update client_snapshots

**Do NOT use Alembic for the first build.** Use `Base.metadata.create_all()`. Add migrations later.
