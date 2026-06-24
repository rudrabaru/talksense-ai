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
- [x] `evaluate_analytics.py` mock speaker attribution values — REPLACED with real computation (2026-06-23)
- [x] `latest_metrics.json` stale mock data — CLEARED (2026-06-23)

---

## Post-Session Speaker Attribution Metrics (Recovery Sprint 2026-06-23)

- **Status**: NOT Production Ready
- **Mock Data**: ELIMINATED. `evaluate_analytics.py` now uses real computation. `latest_metrics.json` cleared.
- **Best Config**: `num_speakers=2` (tested 17 configurations via parameter sweep)
- **WAV Truncation Bug**: Fixed. `AudioBuffer` timeline now perfectly synced.
- **Phantom Speaker Bug**: Fixed via `num_speakers=2` constraint.
- **Evaluation Harness**: `speaker_recovery_harness.py` (single-command reproducible evaluation)
- **Live Diarization**: BROKEN (F1=0.429, SCDR=0.0%, 1 speaker detected out of 2)
- **Post-Session Diarization**: Best measured: F1=0.667, SCDR=33.3%, Accuracy=75.0%
- **Clustering Threshold**: Has ZERO effect with `num_speakers=2` (tested 0.3-0.9, all identical)
- **Failure Pattern**: 2 short Speaker B utterances (2.2s, 1.8s) consistently misattributed to A
- **Gap to Threshold**: F1 gap = 0.083, SCDR gap = 36.7pp
- **Path Forward**: Test with longer audio (real meetings are 2-30+ min, not 32s), or add post-processing turn-taking heuristic

---

## Benchmark Suite (2026-06-24, v2 — human-reviewed GT)

- **Dataset**: 10 samples across 4 categories (2_speaker, 3_speaker, noisy, long_form)
- **Total Audio**: 16.1 minutes (32s to 349s per sample)
- **Human-Reviewed**: 8/10 samples, 19 segment corrections applied
- **Contamination**: ELIMINATED for 8/10 samples (2 remaining: business_meeting, pitch_competition_long)
- **Honest Metrics**: Avg F1=0.832, Avg Accuracy=86.1%, Avg SCDR=68.0%
- **Verdict**: NOT PRODUCTION READY — SCDR fails by 2.0pp (68.0% vs 70.0% threshold)
- **Contamination Impact**: Previous metrics were inflated by 14-21% (F1: 0.952→0.832, SCDR: 82.3%→68.0%)
- **Passing**: 5/10 samples (sales_good, meeting_clear, business_meeting, business_english_long, pitch_competition_long)
- **Failing**: 5/10 samples (meeting_short, sales_meeting, sales_ambiguous, meeting_messy, sales_bad)
- **Key Finding**: Long audio (>2 min) consistently passes. Short noisy audio (<45s) consistently fails.
- **Commands**: `python backend/run_full_benchmark.py` (benchmark), `python annotate_ground_truth.py --status` (review status)

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

---

## Objection Handling Quality Analysis (Implementation Complete)

**Implementation Summary**:
- Implemented `backend/services/objection_handler.py` with the 4-tier scoring logic (IGNORED, ACKNOWLEDGED, ADDRESSED, RESOLVED).
- Integrated `analyze_objection_handling` into `post_session_diarizer.py` to run sequentially after `classify_roles`.

**Final Status**:
- **COMPLETED**. Pipeline calculates objection handling scores and persists them. However, accuracy depends on speaker attribution quality which is currently below threshold.

---

## Analytics Accuracy Audit (Completed)

**Component Accuracy Ranking**:
1. **Speaker Attribution** — Live: F1=0.429 (BROKEN), Post-session: F1=0.667 (below threshold)
2. **Buying Signals** (~40% - Keyword-based, high false positives)
3. **Objections** (~30% - Keyword-based, easily triggered by Sales Rep)
4. **Role Classification** (~25% - Extremely brittle static keywords)
5. **Objection Handling** (~10% - Cascading failures due to dependence on all of the above)

---

## Current Goal

SCDR misses by 2.0pp (68.0% vs 70.0%). To pass:
1. Implement post-processing turn-taking heuristic (if segment < 3s between same-speaker segments, reassign)
2. Review remaining 2 unreviewed GT samples (business_meeting, pitch_competition_long)
3. Test with more audio > 2 min (where Pyannote consistently achieves F1=1.000)
4. Only proceed to Week 4 features after honest benchmark passes all thresholds
