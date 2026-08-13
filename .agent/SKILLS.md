# TalkSense AI — Agent Skills Reference

> **Read this file before touching any code in this repo.**
> It is the single source of truth for architecture, conventions, and build status.

---

## 1. What Is This Project?

TalkSense AI is an **AI-Powered Conversation Intelligence Platform** that analyzes conversations in real-time and delivers actionable insights before the conversation ends.

- **NOT** a transcription tool. **NOT** a meeting recorder. **NOT** a report generator.
- Those are supporting capabilities. **The dashboard IS the product.**
- Core value: understand conversations while they happen → alerts, metrics, history.

---

## 2. Tech Stack

| Layer         | Technology                              |
|---------------|-----------------------------------------|
| Backend       | Python 3.10+, FastAPI, uvicorn          |
| Frontend      | React 19 (Vite), Tailwind CSS 3        |
| Database      | PostgreSQL 16+ on localhost:5432        |
| Migrations    | Alembic (`alembic upgrade head`)        |
| Transcription | Faster-Whisper `small`, int8, CUDA     |
| Sentiment     | `tabularisai/multilingual-sentiment-analysis` (HuggingFace transformers) |
| VAD           | Silero VAD (CPU, lightweight)           |
| Post-Session  | Google Gemini 1.5 Flash                 |
| GPU           | RTX 3050 Laptop, 4GB VRAM (dev target) |
| PyTorch       | CUDA 12.x build                        |
| Auth          | JWT for WebSocket subscription channels only |

> **IMPORTANT:** Pyannote speaker diarization is NOT in the production pipeline. It exists only in `experimental/diart/`. The production system uses Gemini for post-session speaker attribution.

---

## 3. Project Directory Map

```
talksense-ai/
├── backend/
│   ├── main.py                  ← FastAPI app entry point
│   ├── requirements.txt         ← Python deps
│   ├── .env.example             ← Copy to .env and fill in
│   ├── alembic.ini              ← Alembic migration config
│   ├── alembic/                 ← Migration scripts (1 baseline)
│   ├── core/
│   │   ├── config.py            ← Pydantic-settings config (env vars)
│   │   └── security.py          ← JWT token create/verify
│   ├── audio/                   ← Real-time audio pipeline
│   │   ├── vad.py               ← Silero VAD wrapper
│   │   ├── buffer.py            ← Audio accumulation buffer
│   │   ├── transcriber.py       ← Faster-Whisper transcription service
│   │   └── gpu_manager.py       ← GPU concurrency management
│   ├── engine/                  ← Conversation intelligence
│   │   ├── conversation_engine.py ← Heart of the product
│   │   ├── scoring_profiles.py  ← Mode-specific scoring weights
│   │   └── alert_engine.py      ← Real-time alert generation
│   ├── ws/                      ← WebSocket layer
│   │   ├── audio_handler.py     ← /ws/audio/{session_id} endpoint
│   │   ├── session_manager.py   ← Session state machine + background flusher
│   │   ├── broadcast.py         ← WebSocket broadcaster (4 channels)
│   │   └── subscriptions.py     ← /ws/{channel}/{session_id} (JWT-protected)
│   ├── db/                      ← Database layer (COMPLETE)
│   │   ├── models.py            ← SQLAlchemy ORM models (8 tables)
│   │   ├── database.py          ← Async engine setup
│   │   └── crud.py              ← CRUD operations
│   ├── services/
│   │   ├── context_analyzer.py  ← Analytics (LOCKED — DO NOT REWRITE)
│   │   ├── nlp_engine.py        ← NLP enrichment (sentiment + keywords)
│   │   ├── speech_to_text.py    ← Legacy Whisper batch transcriber
│   │   ├── post_session_pipeline.py ← Post-session AI orchestrator
│   │   ├── llm_engine.py        ← Gemini API wrapper
│   │   ├── response_validator.py ← LLM output validation
│   │   ├── prompt_loader.py     ← Versioned prompt bundle loader
│   │   ├── client_memory.py     ← Client snapshot aggregation
│   │   ├── comparison.py        ← Session comparison logic
│   │   ├── objection_handler.py ← Objection analysis (CI-tested)
│   │   └── transcript_builder.py ← Transcript formatting (CI-tested)
│   ├── config/                  ← Static configuration
│   │   └── keywords.json        ← Detection keywords
│   ├── prompts/                 ← Versioned Gemini prompt bundles
│   └── tests/                   ← Pytest suite
│
├── talksense-ui/src/
│   ├── App.jsx                  ← Routing definition
│   ├── index.css                ← Design system CSS (Tailwind directives)
│   ├── pages/
│   │   ├── HomePage.jsx         ← Landing page + session creation
│   │   ├── DashboardPage.jsx    ← MAIN PRODUCT — live dashboard
│   │   ├── UploadPage.jsx       ← Audio file upload (batch mode)
│   │   ├── ResultsPage.jsx      ← Batch results display
│   │   ├── SessionsPage.jsx     ← Session history
│   │   ├── ComparisonPage.jsx   ← Session comparison
│   │   ├── SystemAudioTester.jsx ← Audio device testing
│   │   └── NotFoundPage.jsx     ← 404 handler
│   ├── components/
│   │   └── dashboard/           ← Live dashboard panels
│   ├── hooks/
│   │   └── useSessionWebSocket.js ← 4-channel WS with backoff
│   ├── audio/                   ← Audio source management
│   └── services/
│       └── api.js               ← REST + WS client
│
├── experimental/                ← Isolated experiments (NOT production)
├── scripts/                     ← Development utility scripts
├── docs/                        ← Setup guides, archives
└── .github/workflows/           ← CI pipelines (4 workflows)
```

