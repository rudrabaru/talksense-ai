# Phase 3 — Database & Persistence

> **STATUS: ✅ COMPLETE** — All tasks below have been implemented. Database uses Alembic migrations (not `create_all()`).

## Goal

Connect TalkSense AI's in-memory session state to PostgreSQL so that sessions survive restarts, reports can be generated, and client memory persists across sessions.

## Pre-conditions

- PostgreSQL 17.5 must be running on localhost:5432
- Database `talksense` must exist (create with: `CREATE DATABASE talksense;`)
- `.env` must have `DATABASE_URL` set correctly

## Task List

- [ ] **3.1 — Create DB package**
  - Create `backend/db/__init__.py` (empty)

- [ ] **3.2 — Create SQLAlchemy models**
  - Create `backend/db/models.py`
  - Tables: `users`, `clients`, `sessions`, `transcript_segments`, `session_metrics`, `analysis_results`, `alerts`, `client_snapshots`
  - All required indexes applied
  - Use SQLAlchemy 2.x declarative ORM style

- [ ] **3.3 — Create async DB engine**
  - Create `backend/db/database.py`
  - Async engine using `asyncpg`
  - `get_db()` FastAPI dependency
  - `Base.metadata.create_all()` on startup *(Historical: Alembic is now used instead)*

- [ ] **3.4 — Create CRUD layer**
  - Create `backend/db/crud.py`
  - Functions: `create_session`, `get_session`, `update_session_status`, `save_transcript_segment`, `save_metric`, `save_alert`, `create_client`, `get_client`, `list_clients`, `save_analysis_result`, `update_client_snapshot`, `get_client_briefing`

- [ ] **3.5 — Wire DB init to startup**
  - Add `await database.create_all()` to `main.py` lifespan *(Historical: replaced by `alembic upgrade head`)*
  - Import and call before model warmup

- [ ] **3.6 — Add session flush to session_manager**
  - Every 5 seconds: flush in-memory transcript segments + metrics to DB
  - Use `asyncio.create_task()` background flush loop
  - Must not block the audio pipeline

- [ ] **3.7 — Add session end persistence**
  - On `DELETE /sessions/{id}` or `SessionStatus.COMPLETED`:
    - Save final `analysis_results` row
    - Update `client_snapshots` for the associated client

- [ ] **3.8 — Add clients REST endpoints**
  - `POST /clients` → create client, return client_id
  - `GET /clients` → list all clients for current user
  - `GET /clients/{id}` → get client + briefing data (past meetings, objections, sentiment trend)

- [ ] **3.9 — Add reports REST endpoint**
  - `GET /reports/{session_id}` → return analysis_results + full transcript

- [ ] **3.10 — Verify**
  - `POST /sessions` persists to DB
  - After session ends, `GET /reports/{session_id}` returns full report
  - Second session with same client_id shows correct briefing data

## Files to Create

| File | Status |
|------|--------|
| `backend/db/__init__.py` | ❌ TODO |
| `backend/db/models.py` | ❌ TODO |
| `backend/db/database.py` | ❌ TODO |
| `backend/db/crud.py` | ❌ TODO |

## Files to Modify

| File | Change |
|------|--------|
| `backend/main.py` | Add DB init to lifespan, add /clients and /reports endpoints |
| `backend/ws/session_manager.py` | Add 5s flush loop |

## Dependencies

Add to `backend/requirements.txt` if missing:
```
sqlalchemy>=2.0
asyncpg
```

## DO NOT

- ~~Do NOT use Alembic for this phase — use `create_all()` for simplicity~~ *(Historical: Alembic is now the active migration mechanism)*
- Do NOT block the audio WebSocket pipeline with DB writes — always use `asyncio.create_task()`
- Do NOT remove in-memory session state — DB is a mirror/persistence layer, not a replacement
