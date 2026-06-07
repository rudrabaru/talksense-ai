# TalkSense AI — Active Development Tracking

This file tracks the current active scope of development and file locks.

---

- **Current Phase**: Phase 3 — Database & Persistence
- **Current Objective**: Connect TalkSense AI's in-memory session state to PostgreSQL so that sessions survive restarts, reports can be generated, and client memory persists.
- **Files Being Modified**:
  - [models.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/db/models.py) (NEW)
  - [database.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/db/database.py) (NEW)
  - [crud.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/db/crud.py) (NEW)
  - [main.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/main.py) (MODIFY - wire routes/lifespan startup)
  - [session_manager.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/ws/session_manager.py) (MODIFY - add 5s flush loop)
- **Files Locked**:
  - [context_analyzer.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/services/context_analyzer.py) (Do NOT modify quality formulas, summaries, and insights)
  - [nlp_engine.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/services/nlp_engine.py) (Locked sentiment classifier initialization)
- **Notes**:
  - Do NOT use Alembic migration framework yet. Initialize tables with `Base.metadata.create_all()` on startup.
  - Keep database tasks async or offloaded to avoid blocking WS audio ingestion frame loops.
