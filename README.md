# TalkSense AI

**Real-Time Conversation Intelligence Platform for Meetings and Sales Calls**

---

## Overview

TalkSense AI is a full-stack conversation intelligence platform that analyzes meeting recordings and live sales calls to extract actionable insights. It combines **real-time streaming analytics** (using open-source models for transcription and NLP) with an **asynchronous Post-Session AI Pipeline** (using Gemini) to deliver deep, structured insights and speaker-attributed summaries.

### Problem Statement

Teams and sales professionals struggle to extract actionable insights from live conversations and recordings. Existing solutions either:
- Are strictly offline, missing the opportunity to coach reps during the call.
- Lack transparency in how their "AI" determines deal health or meeting quality.
- Suffer from high latency when trying to provide live metrics.

TalkSense AI addresses this by providing **mode-aware real-time analysis** coupled with powerful **post-session LLM summarization**, ensuring both immediate coaching and deep historical insight.

---

## Key Features

### 🎙️ Real-Time Intelligence (Live)
- **Live Transcription**: Sub-second speech-to-text using local Faster-Whisper.
- **Dynamic Scoring**: Live Meeting/Sales Quality scores updated incrementally as you speak.
- **Live Alerts & Coaching**: Real-time detection of buying signals, objections, and blockers pushed directly to the UI.
- **Sentiment Tracking**: High-frequency NLP sentiment analysis plotting the mood of the conversation live.

### 🧠 Post-Session AI Pipeline (Gemini)
- **Speaker Diarization & Attribution**: LLM-driven speaker mapping (Interviewer vs. Candidate, Rep vs. Prospect) applied immediately after the call ends.
- **Executive Summaries**: High-level assessments of deal quality or meeting execution.
- **Objection Handling Strategies**: Post-call generated recommendations for resolving identified concerns.
- **Follow-Up Actions**: Stage-based recommendations extracted with concrete timelines.

---

## System Architecture

TalkSense AI follows a **Hybrid Processing Pipeline**:

### 1. Real-Time Engine (Local / FastAPI / WebSockets)
- **Audio Capture**: Browser MediaRecorder captures audio chunks and sends them via WebSocket.
- **VAD (Voice Activity Detection)**: Silero VAD filters out silence to optimize compute.
- **STT (Speech-to-Text)**: Faster-Whisper (`large-v3`) provides rapid, word-level timestamped transcripts.
- **NLP (Sentiment & Context)**: Hugging Face Transformers perform sentiment analysis while a highly optimized rule-engine (`AlertEngine`, `ConversationEngine`) detects objections and buying signals.
- **Broadcast**: Insights are streamed back to the React UI instantly.

### 2. Post-Session Pipeline (Cloud LLM)
- Triggered automatically when a session is marked `COMPLETED`.
- A resilient, async worker orchestrates a prompt bundle (schema, instructions) and the full transcript to **Gemini**.
- **Outputs**: Pydantic-validated JSON containing speaker mapping, executive summary, refined action items, and structural metadata.

---

## Tech Stack

### Backend
- **Framework**: FastAPI (async ASGI API)
- **Database**: PostgreSQL 16 (SQLAlchemy ORM + Alembic + asyncpg)
- **Speech-to-Text**: Faster Whisper
- **Voice Activity Detection**: Silero VAD
- **NLP Processing**: Hugging Face Transformers (`tabularisai/multilingual-sentiment-analysis`)
- **Generative AI**: Google Gemini (`google-genai`) for post-session analysis
- **Communication**: WebSockets (Real-time data streaming)

### Frontend
- **Framework**: React 19 + Vite
- **Routing**: React Router DOM 7
- **Styling**: Tailwind CSS
- **Audio**: Web Audio API / `AudioSourceManager`
- **Testing**: Playwright (E2E)

---

## Project Structure

Following our comprehensive repository cleanup, the codebase is strictly organized into production runtime and testing:

```
talksense-ai/
├── backend/
│   ├── main.py                    # FastAPI app + startup lifecycle
│   ├── core/                      # Config (Pydantic Settings) & Security (JWT)
│   ├── db/                        # PostgreSQL models, async CRUD, migrations
│   ├── audio/                     # Silero VAD, Faster-Whisper, Audio Buffers
│   ├── ws/                        # WebSocket connection managers & broadcast logic
│   ├── engine/                    # Real-time Conversation & Alert Engine
│   ├── services/                  # Post-session pipeline, LLM integration, NLP
│   ├── config/                    # Static configuration (keywords.json)
│   ├── prompts/                   # Versioned prompt bundles for Gemini
│   ├── evaluation/                # Health checks and threshold evaluations
│   └── tests/                     # Comprehensive Pytest suite
│
├── talksense-ui/
│   ├── src/
│   │   ├── pages/                 # 8 Core Views (Dashboard, Upload, History, etc)
│   │   ├── components/            # Reusable UI (Sidebar, TranscriptPanel, Metrics)
│   │   ├── hooks/                 # WebSockets & Audio capture hooks
│   │   ├── audio/                 # Audio Sources (Microphone, System, PCM)
│   │   └── services/              # HTTP API abstractions
│   └── tests/                     # Playwright E2E tests
│
└── docs/                          # Architecture diagrams, Setup guides, Archives
```

---

## Setup & Run Instructions

### Prerequisites
- **Python**: 3.10+
- **Node.js**: 20.x+
- **PostgreSQL**: 16+
- **FFmpeg**: Required by Whisper
- **Gemini API Key**: Required for Post-Session pipeline

### Backend Setup
1. Create and activate a virtual environment:
   ```bash
   python -m venv backend/venv
   source backend/venv/bin/activate  # On Windows: backend\venv\Scripts\Activate.ps1
   ```
2. Install dependencies:
   ```bash
   pip install -r backend/requirements.txt
   pip install -r backend/requirements-dev.txt
   ```
3. Setup Environment:
   ```bash
   cp backend/.env.example backend/.env
   # Edit .env with your DB credentials, JWT_SECRET, and GEMINI_API_KEY
   ```
4. Run Migrations & Start Server:
   ```bash
   cd backend
   alembic upgrade head
   uvicorn main:app --reload
   ```

### Frontend Setup
1. Install dependencies:
   ```bash
   cd talksense-ui
   npm ci
   ```
2. Setup Environment:
   ```bash
   cp .env.example .env.local
   # Ensure VITE_WS_URL and VITE_API_URL point to your local backend
   ```
3. Start Dev Server:
   ```bash
   npm run dev
   ```

---

## Development & CI/CD

This project enforces strict code quality through GitHub Actions.

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
npm run test:e2e            # Playwright tests
```

---

## Recent Architecture Changes (The "Cleanup" Release)
- **Experimental Code Removed**: Historical hackathon artifacts (e.g., Diart docker pipelines, dozens of standalone benchmark scripts, and generated JSON/WAV dumps) have been permanently cleaned up to ensure a clean, understandable runtime.
- **Simplified Diarization**: Moved entirely away from complex real-time audio diarization in favor of a robust, highly accurate LLM-driven post-session diarization step.
- **Robustness**: Complete E2E testing added, Pytest suite stabilized, and `.gitignore` hardened against log/audio pollution.

---

**Built for SCET Breakout Hackathon 2026**
