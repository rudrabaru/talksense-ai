# TalkSense AI — Project Build Status

> Last updated: 2026-08-13 (Documentation Audit)
> Always update this file when completing or starting a phase.

---

## Phase Summary

| Phase | Description | Status | Notes |
|-------|-------------|--------|-------|
| Phase 1 | Real-Time Audio Pipeline | ✅ COMPLETE | VAD → Buffer → Whisper (no Pyannote in production) |
| Phase 2 | Conversation Engine | ✅ COMPLETE | Engine, scoring, alerts, meeting/sales modes |
| Phase 3 | Database & Persistence | ✅ COMPLETE | PostgreSQL 16+, async ORM, 8 tables, Alembic, background flusher |
| Phase 4 | Live React Dashboard | ✅ COMPLETE | 8 pages, 5 WS channels, WebSocket hook |
| Phase 5 | Client Memory & Reports | ✅ COMPLETE | Client snapshots, session comparison, post-session AI |
| Phase 6 | Interview Mode | ⚠️ SKELETON ONLY | Scoring profile defined, metrics hardcoded at 50 |

---

## Current Architecture Summary

### What Works

- **Real-time pipeline**: Audio → VAD → Buffer → Whisper → NLP → Conversation Engine → Alerts → Dashboard
- **Session management**: Deferred-watermark flushing, event-based idle signaling, proper shutdown
- **Post-session AI**: Gemini 1.5 Flash for speaker attribution, role classification, executive summaries
- **Analytics engine**: Meeting/Sales quality scoring, objection handling, conversation intelligence
- **Frontend**: Complete WS integration with exponential backoff + REST reconciliation
- **Database**: Async ORM, Alembic migrations, cascading deletes, composite indexes, JSONB metrics
- **CI/CD**: 4 GitHub Actions workflows (backend, frontend, integration, QA pipeline)

### Known Limitations

| Priority | Item | Status |
|----------|------|--------|
| P1 | REST endpoints have zero authentication | Not enforced |
| P1 | `/ws/audio` does not verify JWT token | Frontend sends token but backend ignores it |
| P2 | Interview mode metrics hardcoded at 50.0 | Skeleton only |
| P2 | `main.py:L97` log message says "create_all()" but no such call exists | Misleading log |
| P2 | `models.py:L21-22` docstring says "No Alembic" but Alembic IS active | Stale docstring |

---

## Phase 1 — Real-Time Audio Pipeline ✅

**Files:**
- `backend/audio/vad.py` — Silero VAD, singleton, CPU
- `backend/audio/buffer.py` — audio accumulation buffer, ~2000ms target flush (`TARGET_DURATION_MS`)
- `backend/audio/transcriber.py` — Faster-Whisper, singleton, GPU/int8
- `backend/audio/gpu_manager.py` — GPU concurrency management
- `backend/ws/audio_handler.py` — `/ws/audio/{session_id}` endpoint
- `backend/ws/session_manager.py` — session state machine with background flusher
- `backend/ws/broadcast.py` — 4-channel WebSocket broadcaster
- `backend/ws/subscriptions.py` — `/ws/{channel}/{session_id}` subscription endpoints (JWT-protected)
- `backend/main.py` — startup warmup + REST endpoints

> **Note:** `audio/diarizer.py` does NOT exist. There is no real-time diarization in production.

---

## Phase 2 — Conversation Engine ✅

**Files:**
- `backend/engine/conversation_engine.py` — segments → metrics → state update
- `backend/engine/scoring_profiles.py` — mode-specific scoring weights
- `backend/engine/alert_engine.py` — 7 alert types, cooldown, dedup, max-3 rule

**Scoring Profiles:**
```
Meeting:  participation(40%) + engagement(30%) + balance(20%) + action_items(10%)
Sales:    objection_handling(35%) + sentiment(25%) + listening_ratio(20%) + buying_signals(20%)
Interview: confidence(35%) + filler_penalty(25%) + response_quality(25%) + pause_penalty(15%)
```

---

## Phase 3 — Database & Persistence ✅

**Files:**
- `backend/db/models.py` — 8 tables (users, clients, sessions, transcript_segments, session_metrics, analysis_results, alerts, client_snapshots)
- `backend/db/database.py` — async PostgreSQL engine
- `backend/db/crud.py` — full CRUD operations
- `backend/alembic/` — migration scripts (1 baseline migration: `dc184fe69e15`)

**Schema Management:** Alembic (`alembic upgrade head`). `create_all()` is NOT used.

**Background Flusher:**
- 5-second interval
- Semaphore-throttled (max 5 concurrent)
- Deferred watermark pattern
- Hash-based metric dedup
- Event-based idle signaling

---

## Phase 4 — Live React Dashboard ✅

**Pages:** HomePage, DashboardPage, UploadPage, ResultsPage, SessionsPage, ComparisonPage, SystemAudioTester, NotFoundPage

**Key Components:**
- `useSessionWebSocket.js` — 4-channel WS with exponential backoff + REST reconciliation
- Dashboard panels (TranscriptPanel, MetricsPanel, AlertPanel, etc.)
- Audio source management (Microphone, System, PCM)

---

## Phase 5 — Client Memory & Reports ✅

**Services:**
- `backend/services/post_session_pipeline.py` — post-session AI orchestrator
- `backend/services/llm_engine.py` — Gemini API wrapper
- `backend/services/response_validator.py` — Pydantic validation of LLM output
- `backend/services/prompt_loader.py` — versioned prompt bundle loader
- `backend/services/client_memory.py` — client snapshot aggregation
- `backend/services/comparison.py` — session comparison logic
- `backend/services/objection_handler.py` — objection analysis (tested in CI)
- `backend/services/transcript_builder.py` — transcript formatting (tested in CI)

---

## Phase 6 — Interview Mode ⚠️ SKELETON

**Status:** Scoring profile defined but incomplete:
- `response_quality = 50.0` (hardcoded placeholder — no actual response quality analysis)
- `pause_penalty` is computed from silence duration (not a placeholder)
- No response quality analysis implemented

---

## How to Run

```powershell
# Backend
cd backend
venv\Scripts\activate
alembic upgrade head
uvicorn main:app --reload

# Frontend
cd talksense-ui
npm run dev
```

Visit `http://localhost:5173` for the dashboard.
Visit `http://localhost:8000/docs` for the FastAPI Swagger UI.
