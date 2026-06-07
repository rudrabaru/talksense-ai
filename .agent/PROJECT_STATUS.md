# TalkSense AI v4 — Project Build Status

> Last updated: 2026-06-06  
> Always update this file when completing or starting a phase.

---

## Phase Summary

| Phase | Description | Status | Notes |
|-------|-------------|--------|-------|
| Phase 1 | Real-Time Audio Pipeline | ✅ COMPLETE | All files built and integrated |
| Phase 2 | Conversation Engine | ✅ COMPLETE | Engine, scoring, alerts all built |
| Phase 3 | Database & Persistence | ❌ NOT STARTED | `backend/db/` directory is empty |
| Phase 4 | Live React Dashboard | ❌ NOT STARTED | Only old pages exist; no hooks |
| Phase 5 | Client Memory & Reports | ❌ NOT STARTED | `memory_service.py`, `report_service.py` missing |
| Phase 6 | Interview Mode | ❌ NOT STARTED | Conversation engine needs mode extension |

---

## Phase 1 — Real-Time Audio Pipeline ✅

**Files:**
- `backend/audio/vad.py` — Silero VAD, singleton, CPU
- `backend/audio/buffer.py` — audio accumulation buffer, 1000ms flush
- `backend/audio/transcriber.py` — faster-whisper, singleton, GPU/int8
- `backend/audio/diarizer.py` — Pyannote 3.1, optional, GPU
- `backend/ws/audio_handler.py` — `/ws/audio/{session_id}` endpoint
- `backend/ws/session_manager.py` — session state machine
- `backend/ws/broadcast.py` — 4-channel WebSocket broadcaster
- `backend/ws/subscriptions.py` — `/ws/{channel}/{session_id}` subscription endpoints
- `backend/main.py` — startup warmup + REST endpoints (fully updated)

**Verification status:** NOT yet formally verified (uvicorn startup untested since last session).

---

## Phase 2 — Conversation Engine ✅

**Files:**
- `backend/engine/conversation_engine.py` — segments → metrics → state update
- `backend/engine/scoring_profiles.py` — JSON-driven mode scoring weights
- `backend/engine/alert_engine.py` — cooldown, dedup, severity, max-3 rule

**Reuses from legacy:**
- `backend/services/context_analyzer.py` → `compute_meeting_quality_v2()`, `compose_executive_summary_v2()`, `generate_key_insights_v2()` — all 3 locked, do not modify
- `backend/services/nlp_engine.py` → sentiment pipeline adapted for per-segment streaming

---

## Phase 3 — Database & Persistence ❌

**What's needed:**
- `backend/db/__init__.py`
- `backend/db/models.py` — SQLAlchemy ORM for all 8 tables
- `backend/db/database.py` — async PostgreSQL engine via asyncpg
- `backend/db/crud.py` — CRUD functions for all models

**Integration work after DB is built:**
- Session flush every 5s (into session_manager or a background task)
- On session end: write `analysis_results`, update `client_snapshots`
- On crash recovery: restore session from last DB snapshot

**DB target:** PostgreSQL 17.5, localhost:5432, database `talksense`  
**ORM:** SQLAlchemy 2.x async (`asyncpg` driver)

---

## Phase 4 — Live React Dashboard ❌

**New files needed:**
- `talksense-ui/src/pages/SessionStartPage.jsx`
- `talksense-ui/src/pages/DashboardPage.jsx` ← MAIN PRODUCT PAGE
- `talksense-ui/src/components/dashboard/TranscriptPanel.jsx`
- `talksense-ui/src/components/dashboard/IntelligencePanel.jsx`
- `talksense-ui/src/components/dashboard/AlertPanel.jsx`
- `talksense-ui/src/hooks/useSessionWebSocket.js`
- `talksense-ui/src/hooks/useAudioCapture.js`

**Files needing update:**
- `talksense-ui/src/App.jsx` — add new routes (currently only has old batch routes)

**Current App.jsx routes (OLD):**
```
/        → TranscriptLive (prototype)
/home    → HomePage
/upload  → UploadPage
/results → ResultsPage
/live    → TranscriptLive
```

**Target App.jsx routes (NEW):**
```
/                  → HomePage
/start             → SessionStartPage
/dashboard/:id     → DashboardPage  ← main product
/upload            → UploadPage (keep)
/results           → ResultsPage (keep)
/history           → SessionHistoryPage
/clients           → ClientsPage
/report/:id        → ReportPage
```

---

## Phase 5 — Client Memory & Reports ❌

**New files needed:**
- `backend/services/memory_service.py`
- `backend/services/report_service.py`
- `talksense-ui/src/pages/ReportPage.jsx`
- `talksense-ui/src/pages/SessionHistoryPage.jsx`
- `talksense-ui/src/pages/ClientsPage.jsx`
- `talksense-ui/src/components/ClientBriefingCard.jsx`

**Depends on:** Phase 3 (DB) must be complete first.

---

## Phase 6 — Interview Mode ❌

**What's needed:**
- Extend `backend/engine/conversation_engine.py` with interview metrics:
  - Confidence score (proxy via speech rate + filler words + pause duration)
  - Filler word detection (um, uh, like, you know, basically)
  - Pause detection (>2s within speaker turn)
  - Response quality (length + vocabulary diversity)
- Update `backend/engine/scoring_profiles.py` if interview weights need tuning

**Depends on:** Phase 4 (Dashboard) should be working first.

---

## Known Issues / Open Items

- [ ] PyTorch CUDA build: current install is `2.9.1+cpu` → needs reinstall with CUDA 12.x wheel before Whisper can use GPU
- [ ] Pyannote HF token: must be set in `.env` and model license accepted on HuggingFace before diarization works
- [ ] DB not yet connected: all session state is currently in-memory only (lost on restart)
- [ ] `App.jsx` routes are still the old prototype routes — needs update in Phase 4

---

## How to Run (Current State)

```powershell
# Backend
cd backend
venv\Scripts\activate
uvicorn main:app --reload

# Frontend
cd talksense-ui
npm run dev
```

Visit `http://localhost:5173/live` for the prototype live transcript view.  
Visit `http://localhost:8000/docs` for the FastAPI Swagger UI.
