# TalkSense AI — Codebase Index

This index is optimized for AI context loading and rapid codebase onboarding.

---

## Folder Map & System Owners

### backend/
- **Purpose**: FastAPI application backend providing HTTP API endpoints and WebSocket channels for audio processing and real-time conversation analysis.
- **Key Files**:
  - [main.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/main.py): Application entry point, lifespan, routes, and model warmup.
  - [requirements.txt](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/requirements.txt): Python dependencies.
- **Dependencies**: fastapi, uvicorn, torch, transformers, faster-whisper, silero-vad, sqlalchemy.
- **Owner System**: Backend Core / Platform Lifecycle.

### backend/audio/
- **Purpose**: Real-time audio ingestion pipeline from WebSocket raw PCM binary chunks to VAD, buffering, transcription, and diarization.
- **Key Files**:
  - [vad.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/audio/vad.py): Silero VAD speech detection wrapper.
  - [buffer.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/audio/buffer.py): Audio accumulator buffer (~1000ms speech chunk flush).
  - [transcriber.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/audio/transcriber.py): Faster-Whisper wrapper (singleton model).
  - [diarizer.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/audio/diarizer.py): Pyannote 3.1 speaker tracking wrapper.
- **Dependencies**: Silero VAD, Faster-Whisper, Pyannote.audio.
- **Owner System**: Backend Audio Pipeline.

### backend/engine/
- **Purpose**: Real-time conversation intelligence engine that processes text segments, calculates sentiment/filler/objection metrics, and raises alerts.
- **Key Files**:
  - [conversation_engine.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/engine/conversation_engine.py): Main segment analysis engine.
  - [scoring_profiles.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/engine/scoring_profiles.py): JSON-configured scoring weights for Meeting, Sales, and Interview profiles.
  - [alert_engine.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/engine/alert_engine.py): Severity rules, cooldown tracking, and duplication suppression.
- **Dependencies**: backend/services/nlp_engine.py.
- **Owner System**: Conversation Intelligence / Analytics.

### backend/ws/
- **Purpose**: WebSocket handler, session state management, and real-time subscriber broadcaster.
- **Key Files**:
  - [audio_handler.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/ws/audio_handler.py): `/ws/audio/{session_id}` raw binary PCM receiver.
  - [session_manager.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/ws/session_manager.py): Connection registry and state transitions.
  - [broadcast.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/ws/broadcast.py): Multi-channel broadcaster.
  - [subscriptions.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/ws/subscriptions.py): Client subscription routes (`/ws/transcript`, `/ws/metrics`, `/ws/alerts`, `/ws/status`).
- **Dependencies**: fastapi, websockets.
- **Owner System**: Real-time Communication.

### backend/db/
- **Purpose**: Relational persistence layer for session storage, client briefing snapshots, and reports.
- **Key Files**:
  - [models.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/db/models.py): [TODO] SQLAlchemy models.
  - [database.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/db/database.py): [TODO] Async engine setup.
  - [crud.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/db/crud.py): [TODO] Database helper queries.
- **Dependencies**: SQLAlchemy, asyncpg.
- **Owner System**: Storage & Persistence.

### backend/services/
- **Purpose**: Core NLP helper services and legacy batch analysis processors.
- **Key Files**:
  - [context_analyzer.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/services/context_analyzer.py): Locked legacy batch algorithms for meeting quality.
  - [nlp_engine.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/services/nlp_engine.py): Multi-lingual sentiment classification wrapper.
  - [speech_to_text.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/services/speech_to_text.py): Legacy whisper batch file transcriber.
- **Dependencies**: HuggingFace transformers, torch.
- **Owner System**: NLP & Legacy Compatibility Services.

### talksense-ui/
- **Purpose**: Single Page React frontend built via Vite for dashboard and analytics display.
- **Key Files**:
  - [App.jsx](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/src/App.jsx): Routing definition.
  - [index.css](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/src/index.css): Core design system CSS.
- **Dependencies**: React, React Router, Vite.
- **Owner System**: Frontend UI.

### talksense-ui/src/components/
- **Purpose**: UI cards, selector badges, and real-time dashboard layout blocks.
- **Key Files**:
  - [TranscriptLive.jsx](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/src/components/TranscriptLive.jsx): Legacy live transcription prototype.
  - [dashboard/](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/src/components/dashboard/): [TODO] Upcoming live panels (`TranscriptPanel`, `IntelligencePanel`, `AlertPanel`).
- **Dependencies**: vanilla CSS.
- **Owner System**: Frontend UI Components.

### docs/ & docs/archive/
- **Purpose**: Project specifications, architecture frozen blueprints, and historical fixes documentation.
- **Key Files**:
  - [new_implementation_plan.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/docs/new_implementation_plan.md): Active Phase instructions.
  - [TalkSenseAI_New_Plan.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/docs/archive/TalkSenseAI_New_Plan.md): Core frozen architecture specs.
- **Owner System**: Documentation.

### archive/
- **Purpose**: Deprecated planning documents, legacy fix guides, and superseded architecture context files.
- **Key Directories**:
  - [deprecated_docs/](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/deprecated_docs/): Holds legacy meeting/sales logic simplification plans and surgical fix guides.
  - [old_plans/](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/old_plans/): Holds legacy v3 agent guides and frozen signals strategies.
- **Owner System**: Archive Management.
