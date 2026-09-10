# CLAUDE.md — TalkSense AI (Tier 0 context)

TalkSense AI is an accuracy-critical, real-time conversation-intelligence system. The live dashboard is the product; transcription and reports are supporting capabilities.

**Accuracy is non-negotiable.** Never trade accuracy, regression testing, security, persistence correctness, or production reliability for token or time savings.

## Stack and pipeline
React 19 + Vite + Tailwind 3 | FastAPI (Python 3.10+) | PostgreSQL 16+ with SQLAlchemy 2.x async and Alembic.
Live: mic PCM to `/ws/audio/{session_id}` to Silero VAD (CPU) to buffer to Faster-Whisper (`small`, int8, CUDA) to `conversation_engine` to `alert_engine` to WebSocket broadcast.
Post-session: `post_session_pipeline` to `prompt_loader` to Gemini 1.5 Flash to `response_validator` to PostgreSQL.

## Hard constraints (source: `.agent/ARCHITECTURE.md`)
- 4 GB VRAM development target (RTX 3050). Whisper runs int8, not float16.
- AI models are process singletons: `audio.vad.get_vad()`, `audio.transcriber.get_transcriber()`, `services.nlp_engine.NLPEngine()`. Never reload mid-request.
- GPU inference is bounded by the `gpu_concurrency` semaphore in `backend/audio/gpu_manager.py`. Do not bypass it.
- Schema changes go through Alembic (`alembic upgrade head`). `create_all()` is prohibited.
- Locked, do not rewrite: `compute_meeting_quality_v2()`, `compose_executive_summary_v2()`, `generate_key_insights_v2()` in `backend/services/context_analyzer.py`; the sentiment pipeline in `nlp_engine.py`; scoring weights stay JSON-driven in `scoring_profiles.py`.
- Do not delete the batch `POST /analyze` path. Pyannote diarization is experimental only, not production.
- Accuracy-critical surface: `backend/audio/`, `ws/audio_handler.py`, the locked functions, `backend/benchmark_dataset/`, and any ground truth. Treat every change here as high risk.

## Paths and traversal
`backend/` FastAPI app | `talksense-ui/` React app | `.agent/` project documentation (routing table below).
Two virtualenvs exist and differ: root `venv/` has dev tooling plus runtime and is what the commands below use; `backend/venv/` is runtime-only with different package versions.

**Never traverse:** `venv/`, `backend/venv/`, `node_modules/`, `session_audio/`, `sample_audio/`, `uploads/`, `docs/presentation/`, `experimental/`, `archive/`.
Use ripgrep or git-aware search. Do not run unrestricted `find` from the repo root; `backend/` alone is ~3.7 GB and such a scan times out.
Search before reading. For files over ~20 KB, grep for the symbol and read only the surrounding line range. `context_analyzer.py` (80 KB), `ws/session_manager.py` (52 KB), `db/crud.py` (42 KB) and `main.py` (39 KB) should almost never be read whole.

## Verification commands (all verified working in this repo)
| Purpose | Command | Run from |
|---|---|---|
| Lint | `./venv/Scripts/ruff.exe check backend/` | repo root |
| Format check | `./venv/Scripts/black.exe --check backend/` | repo root |
| Types | `./venv/Scripts/pyright.exe backend/` | repo root |
| Unit tests | `../venv/Scripts/python.exe -m pytest tests/ --ignore=tests/smoke_test_ws.py --ignore=tests/run_verification.py --ignore=tests/validate_pipeline.py` | `backend/` |
| Frontend lint / build | `npm run lint` / `npm run build` | `talksense-ui/` |

Ladder: L1 static and lint, L2 focused tests, L3 broader regression, L4 accuracy benchmark, L5 architecture and release review. Verify proportionally to risk: run the cheapest level that could disprove the change. Never skip L4 when a change can move WER, diarization, sentiment, or a metric formula, and never skip accuracy verification to save tokens.

## Model routing (manual guidance; not automatically enforced)

Pick the least expensive model that fits. Escalate on architectural uncertainty, accuracy risk, or demonstrated Sonnet difficulty, not on task size, importance, or duration.

- **Haiku** for trivial mechanical work only: formatting, imports, renames, tiny UI tweaks.
- **Sonnet + high effort** is the default for everything else: implementation, debugging, testing, refactoring, CI investigation, documentation and harness work, and routine code review.
- **`/model opusplan`** selectively, when a task needs substantial architectural reasoning before implementation: ASR streaming buffer/overlap/merge design; Whisper model tier, quantization, decoding, `initial_prompt`, or `condition_on_previous_text` decisions; real-time diarization architecture; GPU sequencing / VRAM architecture; the locked scoring functions or scoring weights; production or offline pipeline architecture; or another change explicitly identified as accuracy-critical and architecturally consequential. Under `opusplan`, Opus does the planning and reasoning and Sonnet executes the resulting implementation; it does not run the whole implementation on Opus.
- **Direct Opus** only when Sonnet is genuinely stuck after reasonable investigation, or for a final high-stakes accuracy or release sign-off that justifies deeper independent reasoning. Not for continuous use.

Model choice does not replace `/accuracy`: accuracy-critical changes still require ground truth and the verification level `/accuracy` sets, regardless of model. Record model-escalation decisions and any unresolved architectural questions in the session handoff (`session-handoff` skill: "Decisions & constraints carried forward" and "Deferred + open questions").

## Working rules
Search before reading; read targeted line ranges; do not scan the repository for facts already stated here, and do not re-read `.agent/` documents already summarized above. Do not spawn subagents for small localized tasks; use them only when parallelism or specialized reasoning outweighs their context overhead, and require concise, actionable output. Prefer a short evidence summary over a large generated report. Do not guess APIs, versions, flags, commit SHAs, or package names; verify in code or docs before asserting. Be thorough in reasoning and concise in output: no emojis, no em-dashes, no sycophantic openers, no closing fluff.

## Where to look (consult on demand; do not read these as a set)
| Need | File |
|---|---|
| Architecture, locked decisions, prohibited patterns, env vars | `.agent/ARCHITECTURE.md` |
| REST and WebSocket contracts | `.agent/API_CONTRACT.md` |
| Project overview, stack detail, directory map | `.agent/SKILLS.md` |
| What is built versus planned | `.agent/PROJECT_STATUS.md` |
| Locating code by folder and purpose | `.agent/CODEBASE_INDEX.md` |
| What is tested and what is NOT verified | `.agent/TESTING_CHECKLIST.md` |
| Backend, frontend, database, testing, security, performance, directory-hygiene detail | `.agent/agents/*.md` (canonical); thin triggers at `.claude/skills/talksense-*` sharing `.agent/SPECIALIST_PREAMBLE.md` |
| Git workflow and review checklist / release gates | `.agent/DEVELOPMENT_RULES.md` / `.agent/RELEASE_CHECKLIST.md` |
