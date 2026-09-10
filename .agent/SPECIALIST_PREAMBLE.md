# Specialist Agent Preamble — Shared Context

Every `.agent/agents/*.md` specialist document and every `.claude/skills/talksense-*`
skill assumes this preamble. Read it first, then the relevant specialist document,
then the specific control files that document calls out.

This file centralizes what the seven specialist documents previously repeated. It is
a checklist and a routing table, not a redefinition — the canonical text lives in
`CLAUDE.md` and `.agent/ARCHITECTURE.md`, and those win on any conflict.

---

## Control documents (canonical homes)

| Document | Authoritative for |
|---|---|
| `CLAUDE.md` (repo root) | Tier-0 operating context; supersedes older phrasing elsewhere on conflict |
| `.agent/ARCHITECTURE.md` | System architecture, locked decisions, prohibited patterns, environment variables |
| `.agent/API_CONTRACT.md` | REST and WebSocket endpoint contracts and payload shapes |
| `.agent/PROJECT_STATUS.md` | What is implemented versus planned |
| `.agent/CODEBASE_INDEX.md` | Locating code by folder and purpose |
| `.agent/ACTIVE_FILES.md` | Currently locked files and active development scope |
| `.agent/TESTING_CHECKLIST.md` | What is tested and what is NOT VERIFIED |
| `.agent/DEVELOPMENT_RULES.md` | Git workflow, code review, architecture compliance rules |
| `.agent/RELEASE_CHECKLIST.md` | Production readiness gates |
| `.agent/DECISION_LOG.md` | Why past architectural decisions were made |

Read the full set only when a task genuinely spans them. Normally: this preamble,
one specialist document, and the one or two control files it names.

---

## Cross-cutting invariants

Enforced for every domain. Full text in `CLAUDE.md` ("Hard constraints") and
`.agent/ARCHITECTURE.md`.

- **Model singletons.** `audio.vad.get_vad()`, `audio.transcriber.get_transcriber()`,
  `services.nlp_engine.NLPEngine()` are process singletons. Never reload mid-request.
- **GPU bound.** GPU inference is gated by the `gpu_concurrency` semaphore in
  `backend/audio/gpu_manager.py`. Do not bypass it. Whisper and the sentiment model
  never run concurrently on the GPU. 4 GB VRAM target (RTX 3050); Whisper runs int8, not float16.
- **Migrations.** Schema changes go through Alembic (`alembic upgrade head`).
  `Base.metadata.create_all()` is prohibited.
- **Locked functions, do not rewrite.** `compute_meeting_quality_v2()`,
  `compose_executive_summary_v2()`, `generate_key_insights_v2()` in
  `backend/services/context_analyzer.py`; the sentiment pipeline in `nlp_engine.py`;
  scoring weights stay JSON-driven in `scoring_profiles.py`.
- **Audio buffer constants** (`backend/audio/buffer.py`): `TARGET_DURATION_MS = 2000`,
  `OVERLAP_MS = 1000`, `SILENCE_GAP_MS = 600`, `MIN_FLUSH_MS = 800`.
  `TARGET_DURATION_MS = 2000` is the **current** value, not a permanent lock. If an
  approved ASR/streaming architecture changes it, the implementation plus the approved
  design become the source of truth and this documentation must be updated to match.
  Do not change these values outside an approved design.
- **No live diarization.** No Pyannote or diart in the live pipeline. There is no
  `audio/diarizer.py`; do not create one without a design decision.
- **Batch path preserved.** Do not delete the batch `POST /analyze` path.
- **Async persistence.** Database writes are async and off the WebSocket audio ingest path.
- **Explainable scoring only.** No scikit-learn or predictive neural nets in the scoring pipeline.
- **Accuracy is non-negotiable.** `backend/audio/`, `ws/audio_handler.py`, the locked
  functions, `backend/benchmark_dataset/`, and any ground truth are high-risk surface.
  Treat every change there as high risk.

---

## Verification ladder

L1 static/lint → L2 focused tests → L3 broader regression → L4 accuracy benchmark →
L5 architecture/release review.

Run the cheapest level that could disprove the change. Never skip L4 when a change can
move WER, diarization, sentiment, or a metric formula, and never skip accuracy
verification to save tokens or time. Exact commands are in `CLAUDE.md`
("Verification commands").

---

## Working rules

- Plan before execution on non-trivial tasks: research the target files, present a
  plan, wait for approval (`.agent/DEVELOPMENT_RULES.md` §1).
- Never auto-delete or auto-move files. Log cleanups in `.agent/CLEANUP_AUDIT.md` for
  a human to execute.
- No new root-level directories without architecture approval.
- Search before reading; read targeted line ranges. Do not read `context_analyzer.py`,
  `ws/session_manager.py`, `db/crud.py`, or `main.py` whole.
- Do not guess APIs, versions, flags, SHAs, or package names. Verify in code or docs.
- Concise output: no emojis, no em-dashes, no sycophantic openers or closing fluff.
