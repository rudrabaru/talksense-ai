# Database Agent Specialist

## Authoritative References — Read These First

Before making any database change, read:

- `.agent/ARCHITECTURE.md` — database design principles
- `.agent/API_CONTRACT.md` — API response shapes that the DB must support
- `.agent/ACTIVE_FILES.md` — schema lock status
- `.agent/DEVELOPMENT_RULES.md` — migration requirements and `create_all()` prohibition

---

## Scope of Responsibility

The database agent owns the persistence layer: ORM models, Alembic migrations, CRUD functions, and the background flush pipeline.

**Does NOT own:**
- In-memory session state (SessionManager, ConversationState) → Backend Agent
- Business logic or scoring computation → Backend Agent
- Frontend data display → Frontend Agent

---

## Directory Ownership

```
backend/
├── db/
│   ├── models.py     ← SQLAlchemy 2.x ORM models (all 8 tables)
│   ├── database.py   ← async engine, AsyncSessionLocal, get_db()
│   ├── crud.py       ← all data-access functions
│   └── __init__.py
├── alembic/          ← migration scripts and alembic.ini
└── reset_db.py       ← development-only reset helper (NOT for production use)
```

---

## Stack

- **PostgreSQL 16+** on port 5432.
- **SQLAlchemy 2.x** declarative ORM with `asyncpg` driver.
- **Alembic** for all schema migrations.
- `AsyncSessionLocal` from `db/database.py` is the only session factory. Do not create alternative session factories.

---

## Migration Rule — Absolute

**`Base.metadata.create_all()` is NOT used in production.**

The comment in `db/models.py` line 21–22 describes the original Phase 3 design. This was superseded by Alembic before the Phase 3 launch. The comment is stale.

**The only approved way to apply schema changes:**

```bash
cd backend
alembic revision --autogenerate -m "describe the change"
alembic upgrade head
```

CI (`backend-ci.yml`) runs `alembic upgrade head` against a real PostgreSQL instance on every push. Any schema change that is not in a migration file will diverge the CI database from the production database.

---

## Schema — Verified Against `db/models.py`

### Table: `users`
| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | autoincrement |
| `email` | String(255) | unique, indexed |
| `password_hash` | String(255) | bcrypt hash; auth deferred (see Security Agent) |
| `voice_embedding` | JSONB | nullable; reserved for future speaker enrolment |
| `created_at` | DateTime(tz) | server default |

### Table: `clients`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | gen_random_uuid() |
| `user_id` | Integer FK → users(id) | nullable; ondelete=SET NULL |
| `name` | String(255) | required |
| `industry` | String(255) | nullable |
| `created_at` | DateTime(tz) | server default |

### Table: `sessions`
| Column | Type | Notes |
|--------|------|-------|
| `id` | UUID PK | |
| `client_id` | UUID FK → clients(id) | nullable; ondelete=SET NULL; indexed |
| `user_id` | Integer FK → users(id) | nullable; ondelete=SET NULL; indexed |
| `mode` | String(50) | `meeting` / `sales` / `interview` |
| `title` | String(255) | nullable |
| `started_at` | DateTime(tz) | server default |
| `ended_at` | DateTime(tz) | nullable |
| `duration` | Float | nullable; seconds |
| `status` | String(50) | mirrors SessionStatus enum |
| `speaker_attribution_status` | String(50) | nullable; post-session pipeline lifecycle |
| `audio_file_path` | String(1024) | nullable; absolute path to session WAV |

### Table: `transcript_segments`
| Column | Type | Notes |
|--------|------|-------|
| `id` | BigInteger PK | autoincrement |
| `session_id` | UUID FK → sessions(id) | ondelete=CASCADE |
| `segment_id` | String(36) | nullable; unique; Whisper segment UUID |
| `speaker_id` | String(100) | nullable; e.g. "Speaker A", "Speaker 1" |
| `start_time` | Float | audio file offset in seconds |
| `end_time` | Float | audio file offset in seconds |
| `text` | Text | utterance content |
| `sentiment` | Float | nullable; raw score |
| `sentiment_label` | String(50) | nullable; "positive" / "negative" / "neutral" |
| `words` | JSONB | nullable; word-level timestamps from Whisper |

Composite index: `(session_id, start_time)` for ordered transcript retrieval.

