# TalkSense AI v4 — Implementation Plan

## Overview

Build TalkSense AI from its current "batch upload analyzer" state into a fully real-time, WebSocket-driven **Conversation Intelligence Platform** as specified in [TalkSenseAI_New_Plan.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/docs/archive/TalkSenseAI_New_Plan.md).

This is a **summer project** — built to production quality with a proper architecture, not a hackathon MVP.

The existing `context_analyzer.py` and `nlp_engine.py` contain valuable detection logic (sentiment, objection detection, action items, scoring) that will be **preserved and adapted** into the new real-time engine rather than rewritten from scratch.

---

## ✅ Locked Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| **Project scope** | Summer project | Full production-quality build, no shortcuts |
| **Database** | **PostgreSQL 17.5** | Already installed and running on port 5432 |
| **GPU** | **RTX 3050 Laptop, 4GB VRAM** | CUDA capable, tight VRAM budget |
| **PyTorch** | Replace CPU build with CUDA 12.x build | Current install is `2.9.1+cpu` — needs reinstall |
| **Transcription** | `faster-whisper` **small** or **medium**, `int8` on GPU | Saves VRAM; medium.en for English, small for multilingual |
| **Diarization** | Pyannote `speaker-diarization-3.1` with HF token | Run sequentially with Whisper to stay within 4GB |
| **Auth** | **JWT + bcrypt, minimal** | Login/register/me — no RBAC |
| **Modes V1** | **Meeting + Sales** | Interview in Phase 6 |
| **Sentiment** | `tabularisai/multilingual-sentiment-analysis` | Already integrated, keep it |

> [!WARNING]
> **VRAM Budget (RTX 3050, 4GB):** Running Whisper medium + Pyannote simultaneously would exceed 4GB. Strategy: run Pyannote on a slightly delayed rolling window while Whisper has the GPU. Use `int8` quantization on Whisper to reduce footprint. GPU safety fallback: if VRAM < 500MB, pause Pyannote and assign speakers by turn-boundary heuristic.

> [!IMPORTANT]
> **First step before any code**: Reinstall PyTorch with CUDA support. Current install `2.9.1+cpu` has no CUDA. We'll reinstall with the correct CUDA 12.x wheel.

> [!NOTE]
> **What we keep from the existing codebase**: The analysis logic in `context_analyzer.py` (signal detection, meeting quality, sales quality scoring) and `nlp_engine.py` (sentiment, keyword extraction) is solid. We will refactor it to work per-segment in real time rather than batch post-processing.

---

## Proposed Changes

---

### Phase 1 — Real-Time Audio Pipeline (Backend)

This is the foundation. Everything else depends on this.

---

#### [MODIFY] [requirements.txt](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/requirements.txt)

Replace `openai-whisper` with `faster-whisper`. Add WebSocket, VAD, and DB deps.

```
fastapi
uvicorn[standard]
python-multipart
faster-whisper
transformers
torch
torchaudio
scipy
silero-vad
websockets
sqlalchemy
aiosqlite          # or psycopg2 for PostgreSQL
pyannote.audio     # optional, gated model
```

---

#### [NEW] [backend/audio/vad.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/audio/vad.py)

Silero VAD wrapper.

- Loads Silero VAD model on startup (CPU, lightweight)
- `is_speech(chunk: bytes) -> bool` — returns True if chunk contains speech
- Buffers 100–250ms PCM chunks
- Suppresses silence before sending to Whisper

---

#### [NEW] [backend/audio/buffer.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/audio/buffer.py)

Audio accumulation buffer.

- Accumulates VAD-approved chunks
- Flushes to Whisper when buffer reaches ~1000ms of speech
- Handles partial flush on sentence boundaries

---

#### [NEW] [backend/audio/transcriber.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/audio/transcriber.py)

Faster Whisper transcription service.

- Loads model once at startup (`medium`, GPU/CPU, `float16`/`int8`)
- `transcribe(audio_bytes: bytes) -> list[Segment]` — returns timestamped segments
- Each segment: `{ start, end, text, speaker (initially null) }`
- Runs in a `ThreadPoolExecutor` (non-blocking)

---

#### [NEW] [backend/audio/diarizer.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/audio/diarizer.py)

Pyannote speaker diarization (optional, falls back gracefully).

- Loads `pyannote/speaker-diarization-3.1` if HF token available
- Sliding window: 4s window, 1s stride
- Assigns `speaker_id` to each segment by time overlap
- If Pyannote unavailable: assigns speakers based on segment boundaries (alternating)

---

#### [NEW] [backend/ws/session_manager.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/ws/session_manager.py)

Manages all active WebSocket sessions.

