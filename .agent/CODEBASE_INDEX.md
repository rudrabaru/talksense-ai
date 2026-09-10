# TalkSense AI — Codebase Index

This index is optimized for AI context loading and rapid codebase onboarding.

---

## Folder Map & System Owners

### backend/
- **Purpose**: FastAPI application backend providing HTTP API endpoints and WebSocket channels for real-time audio processing, conversation analysis, and post-session AI.
- **Key Files**:
  - `main.py`: Application entry point, lifespan, routes, and model warmup.
  - `requirements.txt`: Python dependencies.
- **Dependencies**: fastapi, uvicorn, torch, transformers, faster-whisper, silero-vad, sqlalchemy, asyncpg, alembic, google-genai.
- **Owner System**: Backend Core / Platform Lifecycle.

### backend/audio/
- **Purpose**: Real-time audio ingestion pipeline from WebSocket raw PCM binary chunks to VAD, buffering, and transcription.
- **Key Files**:
  - `vad.py`: Silero VAD speech detection wrapper (CPU).
  - `buffer.py`: Audio accumulator buffer (~2000ms speech chunk flush; `TARGET_DURATION_MS`).
  - `transcriber.py`: Faster-Whisper wrapper (singleton, GPU/int8).
  - `gpu_manager.py`: GPU concurrency management.
- **Dependencies**: Silero VAD, Faster-Whisper.
- **Owner System**: Backend Audio Pipeline.

### backend/engine/
- **Purpose**: Real-time conversation intelligence engine that processes text segments, calculates metrics, and raises alerts.
- **Key Files**:
  - `conversation_engine.py`: Main segment analysis engine.
  - `scoring_profiles.py`: JSON-configured scoring weights for Meeting, Sales, and Interview profiles.
  - `alert_engine.py`: Severity rules, cooldown tracking, and duplication suppression.
- **Dependencies**: backend/services/nlp_engine.py.
- **Owner System**: Conversation Intelligence / Analytics.

### backend/ws/
- **Purpose**: WebSocket handler, session state management, and real-time subscriber broadcaster.
- **Key Files**:
  - `audio_handler.py`: `/ws/audio/{session_id}` raw binary PCM receiver.
  - `session_manager.py`: Connection registry, state transitions, and background flusher.
  - `broadcast.py`: Multi-channel broadcaster.
  - `subscriptions.py`: JWT-protected subscription routes (`/ws/transcript`, `/ws/metrics`, `/ws/alerts`, `/ws/status`).
- **Dependencies**: fastapi, websockets.
- **Owner System**: Real-time Communication.

### backend/db/
- **Purpose**: Relational persistence layer for session storage, client snapshots, and reports.
- **Key Files**:
  - `models.py`: SQLAlchemy ORM models (8 tables).
  - `database.py`: Async engine setup with asyncpg.
  - `crud.py`: Database helper queries.
- **Schema Management**: Alembic migrations (`alembic/` directory). `create_all()` is NOT used.
- **Dependencies**: SQLAlchemy, asyncpg, Alembic.
- **Owner System**: Storage & Persistence.

### backend/services/
- **Purpose**: Core NLP services, post-session AI pipeline, and legacy batch analysis.
- **Key Files**:
  - `context_analyzer.py`: Locked analytics algorithms (meeting quality, executive summary, key insights).
  - `nlp_engine.py`: Multi-lingual sentiment classification wrapper.
  - `speech_to_text.py`: Legacy Whisper batch file transcriber (for `/analyze` endpoint).
  - `post_session_pipeline.py`: Post-session AI orchestrator (Gemini).
  - `llm_engine.py`: Gemini API wrapper.
  - `response_validator.py`: Pydantic validation of LLM output.
  - `prompt_loader.py`: Versioned prompt bundle loader.
  - `client_memory.py`: Client snapshot aggregation.
  - `comparison.py`: Session comparison logic.
  - `objection_handler.py`: Objection analysis (CI-tested, not production-called).
  - `transcript_builder.py`: Transcript formatting (CI-tested, not production-called).
- **Dependencies**: HuggingFace transformers, torch, google-genai.
- **Owner System**: NLP / Post-Session AI / Legacy Compatibility.

### backend/core/
- **Purpose**: Application configuration and security.
- **Key Files**:
  - `config.py`: Pydantic-settings configuration (loads from env vars / .env files).
  - `security.py`: JWT token creation and verification for WebSocket authentication.
- **Owner System**: Configuration / Security.

### talksense-ui/
- **Purpose**: Single Page React frontend built via Vite for real-time dashboard and analytics.
- **Key Files**:
  - `src/App.jsx`: Routing definition.
  - `src/index.css`: Tailwind CSS design system directives.
- **Dependencies**: React 19, React Router DOM 7, Vite, Tailwind CSS 3.
- **Owner System**: Frontend UI.

### talksense-ui/src/pages/
- **Purpose**: 8 route-level pages.
- **Key Pages**:
  - `DashboardPage.jsx`: Main product — live 3-panel real-time dashboard.
  - `HomePage.jsx`: Landing page with session creation.
  - `SessionsPage.jsx`: Session history and management.
  - `ComparisonPage.jsx`: Side-by-side session comparison.
  - `UploadPage.jsx`: Legacy batch audio file upload.
  - `ResultsPage.jsx`: Batch analysis results.

### talksense-ui/src/components/
- **Purpose**: Reusable UI components and live dashboard panels.
- **Key Directories**:
  - `dashboard/`: Live dashboard panels (TranscriptPanel, MetricsPanel, AlertPanel, etc.).
- **Dependencies**: Tailwind CSS.
- **Owner System**: Frontend UI Components.

### talksense-ui/src/hooks/
- **Purpose**: Custom React hooks for WebSocket and audio.
- **Key Files**:
  - `useSessionWebSocket.js`: 4-channel WS with exponential backoff + REST reconciliation.
- **Owner System**: Frontend Real-time Communication.

### docs/
- **Purpose**: Project documentation, setup guides, and historical archives.
- **Key Files**:
  - `SETUP_GUIDE.md`: Developer environment setup guide.
  - `archive/`: Historical architecture docs and deprecated planning docs.
- **Owner System**: Documentation.

### .agent/
- **Purpose**: Persistent context, architecture rules, build stages, and AI agent directives.
- **Owner System**: Agent System / DevOps Context.

### experimental/
- **Purpose**: Isolated experiments NOT part of production. Contains Diart diarization experiment and benchmarks.
- **Owner System**: Research / Experiments.

### .github/workflows/
- **Purpose**: CI/CD pipelines.
- **Key Files**: `backend-ci.yml`, `frontend-ci.yml`, `integration-ci.yml`, `qa_pipeline.yml`.
- **Owner System**: CI/CD.
