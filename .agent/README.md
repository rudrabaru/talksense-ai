# TalkSense AI — Agent Context Directory

This directory contains all persistent context files for AI agents working in this repository.

**Read these files in order before doing any work:**

| File | What it contains | Priority |
|------|-----------------|----------|
| [SKILLS.md](./SKILLS.md) | Full project overview, tech stack, directory map, all rules | 🔴 Read first |
| [PROJECT_STATUS.md](./PROJECT_STATUS.md) | Current build status, known issues, what works | 🔴 Read second |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Locked decisions, prohibited patterns, design patterns | 🟡 Read before coding |
| [API_CONTRACT.md](./API_CONTRACT.md) | REST and WebSocket API specifications | 🟡 Read before API work |
| [DEVELOPMENT_RULES.md](./DEVELOPMENT_RULES.md) | Git workflow, code review, agent usage rules | 🟡 Read before committing |
| [QUICK_REFERENCE.md](./archive/QUICK_REFERENCE.md) | Meeting quality logic quick ref (locked functions) | 🟢 Archived — historical |
| [CHANGELOG_NEGATIVE_DECISIONS.md](./archive/CHANGELOG_NEGATIVE_DECISIONS.md) | Decision logic refinement history (2026-01-04) | 🟢 Archived — historical |
| [TESTING_CHECKLIST.md](./TESTING_CHECKLIST.md) | What is tested and what is NOT VERIFIED | 🟡 Read before testing |
| [RELEASE_CHECKLIST.md](./RELEASE_CHECKLIST.md) | Production readiness gates | 🟡 Read before deploying |
| [SPECIALIST_PREAMBLE.md](./SPECIALIST_PREAMBLE.md) | Shared context for every specialist doc: control-doc routing, cross-cutting invariants, verification ladder | 🟡 Read before specialist work |

## Specialist documents

`agents/*.md` hold domain detail for backend, database, frontend, performance,
security, testing, and directory hygiene. Each assumes `SPECIALIST_PREAMBLE.md`.
`.claude/skills/talksense-*` are thin Claude Code triggers that load the matching
`agents/*.md` on demand; the `agents/*.md` files remain the canonical source.

## Quick Facts

- **Project:** TalkSense AI — Conversation Intelligence Platform
- **Current state:** All 6 phases complete (Phase 6 Interview is skeleton-only)
- **Backend:** FastAPI + Python 3.10+ in `backend/`
- **Frontend:** React 19 + Vite + Tailwind CSS 3 in `talksense-ui/`
- **Database:** PostgreSQL 16+ with Alembic migrations
- **AI Pipeline:** Silero VAD → Faster-Whisper → NLP → Conversation Engine → Alerts
- **Post-Session:** Gemini 1.5 Flash for speaker attribution + executive summaries
- **Run backend:** `cd backend && venv\Scripts\activate && uvicorn main:app --reload`
- **Run frontend:** `cd talksense-ui && npm run dev`
- **Swagger UI:** http://localhost:8000/docs

## What's Built

✅ Audio pipeline (VAD, buffer, transcriber) — `backend/audio/`
✅ Conversation engine (health score, scoring profiles, alert engine) — `backend/engine/`
✅ WebSocket layer (audio handler, session manager, broadcaster, subscriptions) — `backend/ws/`
✅ Legacy batch analysis (POST /analyze, context_analyzer, nlp_engine) — `backend/services/`
✅ Database (PostgreSQL, async ORM, CRUD, Alembic migrations) — `backend/db/`
✅ Live dashboard (DashboardPage, WebSocket hooks, audio capture) — `talksense-ui/src/`
✅ Client memory + session history + comparison — `backend/services/client_memory.py`
✅ Post-session AI pipeline (Gemini, prompt bundles, response validation) — `backend/services/post_session_pipeline.py`
⚠️ Interview mode (scoring profile defined, metrics hardcoded at 50)

## What Does NOT Exist in Production

❌ Pyannote speaker diarization (experimental only — `experimental/diart/`)
❌ `audio/diarizer.py` (deleted — was never production)
❌ Real-time speaker diarization
❌ JWT authentication on REST endpoints
❌ `/auth/register`, `/auth/login`, `/auth/me` routes
❌ `/reports/{session_id}` route
