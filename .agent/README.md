# TalkSense AI — Agent Context Directory

This directory contains all persistent context files for AI agents working in this repository.

**Read these files in order before doing any work:**

| File | What it contains | Priority |
|------|-----------------|----------|
| [SKILLS.md](./SKILLS.md) | Full project overview, tech stack, directory map, all rules | 🔴 Read first |
| [PROJECT_STATUS.md](./PROJECT_STATUS.md) | Exact build status per phase, known issues, what to build next | 🔴 Read second |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Locked decisions, prohibited patterns, design patterns | 🟡 Read before coding |
| [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) | Legacy batch mode fix guide (meeting quality v2) | 🟢 Reference only |
| [CHANGELOG_NEGATIVE_DECISIONS.md](./CHANGELOG_NEGATIVE_DECISIONS.md) | Decision logic refinement history | 🟢 Reference only |
| [FINAL_FIX_STRATEGY.md](./FINAL_FIX_STRATEGY.md) | Frozen signals fix (legacy) | 🟢 Reference only |
| [FROZEN_SIGNALS_FIX.md](./FROZEN_SIGNALS_FIX.md) | Frozen signals deep dive (legacy) | 🟢 Reference only |
| [FROZEN_SIGNALS_QUICK_REF.md](./FROZEN_SIGNALS_QUICK_REF.md) | Frozen signals quick ref (legacy) | 🟢 Reference only |

## Quick Facts

- **Project:** TalkSense AI v4 — Conversation Intelligence Platform
- **Current build stage:** Phase 3 (DB) is next
- **Backend:** FastAPI + Python 3.11 in `backend/`
- **Frontend:** React + Vite in `talksense-ui/`
- **Run backend:** `cd backend && venv\Scripts\activate && uvicorn main:app --reload`
- **Run frontend:** `cd talksense-ui && npm run dev`
- **Swagger UI:** http://localhost:8000/docs

## What's Built vs What's Not

✅ Audio pipeline (VAD, buffer, transcriber, diarizer)  
✅ Conversation engine (health score, scoring profiles, alert engine)  
✅ WebSocket layer (audio handler, session manager, broadcaster, subscriptions)  
✅ Legacy batch analysis (POST /analyze, context_analyzer, nlp_engine)  
❌ Database (backend/db/ is empty — Phase 3)  
❌ Live dashboard (DashboardPage, hooks, dashboard components — Phase 4)  
❌ Client memory + reports (memory_service, report_service, new pages — Phase 5)  
❌ Interview mode (Phase 6)