```python
sessions: dict[session_id, SessionState]
```

Handles:
- Session creation, state transitions (Created → Connecting → Active → Processing → Completed)
- Per-session audio buffer and pipeline state
- Cleanup on disconnect

---

#### [NEW] [backend/ws/audio_handler.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/ws/audio_handler.py)

WebSocket endpoint `/ws/audio/{session_id}`.

- Accepts binary PCM audio chunks from the browser
- Validates format (16kHz, mono, 16-bit)
- Passes through VAD → Buffer → Transcriber pipeline
- On each transcript segment: fires Conversation Engine → broadcasts to client

**Backpressure**: Drops old metric updates if client queue is full. Never queues indefinitely.

---

#### [MODIFY] [backend/main.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/main.py)

Keep existing `POST /analyze` (batch mode) for backward compatibility. Add:

- WebSocket router mount
- Startup event: model warmup (Whisper, Sentiment, VAD)
- New REST endpoints per plan:
  - `POST /sessions` — create session
  - `GET /sessions/{id}` — get session state
  - `DELETE /sessions/{id}` — end session
  - `POST /clients`, `GET /clients`, `GET /clients/{id}`
  - `GET /reports/{session_id}`
  - `GET /dashboard/{session_id}`

---

### Phase 2 — Conversation Engine (Backend)

Adapts existing analysis logic to work in real time, per incoming segment.

---

#### [NEW] [backend/engine/conversation_engine.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/engine/conversation_engine.py)

The heart of the product. Processes each new transcript segment and updates session state.

**Inputs per call:**
- New segment(s) from Whisper
- Current session state (running metrics)
- Active mode (meeting / sales / interview)

**Outputs:**
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

**Reuses from existing code:**
- `aggregate_sentiment()` from `context_analyzer.py`
- `NLPEngine.enrich_transcript()` adapted for per-segment streaming
- `assess_sales_signals()` and `compute_sales_quality()` (running window)
- `compute_meeting_quality_v2()` (running window)

---

#### [NEW] [backend/engine/scoring_profiles.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/engine/scoring_profiles.py)

Scoring profile weights loaded from config (not hardcoded).

```json
{
  "meeting":   { "participation": 0.40, "engagement": 0.30, "balance": 0.20, "action_items": 0.10 },
  "sales":     { "objections": 0.35, "sentiment": 0.25, "listening_ratio": 0.20, "signals": 0.20 },
  "interview": { "confidence": 0.35, "fillers": 0.25, "response_quality": 0.25, "pauses": 0.15 }
}
```

`compute_health_score(mode, metrics) -> int` — returns 0–100.

---

#### [NEW] [backend/engine/alert_engine.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/engine/alert_engine.py)

Real-time alert generation.

- Evaluates metrics after each segment update
- **Alert levels**: Critical (red), Warning (yellow), Info (blue)
- **Cooldown**: Same alert type suppressed for 30 seconds
- **Max active**: 3 alerts at a time (oldest dropped when exceeded)
- **Duplicate suppression**: Same message not repeated

Alert triggers:
| Alert | Level | Condition |
|---|---|---|
| Sentiment crash | Critical | Sentiment drops 30+ points in 60s |
| Speaking imbalance | Critical | One speaker > 80% for 2+ min |
| Repeated objections | Critical | 3+ objections detected |
| Long silence | Warning | >15s silence detected |
| Excessive fillers | Warning | >5 filler words in 60s |
| Reduced engagement | Warning | Health score drops below 40 |
| Buying signal | Info | Positive buying signal detected |
| Sentiment shift | Info | Sentiment moves from negative to positive |

---

#### [NEW] [backend/ws/broadcast.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/ws/broadcast.py)

WebSocket broadcaster. Sends updates over 4 channels:

- `/transcript` — new segment with speaker + sentiment
- `/metrics` — updated health score, speaking ratio, participation
- `/alerts` — new alert (with level, message, timestamp)
- `/status` — session state changes

Implements backpressure: if client is lagging, drop old `/metrics` updates, always deliver `/alerts`.

---

### Phase 3 — Database & Persistence (Backend)

---

#### [NEW] [backend/db/models.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/db/models.py)

SQLAlchemy models for all tables in the plan:

- `users` — id, email, password_hash, created_at
- `clients` — id, user_id, name, industry, created_at
- `sessions` — id, client_id, mode, title, started_at, ended_at, duration, status
- `transcript_segments` — id, session_id, speaker_id, start_time, end_time, text, sentiment
- `session_metrics` — id, session_id, metric_name, metric_value
- `analysis_results` — id, session_id, health_score, summary, report_json
- `alerts` — id, session_id, type, severity, message, timestamp
- `client_snapshots` — id, client_id, snapshot_date, summary, sentiment_score

