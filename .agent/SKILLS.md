# TalkSense AI v4 — Agent Skills Reference

> **Read this file before touching any code in this repo.**
> It is the single source of truth for architecture, conventions, and build status.

---

## 1. What Is This Project?

TalkSense AI is an **AI-Powered Conversation Intelligence Platform** that analyzes conversations in real-time and delivers actionable insights before the conversation ends.

- **NOT** a transcription tool. **NOT** a meeting recorder. **NOT** a report generator.
- Those are supporting capabilities. **The dashboard IS the product.**
- Core value: understand conversations while they happen → alerts, metrics, history.

**Spec documents:**
- Architecture blueprint → `docs/archive/TalkSenseAI_New_Plan.md`
- Implementation plan   → `docs/new_implementation_plan.md`
- Agent decisions log   → `.agent/` (all files here)

---

## 2. Tech Stack

| Layer         | Technology                              |
|---------------|-----------------------------------------|
| Backend       | Python 3.11+, FastAPI, uvicorn          |
| Frontend      | React (Vite), vanilla CSS               |
| Database      | PostgreSQL 17.5 on localhost:5432       |
| Transcription | `faster-whisper` small/medium, int8     |
| Diarization   | `pyannote/speaker-diarization-3.1`      |
| Sentiment     | `tabularisai/multilingual-sentiment-analysis` (HuggingFace transformers) |
| VAD           | Silero VAD (CPU, lightweight)           |
| GPU           | RTX 3050 Laptop, 4GB VRAM              |
| PyTorch       | CUDA 12.x build (NOT cpu build)         |
| Auth          | JWT + bcrypt (deferred — session_id keyed for now) |

**VRAM Budget Rule:** Whisper + Pyannote CANNOT run simultaneously on 4GB.  
→ Pyannote runs on a rolling delayed window. Whisper runs first.  
→ If VRAM < 500MB: pause Pyannote, use turn-boundary heuristic for speakers.

---

## 3. Project Directory Map

