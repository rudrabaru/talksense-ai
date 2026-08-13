# TalkSense AI — Backend

**Real-Time Conversation Intelligence API**

This is the FastAPI backend for TalkSense AI. It powers real-time audio processing, conversation analytics, and post-session AI analysis.

---

## Architecture

The backend operates two distinct intelligence paths:

### 1. Real-Time Pipeline (WebSocket)

```
Browser Microphone → /ws/audio/{session_id}
    → Silero VAD (speech detection)
    → Audio Buffer (~1000ms accumulation)
    → Faster-Whisper (speech-to-text, small model, int8)
    → NLP Engine (sentiment analysis)
    → Conversation Engine (metrics, scoring)
    → Alert Engine (coaching alerts)
    → Broadcast → /ws/transcript, /ws/metrics, /ws/alerts, /ws/status
```

### 2. Post-Session Pipeline (Gemini LLM)

Triggered when a session is completed (if `ENABLE_POST_SESSION_AI=true`):

```
Full transcript → Prompt Bundle → Gemini 1.5 Flash
    → Response Validation (Pydantic)
    → Speaker Attribution / Role Classification
    → Executive Summary + Action Items
    → PostgreSQL persistence
```

### 3. Legacy Batch Analysis (REST)

The `POST /analyze` endpoint supports offline audio file uploads for batch analysis.

---

## Key Modules

| Directory | Purpose |
|-----------|---------|
| `audio/` | VAD, audio buffer, Faster-Whisper transcriber, GPU manager |
| `engine/` | Conversation engine, scoring profiles, alert engine |
| `ws/` | WebSocket handlers, session manager, broadcast, subscriptions |
| `services/` | NLP engine, post-session pipeline, LLM engine, context analyzer |
| `db/` | SQLAlchemy async models, CRUD operations, Alembic migrations |
| `core/` | Pydantic Settings config, JWT security |
| `prompts/` | Versioned Gemini prompt bundles |
| `config/` | Static configuration (keywords, scoring profiles) |

---

## Quick Start

```bash
cd backend
python -m venv venv
.\venv\Scripts\activate          # Windows
pip install torch torchaudio --index-url https://download.pytorch.org/whl/cu124
pip install -r requirements.txt
cp .env.example .env             # Edit with your credentials
alembic upgrade head             # Create database tables
uvicorn main:app --reload
```

See the root [README.md](../README.md) and [docs/SETUP_GUIDE.md](../docs/SETUP_GUIDE.md) for detailed setup instructions.

---

## API Endpoints

| Method | Route | Purpose |
|--------|-------|---------|
| `GET` | `/health` | Health check |
| `POST` | `/sessions` | Create new session |
| `GET` | `/sessions` | List all sessions |
| `GET` | `/sessions/{id}` | Get session details |
| `DELETE` | `/sessions/{id}` | End session |
| `GET` | `/sessions/compare` | Compare sessions |
| `GET` | `/sessions/{id}/audio` | Get session audio |
| `GET` | `/dashboard/{id}` | Dashboard snapshot (reconnect) |
| `POST` | `/clients` | Create client |
| `GET` | `/clients` | List clients |
| `GET` | `/clients/{id}` | Get client details |
| `POST` | `/analyze` | Legacy batch analysis |

## WebSocket Channels

| Channel | Direction | Auth |
|---------|-----------|------|
| `/ws/audio/{id}` | Client → Server | None |
| `/ws/transcript/{id}` | Server → Client | JWT |
| `/ws/metrics/{id}` | Server → Client | JWT |
| `/ws/alerts/{id}` | Server → Client | JWT |
| `/ws/status/{id}` | Server → Client | JWT |
