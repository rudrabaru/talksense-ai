---
name: talksense-database
description: >-
  Database specialist context for TalkSense AI. Use when changing the persistence
  layer — backend/db/models.py (SQLAlchemy 2.x ORM), backend/db/database.py,
  backend/db/crud.py, backend/alembic/ migrations, or the 5-second background flush
  pipeline. Covers the verified schema, ORM design rules, migration procedure,
  persistence invariants, and forbidden changes.
---

# TalkSense AI — Database Specialist

Start with [`.agent/SPECIALIST_PREAMBLE.md`](../../../.agent/SPECIALIST_PREAMBLE.md)
(shared invariants, control docs, verification ladder).

**Full detail:** [`.agent/agents/database_agent.md`](../../../.agent/agents/database_agent.md)
— canonical per-table schema (8 tables), ORM rules, and the step-by-step migration
procedure. Read it before any schema change.

## When this applies

Changes to ORM models, Alembic migrations, CRUD functions, or the background flush
pipeline. In-memory session state and scoring logic are backend, not database
(`talksense-backend`).

## Hard stops

- `Base.metadata.create_all()` is prohibited. Every schema change is an Alembic
  migration committed alongside the model change.
- Do not introduce `lazy="select"` or `lazy="dynamic"` relationships — both break in
  async context. All relationships use `lazy="raise"`.
- Do not drop the `transcript_segments.segment_id` unique constraint — it prevents
  duplicate Whisper segment inserts across overlapping flush cycles.
- Do not add synchronous DB calls inside the WebSocket audio ingest loop.
- Do not repurpose `reset_db.py` for production.

## Before merging

- Migration file generated, inspected (do not trust autogenerate blindly), and
  committed with the model change.
- New FK columns use the correct `ondelete=` strategy (`SET NULL` for parent refs,
  `CASCADE` for session children).
- `alembic upgrade head` passes locally; CI (`backend-ci.yml`) runs migrations
  against clean PostgreSQL.
- All DateTime columns timezone-aware; `lazy="raise"` preserved.