```
talksense-ai/
├── backend/
│   ├── main.py                  ← FastAPI app entry point (v4, fully updated)
│   ├── requirements.txt         ← Python deps
│   ├── .env.example             ← Copy to .env and fill in
│   ├── core/
│   │   └── config.py            ← Pydantic-settings config (env vars)
│   ├── audio/                   ← Real-time audio pipeline (ALL BUILT ✅)
│   │   ├── vad.py               ← Silero VAD wrapper
│   │   ├── buffer.py            ← Audio accumulation buffer
│   │   ├── transcriber.py       ← Faster-Whisper transcription service
│   │   └── diarizer.py          ← Pyannote speaker diarization
│   ├── engine/                  ← Conversation intelligence (ALL BUILT ✅)
│   │   ├── conversation_engine.py ← Heart of the product
│   │   ├── scoring_profiles.py  ← Mode-specific scoring weights
│   │   └── alert_engine.py      ← Real-time alert generation
│   ├── ws/                      ← WebSocket layer (ALL BUILT ✅)
│   │   ├── audio_handler.py     ← /ws/audio/{session_id} endpoint
│   │   ├── session_manager.py   ← Session state machine
│   │   ├── broadcast.py         ← WebSocket broadcaster (4 channels)
│   │   └── subscriptions.py     ← /ws/{channel}/{session_id} sub endpoints
│   ├── db/                      ← ⚠️ NOT YET BUILT (Phase 3)
│   │   ├── models.py            ← SQLAlchemy ORM models [TODO]
│   │   ├── database.py          ← Async engine setup [TODO]
│   │   └── crud.py              ← CRUD operations [TODO]
│   ├── services/
│   │   ├── context_analyzer.py  ← Legacy batch analysis (KEEP, DO NOT REWRITE)
│   │   ├── nlp_engine.py        ← NLP enrichment (KEEP, adapted for streaming)
│   │   ├── speech_to_text.py    ← Legacy whisper wrapper (batch only)
│   │   ├── memory_service.py    ← ⚠️ NOT YET BUILT (Phase 5)
│   │   └── report_service.py    ← ⚠️ NOT YET BUILT (Phase 5)
│   └── utils/
│       └── config_loader.py     ← Kept from v3
│
├── talksense-ui/src/
│   ├── App.jsx                  ← ⚠️ NEEDS UPDATE (only has old routes)
│   ├── index.css                ← Design system CSS
│   ├── pages/
│   │   ├── HomePage.jsx         ← Kept (minor CTA updates needed)
│   │   ├── UploadPage.jsx       ← Kept (batch mode)
│   │   ├── ResultsPage.jsx      ← Kept (batch results)
│   │   ├── SessionStartPage.jsx ← ⚠️ NOT YET BUILT (Phase 4)
│   │   ├── DashboardPage.jsx    ← ⚠️ NOT YET BUILT (Phase 4) ← MAIN PRODUCT
│   │   ├── ReportPage.jsx       ← ⚠️ NOT YET BUILT (Phase 5)
│   │   ├── SessionHistoryPage.jsx ← ⚠️ NOT YET BUILT (Phase 5)
│   │   └── ClientsPage.jsx      ← ⚠️ NOT YET BUILT (Phase 5)
│   ├── components/
│   │   ├── InsightCard.jsx      ← Kept
│   │   ├── ModeSelector.jsx     ← Kept
│   │   ├── SentimentBadge.jsx   ← Kept
│   │   ├── TranscriptBlock.jsx  ← Kept
│   │   ├── TranscriptLive.jsx   ← Legacy live view (superseded by DashboardPage)
│   │   ├── dashboard/           ← ⚠️ NOT YET BUILT (Phase 4)
│   │   │   ├── TranscriptPanel.jsx  ← live scrolling transcript
│   │   │   ├── IntelligencePanel.jsx ← metrics center panel
│   │   │   └── AlertPanel.jsx       ← right panel alerts
│   │   └── ClientBriefingCard.jsx ← ⚠️ NOT YET BUILT (Phase 5)
│   ├── hooks/                   ← ⚠️ NOT YET BUILT (Phase 4)
│   │   ├── useSessionWebSocket.js ← manages all 4 WS connections
│   │   └── useAudioCapture.js   ← mic → WS streaming
│   └── services/
│       └── api.js               ← REST + WS client (BUILT ✅)
│
├── docs/
│   ├── new_implementation_plan.md   ← Detailed phase-by-phase plan
│   └── archive/TalkSenseAI_New_Plan.md ← Architecture blueprint
│
└── .agent/
    ├── SKILLS.md                ← THIS FILE
    ├── PROJECT_STATUS.md        ← Current build status per phase
    ├── ARCHITECTURE.md          ← Key design decisions & rules
    ├── QUICK_REFERENCE.md       ← Legacy: batch analysis fix guide (v3)
    ├── CHANGELOG_NEGATIVE_DECISIONS.md ← Legacy: decision logic fix
    ├── FINAL_FIX_STRATEGY.md    ← Legacy: frozen signals fix
    ├── FROZEN_SIGNALS_FIX.md    ← Legacy: frozen signals deep dive
    └── FROZEN_SIGNALS_QUICK_REF.md ← Legacy: frozen signals reference
```

---

## 4. Build Status by Phase

| Phase | What | Status |
|-------|------|--------|
| Phase 1 | Real-Time Audio Pipeline | ✅ BUILT |
| Phase 2 | Conversation Engine | ✅ BUILT |
| Phase 3 | Database & Persistence | ⚠️ NOT STARTED |
| Phase 4 | Live React Dashboard | ⚠️ NOT STARTED |
| Phase 5 | Client Memory & Reports | ⚠️ NOT STARTED |
| Phase 6 | Interview Mode | ⚠️ NOT STARTED |

**Next build target: Phase 3 (DB) → Phase 4 (Dashboard).**

---

## 5. WebSocket Architecture

The backend exposes **5 WebSocket endpoints** per session:

