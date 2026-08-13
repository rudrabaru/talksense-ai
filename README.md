# TalkSense AI

**Real-Time Conversation Intelligence Platform for Meetings and Sales Calls**

---

## Overview

TalkSense AI is a full-stack conversation intelligence platform that analyzes live meetings and sales calls to extract actionable insights in real time. It combines **real-time streaming analytics** (using open-source models for transcription, VAD, and NLP) with an **asynchronous Post-Session AI Pipeline** (using Google Gemini) to deliver deep, structured insights and speaker-attributed summaries.

### Problem Statement

Teams and sales professionals struggle to extract actionable insights from live conversations. Existing solutions either:
- Are strictly offline, missing the opportunity to coach reps during the call.
- Lack transparency in how their "AI" determines deal health or meeting quality.
- Suffer from high latency when trying to provide live metrics.

TalkSense AI addresses this by providing **mode-aware real-time analysis** coupled with powerful **post-session LLM summarization**, ensuring both immediate coaching and deep historical insight.

---

## Key Features

### 🎙️ Real-Time Intelligence (Live)
- **Live Transcription**: Sub-second speech-to-text using local Faster-Whisper (small model, int8, CUDA).
- **Voice Activity Detection**: Silero VAD filters silence to optimize GPU compute.
- **Dynamic Scoring**: Live Meeting/Sales Quality scores updated incrementally as you speak.
- **Live Alerts & Coaching**: Real-time detection of buying signals, objections, and blockers pushed directly to the UI.
- **Sentiment Tracking**: High-frequency NLP sentiment analysis plotting the mood of the conversation live.

### 🧠 Post-Session AI Pipeline (Gemini)
- **LLM-Driven Speaker Attribution**: Gemini-powered role classification (Interviewer vs. Candidate, Rep vs. Prospect) applied after the call ends.
- **Executive Summaries**: High-level assessments of deal quality or meeting execution.
- **Objection Handling Strategies**: Post-call generated recommendations for resolving identified concerns.
- **Follow-Up Actions**: Stage-based recommendations extracted with concrete timelines.

---

## System Architecture

TalkSense AI follows a **Hybrid Processing Pipeline** with two distinct intelligence paths:

### 1. Real-Time Engine (Local / FastAPI / WebSockets)

```
Browser Microphone
    ↓  binary PCM (~250ms chunks)
/ws/audio/{session_id}          ← audio_handler.py
    ↓  validated chunks
Silero VAD                      ← vad.py: is_speech() filter
    ↓  speech chunks only
Audio Buffer                    ← buffer.py: accumulate ~1000ms
    ↓  buffered audio
Faster-Whisper                  ← transcriber.py: speech-to-text
    ↓  {start, end, text, words}
NLP + Conversation Engine       ← nlp_engine.py + conversation_engine.py
    ↓  metrics, alerts, state
Broadcast                       ← broadcast.py → /ws/transcript, /ws/metrics, /ws/alerts
    ↓
React Dashboard
```

### 2. Post-Session Pipeline (Cloud LLM)

- Triggered automatically when a session is marked `COMPLETED` (if `ENABLE_POST_SESSION_AI=true`).
- An async worker orchestrates a prompt bundle (schema + instructions) and the full transcript to **Gemini 1.5 Flash**.
- **Outputs**: Pydantic-validated JSON containing speaker role mapping, executive summary, refined action items, and structural metadata.

---

## Tech Stack

### Backend
- **Framework**: FastAPI (async ASGI)
- **Database**: PostgreSQL 16+ (SQLAlchemy 2.x async ORM + Alembic migrations + asyncpg)
- **Speech-to-Text**: Faster-Whisper (`small` model, int8 quantization, CUDA)
- **Voice Activity Detection**: Silero VAD (CPU)
- **NLP / Sentiment**: Hugging Face Transformers (`tabularisai/multilingual-sentiment-analysis`)
- **Generative AI**: Google Gemini 1.5 Flash (`google-genai`) for post-session analysis
- **Real-Time Communication**: WebSockets (5 channels per session)
- **Authentication**: JWT tokens for WebSocket subscription channels

### Frontend
- **Framework**: React 19 + Vite
- **Routing**: React Router DOM 7
- **Styling**: Tailwind CSS 3
- **Audio Capture**: Web Audio API / `AudioSourceManager`
- **Testing**: Playwright (E2E)

---

## Project Structure