---

## 4. Build Status by Phase

| Phase | What | Status |
|-------|------|--------|
| Phase 1 | Real-Time Audio Pipeline | ✅ COMPLETE |
| Phase 2 | Conversation Engine | ✅ COMPLETE |
| Phase 3 | Database & Persistence | ✅ COMPLETE |
| Phase 4 | Live React Dashboard | ✅ COMPLETE |
| Phase 5 | Client Memory & Reports | ✅ COMPLETE |
| Phase 6 | Interview Mode | ⚠️ SKELETON (metrics hardcoded at 50) |

---

## 5. WebSocket Architecture

The backend exposes **5 WebSocket endpoints** per session:

| Channel | Endpoint | Direction | Auth | Payload |
|---------|----------|-----------|------|---------|
| Audio input | `/ws/audio/{session_id}` | Client → Server | ❌ None | Binary PCM chunks |
| Transcript | `/ws/transcript/{session_id}?token=JWT` | Server → Client | ✅ JWT | `{speaker, text, sentiment, start, end}` |
| Metrics | `/ws/metrics/{session_id}?token=JWT` | Server → Client | ✅ JWT | `{health_score, speaking_ratio, ...}` |
| Alerts | `/ws/alerts/{session_id}?token=JWT` | Server → Client | ✅ JWT | `{level, message, timestamp}` |
| Status | `/ws/status/{session_id}?token=JWT` | Server → Client | ✅ JWT | `{status, elapsed_seconds}` |

**Backpressure rule:** If client lags, DROP old `/metrics` updates. NEVER drop `/alerts`.

---

## 6. REST API

```
GET    /health                → health check
POST   /sessions              → create session (returns session_id + ws_token + WS URLs)
GET    /sessions              → list all sessions
GET    /sessions/{id}         → get session state
DELETE /sessions/{id}         → end session
GET    /sessions/compare      → compare sessions
GET    /sessions/{id}/audio   → get session audio
GET    /dashboard/{id}        → full conversation snapshot (reconnect)
POST   /clients               → create client
GET    /clients               → list clients
GET    /clients/{id}          → get client details
POST   /analyze               → LEGACY batch mode (keep forever)
```

**Auth status:** ALL REST endpoints are UNAUTHENTICATED. No auth middleware exists.

**Routes that DO NOT EXIST:** `/auth/register`, `/auth/login`, `/auth/me`, `/reports/{session_id}`

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

## 9. Scoring Profiles

```json
{
  "meeting":   { "participation": 0.40, "engagement": 0.30, "balance": 0.20, "action_items": 0.10 },
  "sales":     { "objections": 0.35, "sentiment": 0.25, "listening_ratio": 0.20, "signals": 0.20 },
  "interview": { "confidence": 0.35, "fillers": 0.25, "response_quality": 0.25, "pauses": 0.15 }
}
```

---

## 10. Alert System Rules

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

## 11. Database Schema

8 tables managed by Alembic (baseline migration: `dc184fe69e15`):
- `users` — id, email, password_hash, created_at
- `clients` — id, user_id, name, industry, created_at
- `sessions` — id, client_id, mode, title, started_at, ended_at, duration, status
- `transcript_segments` — id, session_id, speaker_id, start_time, end_time, text, sentiment
- `session_metrics` — id, session_id, metric_name, metric_value
- `analysis_results` — id, session_id, health_score, summary, report_json
- `alerts` — id, session_id, type, severity, message, timestamp
- `client_snapshots` — id, client_id, snapshot_date, summary, sentiment_score

---

## 12. What To Preserve — DO NOT REWRITE

| File | What's locked |
|------|--------------|
| `backend/services/context_analyzer.py` | `compute_meeting_quality_v2()`, `compose_executive_summary_v2()`, `generate_key_insights_v2()` — all 3 locked |
| `backend/services/nlp_engine.py` | Sentiment pipeline, keyword extraction |
| `backend/audio/vad.py` | Silero VAD singleton — do not reload |
| `backend/audio/transcriber.py` | Whisper singleton — do not reload |
| `backend/engine/scoring_profiles.py` | Profile weights — configurable only via JSON, not hardcoded |

---

## 13. Environment Setup

```bash
# Backend
cd backend
python -m venv venv
venv\Scripts\activate
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
copy .env.example .env   # then fill in real values
alembic upgrade head     # create database tables
uvicorn main:app --reload

# Frontend
cd talksense-ui
npm ci
npm run dev
```

Key `.env` variables:
- `DATABASE_URL` — PostgreSQL connection string
- `GEMINI_API_KEY` — Google AI Studio API key (for post-session AI)
- `ENABLE_POST_SESSION_AI` — true/false
- `WHISPER_MODEL` — small (default) or medium
- `WHISPER_DEVICE` — cuda (default) or cpu
- `JWT_SECRET_KEY` — random hex string for WS token signing
- `HF_TOKEN` — optional; Hugging Face token for experimental Pyannote usage only

---

## 14. Legacy Files (Batch Mode — DO NOT DELETE)

These files power the old `/analyze` endpoint and `UploadPage.jsx`. They stay forever:
- `backend/services/speech_to_text.py` (old Whisper batch transcriber)
- `backend/services/context_analyzer.py` (batch analysis functions)
- `talksense-ui/src/pages/UploadPage.jsx`
- `talksense-ui/src/pages/ResultsPage.jsx`