All required indexes applied.

---

#### [NEW] [backend/db/database.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/db/database.py)

SQLAlchemy async engine setup. Configurable for SQLite (default) or PostgreSQL via env var.

---

#### [NEW] [backend/db/crud.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/db/crud.py)

CRUD operations for all models.

---

#### Session Persistence

- Every 5 seconds, flush in-memory session state to DB (transcript segments + metrics)
- On session end: compute final `analysis_results`, update `client_snapshots`
- On crash recovery: restore session from last DB snapshot

---

### Phase 4 — Live React Dashboard (Frontend)

Complete rebuild of the frontend. The existing `HomePage`, `UploadPage`, `ResultsPage` are replaced or supplemented with a live dashboard experience.

---

#### [NEW] [talksense-ui/src/pages/DashboardPage.jsx](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/src/pages/DashboardPage.jsx)

The main product page. 3-panel layout:

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

WebSocket client connects to all 4 channels on mount.

---

#### [NEW] [talksense-ui/src/hooks/useSessionWebSocket.js](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/src/hooks/useSessionWebSocket.js)

Custom React hook managing all 4 WebSocket connections for a session.

- Auto-reconnect on drop
- Exposes: `transcript`, `metrics`, `alerts`, `status`
- Handles backpressure gracefully (only latest metrics state kept)

---

#### [NEW] [talksense-ui/src/hooks/useAudioCapture.js](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/src/hooks/useAudioCapture.js)

Browser microphone → WebSocket streaming.

- Uses `MediaRecorder` API (or `AudioWorklet` for raw PCM)
- Converts to PCM 16kHz mono 16-bit
- Streams 250ms chunks to `/ws/audio/{session_id}`
- Handles mic permission denial gracefully

---

#### [NEW] [talksense-ui/src/components/dashboard/TranscriptPanel.jsx](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/src/components/dashboard/TranscriptPanel.jsx)

Live scrolling transcript.
- Color-coded by speaker
- Sentiment badge per segment (🟢 🔴 ⚪)
- Auto-scrolls to latest
- Filler words highlighted

---

#### [NEW] [talksense-ui/src/components/dashboard/IntelligencePanel.jsx](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/src/components/dashboard/IntelligencePanel.jsx)

Center panel — live conversation metrics.
- Animated Health Score gauge (0–100, color-coded)
- Sentiment trend sparkline
- Speaking ratio bar (Speaker A vs B)
- Participation donut chart
- Mode-specific cards (objections for Sales, fillers for Interview)

---

#### [NEW] [talksense-ui/src/components/dashboard/AlertPanel.jsx](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/src/components/dashboard/AlertPanel.jsx)

Right panel — real-time alert feed.
- Sorted by severity (Critical first)
- Toast-style entry animations
- Alert age indicator
- Max 3 visible, older ones fade out

---

#### [NEW] [talksense-ui/src/pages/SessionStartPage.jsx](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/src/pages/SessionStartPage.jsx)

Pre-session setup flow:
1. Select mode (Meeting / Sales / Interview)
2. Select or create client
3. Shows **Client Briefing Card** (if returning client)
4. Start button → creates session → goes to DashboardPage

---

#### [NEW] [talksense-ui/src/components/ClientBriefingCard.jsx](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/src/components/ClientBriefingCard.jsx)

Displays client memory before session:
```
Client: ABC Corp  |  6 past meetings
Sentiment trend: Improving ↗
Common objections: Pricing, Integration
Last session: 2 weeks ago
```

---

#### [MODIFY] [talksense-ui/src/App.jsx](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/src/App.jsx)

Add new routes:
- `/` → HomePage (keep, update with new CTAs)
- `/start` → SessionStartPage
- `/dashboard/:sessionId` → DashboardPage
- `/upload` → UploadPage (keep for batch mode)
- `/results` → ResultsPage (keep for batch results)
- `/history` → SessionHistoryPage (new)
- `/clients` → ClientsPage (new)
- `/report/:sessionId` → ReportPage (new)

---

### Phase 5 — Client Memory & Reports (Backend + Frontend)

---

#### [NEW] [backend/services/memory_service.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/services/memory_service.py)

Client memory management.

- `get_client_briefing(client_id)` → returns past meetings, objections, sentiment trend
- `update_client_snapshot(client_id, session_results)` → updates snapshot after session
- Queries `client_snapshots` + `analysis_results` tables

---

#### [NEW] [backend/services/report_service.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/services/report_service.py)

Post-session report generation.
- Compiles full transcript, metrics, alerts, health score timeline
- Generates executive summary using existing `compose_executive_summary_v2()`
- Stores in `analysis_results` table