| Channel | Endpoint | Direction | Payload |
|---------|----------|-----------|---------|
| Audio input | `/ws/audio/{session_id}` | Client → Server | Binary PCM chunks |
| Transcript | `/ws/transcript/{session_id}` | Server → Client | `{speaker, text, sentiment, start, end}` |
| Metrics | `/ws/metrics/{session_id}` | Server → Client | `{health_score, speaking_ratio, participation, ...}` |
| Alerts | `/ws/alerts/{session_id}` | Server → Client | `{level, message, timestamp}` |
| Status | `/ws/status/{session_id}` | Server → Client | `{status, elapsed_seconds}` |

**Backpressure rule:** If client lags, DROP old `/metrics` updates. NEVER drop `/alerts`.

---

## 6. REST API

```
POST   /sessions              → create session, returns session_id + WS URLs
GET    /sessions/{id}         → get session state
DELETE /sessions/{id}         → end session
GET    /dashboard/{id}        → full conversation snapshot (for reconnect)
POST   /clients               → create client
GET    /clients               → list clients
GET    /clients/{id}          → get client + briefing data
GET    /reports/{session_id}  → post-session report
POST   /auth/register         → JWT auth (deferred)
POST   /auth/login            → JWT auth (deferred)
GET    /auth/me               → JWT auth (deferred)
POST   /analyze               → LEGACY batch mode (keep forever)
GET    /health                → health check
```

---

## 7. Session Lifecycle

```
Created → Connecting → Active → Processing → Completed
                                           → Failed
                                           → Interrupted
                                           → Expired
```

Recovery: session state flushed to DB every 5 seconds.

---

## 8. Audio Contract

```
Format: PCM
Sample rate: 16 kHz
Channels: Mono
Bit depth: 16-bit
Chunk size: 100–250ms
```

Reject anything else immediately at the WebSocket handler.

---

## 9. Conversation Engine Output Schema

```json
{
  "sentiment": "positive",
  "speaking_ratio": "60/40",
  "health_score": 84,
  "alerts": [],
  "participation": { "Speaker 1": 60, "Speaker 2": 40 },
  "filler_words": 3,
  "objections": []
}
```

---

## 10. Scoring Profiles

```json
{
  "meeting":   { "participation": 0.40, "engagement": 0.30, "balance": 0.20, "action_items": 0.10 },
  "sales":     { "objections": 0.35, "sentiment": 0.25, "listening_ratio": 0.20, "signals": 0.20 },
  "interview": { "confidence": 0.35, "fillers": 0.25, "response_quality": 0.25, "pauses": 0.15 }
}
```

---

## 11. Alert System Rules

| Alert | Level | Trigger |
|-------|-------|---------|
| Sentiment crash | 🔴 Critical | Drops 30+ points in 60s |
| Speaking imbalance | 🔴 Critical | One speaker >80% for 2+ min |
| Repeated objections | 🔴 Critical | 3+ objections detected |
| Long silence | 🟡 Warning | >15s silence |
| Excessive fillers | 🟡 Warning | >5 filler words in 60s |
| Reduced engagement | 🟡 Warning | Health score drops below 40 |
| Buying signal | 🔵 Info | Positive buying signal detected |
| Sentiment shift | 🔵 Info | Negative → positive shift |

**Cooldown:** Same alert type suppressed for 30s.  
**Max active:** 3 alerts. Oldest dropped when exceeded.  
**Duplicates:** Suppressed always.

---

## 12. Database Schema (Phase 3 target)

Tables:
- `users` — id, email, password_hash, created_at
- `clients` — id, user_id, name, industry, created_at
- `sessions` — id, client_id, mode, title, started_at, ended_at, duration, status
- `transcript_segments` — id, session_id, speaker_id, start_time, end_time, text, sentiment
- `session_metrics` — id, session_id, metric_name, metric_value
- `analysis_results` — id, session_id, health_score, summary, report_json
- `alerts` — id, session_id, type, severity, message, timestamp
- `client_snapshots` — id, client_id, snapshot_date, summary, sentiment_score