```
talksense-ai/
├── backend/
│   ├── main.py                    # FastAPI app entry point + startup lifecycle
│   ├── core/                      # Config (Pydantic Settings) & Security (JWT)
│   ├── db/                        # PostgreSQL models, async CRUD, Alembic migrations
│   ├── audio/                     # Silero VAD, Faster-Whisper, Audio Buffers
│   ├── ws/                        # WebSocket handlers, session manager, broadcast
│   ├── engine/                    # Real-time Conversation & Alert Engine
│   ├── services/                  # NLP engine, post-session pipeline, LLM integration
│   ├── config/                    # Static configuration (keywords.json, scoring profiles)
│   ├── prompts/                   # Versioned prompt bundles for Gemini
│   ├── alembic/                   # Database migration scripts
│   └── tests/                     # Pytest suite (unit + integration)
│
├── talksense-ui/
│   ├── src/
│   │   ├── pages/                 # 8 Views (Dashboard, Upload, Sessions, Results, etc.)
│   │   ├── components/            # Reusable UI (Sidebar, TranscriptPanel, Metrics)
│   │   ├── hooks/                 # WebSocket & Audio capture hooks
│   │   ├── audio/                 # Audio source management (Mic, System, PCM)
│   │   └── services/              # HTTP API client
│   └── tests/                     # Playwright E2E tests
│
├── experimental/                  # Isolated experiments (Diart diarization, benchmarks)
├── scripts/                       # Development utility scripts
├── docs/                          # Setup guides, archives
└── .github/workflows/             # CI pipelines (Backend, Frontend, Integration, QA)
```

---

## Setup & Run Instructions

### Prerequisites
- **Python**: 3.10+
- **Node.js**: 20.x+
- **PostgreSQL**: 16+
- **FFmpeg**: Required by Whisper audio processing
- **NVIDIA GPU** (optional): CUDA-capable GPU for accelerated inference
- **Gemini API Key**: Required for Post-Session AI pipeline

### Backend Setup
1. Create and activate a virtual environment:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\Activate.ps1
   ```
2. Install PyTorch (CUDA or CPU):
   ```bash
   # GPU (NVIDIA):
   pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
   # CPU only:
   pip install torch torchaudio
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Setup environment:
   ```bash
   cp .env.example .env
   # Edit .env with your DB credentials, JWT_SECRET_KEY, and GEMINI_API_KEY
   ```
5. Create database and run migrations:
   ```bash
   psql -U postgres -c "CREATE DATABASE talksense;"
   alembic upgrade head
   ```
6. Start the server:
   ```bash
   uvicorn main:app --reload
   ```

### Frontend Setup
1. Install dependencies:
   ```bash
   cd talksense-ui
   npm ci
   ```
2. Setup environment:
   ```bash
   cp .env.example .env
   # Ensure VITE_API_URL points to your backend (default: http://localhost:8000)
   ```
3. Start dev server:
   ```bash
   npm run dev
   ```

### Verify

- Backend health: `http://localhost:8000/health` → `{"status": "ok", "service": "TalkSense AI", "version": "4.0.0"}`
- API docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`

---

## WebSocket Channels

Each session uses 5 WebSocket channels:

| Channel | Path | Direction | Auth | Purpose |
|---------|------|-----------|------|---------|
| Audio | `/ws/audio/{session_id}` | Client → Server | ❌ Not enforced | Binary PCM audio stream |
| Transcript | `/ws/transcript/{session_id}` | Server → Client | ✅ JWT | Live transcript segments |
| Metrics | `/ws/metrics/{session_id}` | Server → Client | ✅ JWT | Live conversation metrics |
| Alerts | `/ws/alerts/{session_id}` | Server → Client | ✅ JWT | Real-time coaching alerts |
| Status | `/ws/status/{session_id}` | Server → Client | ✅ JWT | Session state changes |

---

## Development & CI/CD

This project enforces strict code quality through 4 GitHub Actions workflows.

### Backend Validation
```bash
cd backend
black --check .             # Formatting
ruff check .                # Linting
pyright                     # Type Checking
pytest tests/ -v            # Unit & Integration Tests
```

### Frontend Validation
```bash
cd talksense-ui
npm run lint                # ESLint
npm run build               # Production Build test
npm run test:e2e            # Playwright E2E tests
```

---

## Environment Variables

See `backend/.env.example` for the full reference. Key variables:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | — | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `JWT_SECRET_KEY` | Recommended | Auto-generated | Secret for signing WebSocket JWT tokens |
| `GEMINI_API_KEY` | For post-session | — | Google Gemini API key |
| `ENABLE_POST_SESSION_AI` | No | `false` | Enable post-session LLM analysis |
| `WHISPER_MODEL` | No | `small` | Faster-Whisper model size |
| `WHISPER_DEVICE` | No | `cuda` | `cuda` or `cpu` |
| `WHISPER_COMPUTE_TYPE` | No | `int8` | Quantization type |
| `ENV` | No | `development` | Environment mode |
| `CORS_ORIGINS` | No | `http://localhost:5173` | Allowed frontend origins |

---

**Built for SCET Breakout Hackathon 2026**
