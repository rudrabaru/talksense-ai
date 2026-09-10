---
name: talksense-backend
description: >-
  Backend specialist context for TalkSense AI. Use when changing anything under
  backend/ — FastAPI routes in main.py, the audio pipeline (audio/vad.py,
  audio/buffer.py, audio/transcriber.py), conversation_engine, alert_engine,
  ws/audio_handler.py, ws/session_manager.py, services/ (nlp_engine,
  context_analyzer, post_session_pipeline, llm_engine, prompt_loader,
  response_validator), or session lifecycle. Covers backend invariants, forbidden
  changes, required pre-merge checks, and escalation conditions.
---

# TalkSense AI — Backend Specialist

Start with [`.agent/SPECIALIST_PREAMBLE.md`](../../../.agent/SPECIALIST_PREAMBLE.md)
(shared invariants, control docs, verification ladder).

**Full detail:** [`.agent/agents/backend_agent.md`](../../../.agent/agents/backend_agent.md)
— canonical directory ownership map, per-subsystem invariants, and checklists. Read
it before non-trivial backend work.

## When this applies

Any change under `backend/` except database schema/migrations (see
`talksense-database`), the React app (`talksense-frontend`), or security policy
(`talksense-security`).

## Hard stops

- Do not modify the locked functions in `context_analyzer.py`
  (`compute_meeting_quality_v2`, `compose_executive_summary_v2`,
  `generate_key_insights_v2`) or the `nlp_engine.py` sentiment singleton init.
- Do not change buffer constants (`TARGET_DURATION_MS`, `OVERLAP_MS`,
  `SILENCE_GAP_MS`, `MIN_FLUSH_MS`) outside an approved ASR/streaming design.
- Do not run Whisper via a blocking call — always `run_in_executor` / threadpool.
- Do not bypass the `gpu_concurrency` semaphore in `audio/gpu_manager.py`.
- Do not introduce Pyannote/diart in the live pipeline; do not create `audio/diarizer.py`.
- Do not use `Base.metadata.create_all()`; do not delete the batch `POST /analyze` path.
- Do not change `initial_prompt` / `condition_on_previous_text` behavior without a
  team decision (see `.agent/DECISION_LOG.md`).

## Before merging

- Payloads match `.agent/API_CONTRACT.md`.
- GPU model loads stay singleton and sequential; DB writes stay async/background.
- Alert cooldown (`COOLDOWN_SECONDS = 30`) and cap (`MAX_ACTIVE_ALERTS = 3`) unchanged.
- `process_segments()` watermark logic and `session_manager.end()` final-flush
  sequence not bypassed.
- Verify at the ladder level that could disprove the change; never skip L4 accuracy
  checks when the change can move WER, sentiment, or a metric formula.