### Table: `session_metrics`
| Column | Type | Notes |
|--------|------|-------|
| `id` | BigInteger PK | autoincrement |
| `session_id` | UUID FK → sessions(id) | ondelete=CASCADE |
| `metric_name` | String(100) | e.g. "health_score", "participation" |
| `metric_value` | JSONB | scalar or structured (dict/list/number) |
| `timestamp` | DateTime(tz) | server default |

Composite index: `(session_id, timestamp)` for time-ordered metric history.

### Table: `analysis_results`
| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `session_id` | UUID FK → sessions(id) | unique; one-to-one with Session |
| `health_score` | Integer | nullable |
| `summary` | Text | nullable |
| `report_json` | JSONB | nullable; decisions, action_items, key_insights, sentiment_timeline |
| `processed_transcript` | JSONB | nullable; LLM-processed segments |
| `created_at` | DateTime(tz) | server default |

### Table: `alerts`
| Column | Type | Notes |
|--------|------|-------|
| `id` | BigInteger PK | autoincrement |
| `session_id` | UUID FK → sessions(id) | ondelete=CASCADE |
| `type` | String(100) | nullable; alert_type key |
| `severity` | String(50) | `critical` / `warning` / `info` |
| `message` | Text | human-readable alert text |
| `timestamp` | DateTime(tz) | not nullable |

Composite index: `(session_id, timestamp)`.

### Table: `client_snapshots`
| Column | Type | Notes |
|--------|------|-------|
| `id` | Integer PK | |
| `client_id` | UUID FK → clients(id) | ondelete=CASCADE |
| `snapshot_date` | DateTime(tz) | server default |
| `summary` | Text | nullable |
| `sentiment_score` | Float | nullable |
| `sentiment_trend` | String(50) | nullable; `improving` / `stable` / `declining` |
| `meetings_count` | Integer | default 0 |
| `last_meeting_date` | DateTime(tz) | nullable |
| `common_objections` | JSONB | nullable; list of strings |

Composite index: `(client_id, snapshot_date)`.

---

## ORM Design Rules

- All DateTime columns are timezone-aware (`DateTime(timezone=True)`).
- All relationships use `lazy="raise"` — never load relationships implicitly (prevents async IO errors).
- `clients.user_id` and `sessions.client_id`/`sessions.user_id` use `ondelete="SET NULL"` — deleting a parent preserves child rows.
- `sessions` → children use `ondelete="CASCADE"` — deleting a session deletes all its segments, metrics, alerts, and analysis result.
- JSONB is used for any variable-width or structured field.
- Do NOT use `lazy="select"` or `lazy="dynamic"` — both cause runtime errors in async context.

---

## Persistence Invariants

- **5-second flush**: `FLUSH_INTERVAL_SECONDS = 5.0` in `ws/session_manager.py`. The background flusher calls CRUD functions on each active session. DB writes must remain async.
- **Final flush**: On `session_manager.end()`, a final flush persists all remaining in-memory state before the session is removed.
- **Stale session recovery**: `crud.recover_stale_sessions()` runs at startup, marking any session with status `created` or `active` as `interrupted` if it has no recent activity.
- **No double-insert**: `segment_id` (unique index) prevents duplicate Whisper segment rows across overlapping flush cycles.

---

## Schema Change Procedure

1. Modify `db/models.py`.
2. Run `alembic revision --autogenerate -m "description"`.
3. Inspect the generated migration file — do not trust autogenerate blindly.
4. Run `alembic upgrade head` locally against a test DB.
5. PR against `dev`. CI will validate the migration applies cleanly.
6. Never apply schema changes directly via SQL without a corresponding migration file.

---

## Required Checks Before Merging DB Changes

- [ ] Migration file generated and committed alongside model changes
- [ ] `create_all()` not introduced anywhere
- [ ] `lazy="raise"` preserved on all relationships
- [ ] All new FK columns use correct `ondelete=` strategy
- [ ] `alembic upgrade head` passes locally
- [ ] CI passes (backend-ci.yml runs migrations against clean PostgreSQL)

---

## Forbidden Changes

- Do not use `Base.metadata.create_all()`.
- Do not introduce `lazy="select"` or `lazy="dynamic"` relationships.
- Do not drop the `segment_id` unique constraint — this prevents duplicate segment insertions.
- Do not add synchronous DB calls inside the WebSocket audio ingest loop.
- Do not modify `reset_db.py` for production use — it is a development utility only.
