# TalkSense AI - Project Context

## Project Overview
TalkSense AI is an **offline-first conversation intelligence platform** designed to analyze meeting recordings and sales calls. It provides real-time and post-session insights using local AI models (Speech-to-Text and NLP enrichment) combined with a rule-based context intelligence layer. It maintains data privacy by running completely offline and without cloud API dependencies.

## Tech Stack
**Backend:**
- **Framework:** FastAPI (Python 3.10)
- **Database:** SQLAlchemy 2.0 (async ORM) with PostgreSQL (JSONB columns)
- **AI Models:** 
  - *VAD:* Silero VAD
  - *STT:* faster-whisper
  - *Diarization:* Pyannote 3.1
  - *Sentiment:* `tabularisai/multilingual-sentiment-analysis` (Hugging Face)
- **Real-Time:** WebSockets for live audio ingestion and telemetry broadcasting.
- **Server:** Uvicorn

**Frontend:**
- **Framework:** React 19
- **Build Tool:** Vite (Rolldown)
- **Styling:** Tailwind CSS
- **Features:** Custom AudioWorklet (`PCMProcessor`) for live audio capture and multi-channel WebSockets for dashboards.

## System Architecture
1. **Real-Time Audio Pipeline:**
   - Inbound WebSocket stream captures binary PCM audio.
   - Live Voice Activity Detection (VAD) and fast speech-to-text.
   - Outbound WebSocket channels broadcast live transcript, metrics, alerts, and status.
2. **Context Analyzer:**
   - **Meeting Mode:** Detects decisions, action items, blockers, and calculates a Meeting Quality Score.
   - **Sales Mode:** Tracks objections, buying signals, commitments, and calculates a Sales Quality Score.
3. **Post-Session Diarization:**
   - Pyannote aligns and attributes speakers to transcript segments.
   - Role classification heuristics (or LLM via Gemini) to label speakers as `sales_rep` or `customer`.
   - Advanced analytics for objection handling response time and resolution.

## Current State & Recent Progress
- **Architecture Frozen:** Word-level Pyannote attribution enabled and 5-word smoothing permanently removed (Variant C selected).
- **Core Metrics (v4 Canonical):** **91.3% Speaker Accuracy**, **0.925 Macro F1**, **48.4% Legacy Boundary Recall @ 500ms**.
- **Diagnostics Frameworks:** Command-line tools (e.g. `run_full_benchmark.py`) correctly prove that the 48.4% Boundary Recall is driven entirely by sub-500ms transition tolerances rather than speaker misattributions.
- **Bug Fixes:** Resolved the "WAV Truncation Bug" ensuring live audio chunks map perfectly to the on-disk WAV file. Also mitigated the "Phantom Speaker" Pyannote clustering bug.
- **Advanced Sales Analytics:** Added automated objection handling quality scoring based on rep response times and customer follow-up signals.
- **UI Enhancements:** The frontend now features live panels for scrolling transcripts, metric visualizers (Talk Timeline, Objection Scorecard), and system alerts.

## Active Environment
Currently, both the backend API and frontend development server are actively running:
- **Backend:** `uvicorn backend.main:app --reload`
- **Frontend:** `npm run dev`

## Next Steps / Roadmap
- Improve Role Classification and Objection Handling analytics accuracy.
- Transition from static keyword matching to LLM Intent Recognition for advanced semantic classification.
- Build UI for Sales Rep Leaderboards and aggregate metrics.