---

#### [NEW] [talksense-ui/src/pages/ReportPage.jsx](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/src/pages/ReportPage.jsx)

Post-session report view.
- Health score with breakdown
- Full transcript with sentiment
- Key decisions / action items / objections
- Client memory update preview

---

### Phase 6 — Interview Mode

---

#### [MODIFY] [backend/engine/conversation_engine.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/engine/conversation_engine.py)

Add Interview mode metrics:
- Confidence score (proxy: speech rate, filler words, pause duration)
- Filler word detection (um, uh, like, you know, basically)
- Pause detection (>2s silence within speaker turn)
- Response quality (length and vocabulary diversity)

---

## Build Order Summary

```
Phase 1 — Real-Time Audio Pipeline    ← Unlocks everything
Phase 2 — Conversation Engine         ← Core product value
Phase 3 — Database                    ← Enables persistence
Phase 4 — Live Dashboard              ← Product face / demo
Phase 5 — Client Memory + Reports     ← Differentiator
Phase 6 — Interview Mode              ← Third mode
```

**Auth (JWT/bcrypt)**: Deferred unless needed. Session will be keyed by session_id for hackathon.

---

## File Tree After Implementation

```
backend/
├── main.py                          (modified)
├── requirements.txt                 (modified)
├── audio/
│   ├── vad.py                       (new)
│   ├── buffer.py                    (new)
│   └── transcriber.py               (new)
├── engine/
│   ├── conversation_engine.py       (new)
│   ├── scoring_profiles.py          (new)
│   └── alert_engine.py              (new)
├── ws/
│   ├── audio_handler.py             (new)
│   ├── session_manager.py           (new)
│   └── broadcast.py                 (new)
├── db/
│   ├── models.py                    (new)
│   ├── database.py                  (new)
│   └── crud.py                      (new)
├── services/
│   ├── context_analyzer.py          (kept, adapted)
│   ├── nlp_engine.py                (kept, adapted)
│   ├── speech_to_text.py            (replaced by audio/transcriber.py)
│   ├── memory_service.py            (new)
│   └── report_service.py            (new)
├── config/
│   └── keywords.json                (kept)
└── utils/
    └── config_loader.py             (kept)

talksense-ui/src/
├── App.jsx                          (modified - new routes)
├── pages/
│   ├── HomePage.jsx                 (kept, minor updates)
│   ├── SessionStartPage.jsx         (new)
│   ├── DashboardPage.jsx            (new - main product)
│   ├── ReportPage.jsx               (new)
│   ├── SessionHistoryPage.jsx       (new)
│   ├── ClientsPage.jsx              (new)
│   ├── UploadPage.jsx               (kept - batch mode)
│   └── ResultsPage.jsx              (kept - batch results)
├── components/
│   ├── dashboard/
│   │   ├── TranscriptPanel.jsx      (new)
│   │   ├── IntelligencePanel.jsx    (new)
│   │   └── AlertPanel.jsx           (new)
│   ├── ClientBriefingCard.jsx       (new)
│   ├── InsightCard.jsx              (kept)
│   ├── ModeSelector.jsx             (kept)
│   ├── SentimentBadge.jsx           (kept)
│   └── TranscriptBlock.jsx          (kept)
├── hooks/
│   ├── useSessionWebSocket.js       (new)
│   └── useAudioCapture.js           (new)
└── services/
    └── api.js                       (new - REST + WS client)
```

---

## Verification Plan

### Phase 1 Checkpoint
- `uvicorn main:app --reload` starts without errors
- WebSocket `/ws/audio/{session_id}` accepts binary data
- Microphone audio → transcript appears in terminal logs within 3s
- VAD suppresses silence (no empty transcriptions)

### Phase 2 Checkpoint
- Health score updates in real time as transcript grows
- Alerts fire correctly (test with pre-recorded audio)
- Scoring profiles produce different scores for same transcript in different modes

### Phase 3 Checkpoint
- Session created via `POST /sessions` is persisted in DB
- After session ends, `GET /reports/{session_id}` returns full report
- Client briefing card populates from DB for returning client

### Phase 4 Checkpoint
- Dashboard opens, mic permission granted, audio streams
- Left panel shows live transcript with speaker labels
- Center panel updates metrics in real time
- Right panel shows alerts as they fire
- 3-panel layout is responsive and visually polished

### Phase 5 Checkpoint
- Second session with same client shows Client Briefing Card
- Report page shows full post-session breakdown

### End-to-End
Run 2 minutes of Meeting mode audio → verify:
- Transcript accuracy
- Health score reflects conversation quality
- At least 1 alert fires
- Report is generated
- Client memory updated