Required indexes: `sessions(client_id)`, `transcript_segments(session_id)`, `alerts(session_id)`, `client_snapshots(client_id)`

DB URL format: `postgresql+asyncpg://postgres:<password>@localhost:5432/talksense`

---

## 13. Frontend Dashboard Layout (Phase 4 target)

```
┌─────────────────────────────────────────────────────┐
│  Top Bar: Mode | Client | Timer | Health Score       │
├──────────────┬──────────────────┬───────────────────┤
│ LEFT         │ CENTER           │ RIGHT             │
│ Live         │ Conversation     │ Alert Feed        │
│ Transcript   │ Intelligence     │                   │
│              │                  │ 🔴 Critical       │
│ Speaker A    │ Sentiment: +72   │ 🟡 Warning        │
│ Speaker B    │ Health: 84       │ 🔵 Info           │
│ Speaker A    │ Talk Ratio: 60/40│                   │
└──────────────┴──────────────────┴───────────────────┘
```

React routes to add (currently only has old routes):
- `/` → HomePage (update CTAs)
- `/start` → SessionStartPage
- `/dashboard/:sessionId` → DashboardPage ← **main product**
- `/upload` → UploadPage (keep)
- `/results` → ResultsPage (keep)
- `/history` → SessionHistoryPage
- `/clients` → ClientsPage
- `/report/:sessionId` → ReportPage

---

## 14. What To Preserve — DO NOT REWRITE

| File | What's locked |
|------|--------------|
| `backend/services/context_analyzer.py` | `compute_meeting_quality_v2()`, `compose_executive_summary_v2()`, `generate_key_insights_v2()` — all 3 locked |
| `backend/services/nlp_engine.py` | Sentiment pipeline, keyword extraction — keep, adapt for streaming |
| `backend/audio/vad.py` | Silero VAD singleton — do not reload |
| `backend/audio/transcriber.py` | Whisper singleton — do not reload |
| `backend/audio/diarizer.py` | Pyannote singleton — do not reload |
| `backend/engine/scoring_profiles.py` | Profile weights — configurable only via JSON, not hardcoded |

---

## 15. Latency Budget

```
Buffer          1000ms
Whisper          700ms
Pyannote         700ms
Assembly          50ms
Analytics        100ms
Network           50ms
Total target:  ~2.5s
```

---

## 16. Environment Setup

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env   # then fill in real values
uvicorn main:app --reload

# Frontend
cd talksense-ui
npm install
npm run dev
```

Key `.env` variables:
- `DATABASE_URL` — PostgreSQL connection string
- `HF_TOKEN` — Hugging Face token for Pyannote
- `WHISPER_MODEL` — small (default) or medium
- `WHISPER_DEVICE` — cuda (default) or cpu
- `PYANNOTE_ENABLED` — true/false

---

## 17. Testing Checkpoints

### Phase 1 (Audio Pipeline) — VERIFY STILL WORKS
- `uvicorn main:app --reload` starts without errors
- `/ws/audio/{session_id}` accepts binary data
- Microphone audio → transcript in terminal within 3s
- VAD suppresses silence

### Phase 3 (DB) — UPCOMING
- `POST /sessions` persists to PostgreSQL
- After session ends, `GET /reports/{session_id}` returns full report

### Phase 4 (Dashboard) — UPCOMING
- Dashboard opens, mic permission works
- Left panel: live transcript with speaker labels
- Center panel: real-time metrics
- Right panel: alerts as they fire
- 3-panel layout is responsive and polished

---

## 18. Legacy Files (Batch Mode — DO NOT DELETE)

These files power the old `/analyze` endpoint and `UploadPage.jsx`. They stay forever:
- `backend/services/speech_to_text.py` (old openai-whisper batch transcriber)
- `backend/services/context_analyzer.py` (batch analysis functions)
- `talksense-ui/src/pages/UploadPage.jsx`
- `talksense-ui/src/pages/ResultsPage.jsx`
- `talksense-ui/src/components/TranscriptLive.jsx` (prototype live view)
