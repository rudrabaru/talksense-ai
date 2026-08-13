# TalkSense AI — Active Development Tracking

This file tracks the current active scope of development and file locks.

---

- **Current Phase**: All core phases (1–5) complete. Phase 6 (Interview Mode) is skeleton-only.
- **Current Objective**: Documentation cleanup and accuracy audit. No active feature development.
- **Files Being Modified**: Documentation files only (`.md` files).
- **Files Locked**:
  - `backend/services/context_analyzer.py` — Do NOT modify quality formulas, summaries, and insights (`compute_meeting_quality_v2()`, `compose_executive_summary_v2()`, `generate_key_insights_v2()`)
  - `backend/services/nlp_engine.py` — Locked sentiment classifier initialization
- **Notes**:
  - Database schema is managed by Alembic (`alembic upgrade head`). Do NOT use `create_all()`.
  - Keep database tasks async to avoid blocking WS audio ingestion frame loops.
  - Post-session AI pipeline uses Gemini 1.5 Flash (`ENABLE_POST_SESSION_AI=true`).
