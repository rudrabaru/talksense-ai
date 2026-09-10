# TalkSense AI — Production Release Checklist

**Status as of:** 2026-08-18
**Architecture reference:** `.agent/ARCHITECTURE.md`
**Project status reference:** `.agent/PROJECT_STATUS.md`

> **Critical distinctions used in this document:**
>
> **CODE COMPLETE** — the feature is implemented and runs without crashing.
> **FEATURE VERIFIED** — a functional test confirms the feature executes end-to-end.
> **ACCURACY VERIFIED** — the AI output has been validated against ground truth.
> **PRODUCTION READY** — all of the above, plus security, performance, and ops checks passed.
>
> These four levels are not equivalent. This checklist records which level each area has reached.

---

## Pre-Deployment Checks

- [ ] **Git branch cleanliness** — confirm all development work is integrated. Confirm no direct commits to `main` without review.
- [ ] **CI passing** — `backend-ci.yml`, `frontend-ci.yml`, and `qa_pipeline.yml` all pass on the target branch.
- [ ] **`google-genai` package installed** — `tests/test_llm_engine.py` and `tests/test_post_session_pipeline.py` fail collection locally if this package is absent. Verify it is available in the deployment environment.

---

## 1. Backend

### Model Startup

- [ ] **Silero VAD loads without error** — `FEATURE VERIFIED` (startup log)
  - `get_vad()` is called at startup and cached. Skipped in `ENV=test`.

- [ ] **Faster-Whisper loads without error** — `FEATURE VERIFIED` (startup log)
  - Model: `whisper_model` setting (default: `small`).
  - Compute: `whisper_compute_type` (default: `int8`).
  - Device: `whisper_device` (default: `cuda`; use `cpu` for non-GPU environments).

- [ ] **Sentiment Transformer loads without error** — `FEATURE VERIFIED` (startup log)
  - `get_nlp_engine()` called at startup and cached.

- [ ] **Pyannote diarizer** — `NOT APPLICABLE (current release)`
  - Real-time diarizer is explicitly set to `None`. No Pyannote model is loaded at startup.
  - Post-session speaker attribution is handled by Gemini LLM text inference, not acoustic diarization.
  - Do not document Pyannote as a loaded model.

- [ ] **Whisper `initial_prompt` behavior** — `CODE COMPLETE` / `ACCURACY NOT VERIFIED`
  - The last confirmed transcript segment text (up to 200 characters) is passed as `initial_prompt` to Whisper for each chunk.
  - This is intentional context conditioning. It has NOT been removed.
  - Accuracy impact (hallucination reduction or introduction) is not yet measured.

### Thread Safety

- [ ] **Whisper runs in thread pool** — `CODE COMPLETE`
  - `transcriber.transcribe_async()` uses `asyncio.run_in_executor` to avoid blocking the event loop.

- [ ] **GPU concurrency gated** — `CODE COMPLETE`
  - `gpu_concurrency` setting (default: 3) limits simultaneous GPU inference requests.

### Background Flusher

- [ ] **Session flusher starts** — `FEATURE VERIFIED` (startup log)
  - `start_flusher()` launches the `_flush_loop` coroutine at app startup.
  - Flush interval: `FLUSH_INTERVAL_SECONDS = 5.0`.

---

## 2. Frontend

- [ ] **Production build succeeds** — `FEATURE VERIFIED` (CI)
  - `npm run build` produces bundles in `talksense-ui/dist/`.

- [ ] **ONNX WASM assets present** — verify `ort-wasm-simd-threaded.wasm` is in the dist output.
  - Required for `@ricky0123/vad-web` (browser-side VAD).
  - Missing assets cause silent WASM load failures. No automated check exists for this.

- [ ] **API/WS URLs configured for environment** — confirm `VITE_API_URL` and `VITE_WS_URL` point to the correct backend, not `localhost`.

- [ ] **ESLint passes** — `FEATURE VERIFIED` (CI: `npm run lint`).

---

## 3. Database

- [ ] **PostgreSQL reachable on port 5432** — verify target DB is running before deployment.

- [ ] **Schema migration applies** — `FEATURE VERIFIED` (CI)
  - `alembic upgrade head` runs in CI and locally against test DB.
  - Verify against production DB before cutover.

- [ ] **All 8 tables present after migration:**
  - `users`, `clients`, `sessions`, `transcript_segments`, `session_metrics`, `analysis_results`, `alerts`, `client_snapshots`

- [ ] **Performance indexes present:**
  - `sessions(client_id)`
  - `transcript_segments(session_id)`
  - `alerts(session_id)`
  - `client_snapshots(client_id)`

- [ ] **Stale session recovery** — `CODE COMPLETE`
  - `recover_stale_sessions()` runs at startup to mark orphaned active/created sessions as interrupted.

---

## 4. Environment Variables

Verify all required environment variables are set before deploying:

| Variable | Required | Notes |
|----------|----------|-------|
| `DATABASE_URL` | Yes | `postgresql+asyncpg://<user>:<pw>@<host>:5432/talksense` |
| `GEMINI_API_KEY` | Yes (if post-session AI enabled) | Required for `run_post_session_pipeline` |
| `ENABLE_POST_SESSION_AI` | Yes | `true` to enable; `false` to skip post-session Gemini analysis |
| `WHISPER_MODEL` | Recommended | Default: `small`; `medium` for higher accuracy on adequate GPU |
| `WHISPER_COMPUTE_TYPE` | Recommended | Default: `int8` |
| `WHISPER_DEVICE` | Recommended | `cuda` for GPU; `cpu` for non-GPU environments |
| `JWT_SECRET_KEY` | Yes | Must be a securely generated value — not the default |
| `ENV` | Yes | `production` or `staging` |
| `CORS_ORIGINS` | Yes | Restrict to the production frontend URL |
| `HF_TOKEN` | Situational | Required only if loading gated Hugging Face models |

> **Security note:** `jwt_secret_key` defaults to `secrets.token_hex(32)` (auto-generated per process restart). In production, this must be set as a stable environment variable — otherwise all JWT tokens are invalidated on each restart.

---

## 5. Security

- [ ] **HTTPS / WSS enforced** — enforce SSL at the gateway/reverse-proxy. Audio streams use `wss://`.
- [ ] **CORS restricted** — `cors_origins` in config defaults to `http://localhost:5173`. This must be overridden to the production frontend URL before deployment.
- [ ] **JWT key is not default** — confirm `JWT_SECRET_KEY` is set in environment and not auto-generated at runtime.
- [ ] **No user authentication system exists** — there are no `/auth/register`, `/auth/login`, or `/auth/me` route handlers (they appear only in the `backend/main.py` module docstring) and no `get_current_user` dependency on any REST route. All REST endpoints are unauthenticated. The `/ws/transcript|metrics|alerts|status` subscription channels **do** verify the JWT `ws_token` via `verify_ws_token()` and close with code `1008` on failure; `/ws/audio/{session_id}` does **not** verify the token. Before any pilot or production exposure, either add a REST auth layer or explicitly document the REST surface as unauthenticated and rely on network isolation. Canonical detail: `.agent/agents/security_agent.md`; route status: `.agent/SKILLS.md` §6 and `.agent/API_CONTRACT.md` §Authentication.
- [ ] **Input validation** — text fields and query parameters pass through FastAPI/Pydantic schema validation. SQL injection is mitigated via SQLAlchemy parameterized queries.

---

## 6. Performance

- [ ] **GPU VRAM headroom** — verify at least 500MB free VRAM before deploying on 4GB GPU cards. Whisper and sentiment model share the GPU.
- [ ] **GPU semaphore configured** — `gpu_concurrency` setting (default: 3) prevents concurrent GPU overload. Adjust to hardware capacity.
- [ ] **WebSocket backpressure** — metrics broadcaster drops intermediate frames when client buffer is saturated (by design). Alert delivery is not dropped.

---

## 7. Known Limitations at Release (Accuracy)

The following items are **CODE COMPLETE** but **NOT ACCURACY VERIFIED**. They should be disclosed before any production deployment for evaluation or customer-facing use:

| Feature | Status | Impact |
|---------|--------|--------|
| Live speaker attribution | NOT WORKING (diarizer = None) | All live segments are "Speaker 1". Speaking ratio, roles, interruptions, speaker switches are wrong during live sessions. |
| Post-session speaker attribution | CODE COMPLETE / ACCURACY NOT VERIFIED | LLM re-attributes speakers from text; no ground-truth benchmark run. |
| SCDR (Speaker Change Detection Rate) | NOT MEASURED | Live SCDR = 0. Post-session SCDR not benchmarked against real data. |
| Interruption count | NOT WORKING in live sessions | Always 0 due to single-speaker collapse. |
| Health score | FUNCTIONAL / ACCURACY NOT VERIFIED | Produces values in [0,100] range; validity of scoring weights not independently validated. |
| Whisper transcription accuracy | NOT BENCHMARKED | WER not measured against ground-truth audio. |
| Timestamp alignment | LATENT CONCERN | DB timestamps vs WAV file timeline — coherent but untested under real conditions. |
| `latest_metrics.json` | SEEDED WITH MOCK DATA | `analytics_health` thresholds computed from a single-sample mock run, not real evaluation. |

---

## 8. Monitoring & Logging

- [ ] **Model latency logged** — Whisper processing time is logged per segment. Warning threshold for slow inference should be configured operationally.
- [ ] **Error logging** — FastAPI exception handlers log to stderr. Redirect to persistent storage in production.
- [ ] **Log rotation** — configure log rotation; retain production logs for at least 30 days.
- [ ] **Profiling** — `profiling_enabled = True` by default. Verify this is acceptable in production or disable it.

---

## 9. Release Gate Summary

| Gate | Current State |
|------|--------------|
| Backend unit tests pass (mocked) | PASS (local + CI, excluding `google-genai` tests) |
| Frontend E2E tests pass (mocked) | PASS (CI) |
| Schema migration applies | PASS (CI) |
| WebSocket smoke test | PASS (requires live server — QA pipeline) |
| Speaker attribution accuracy | **NOT MET** |
| SCDR benchmark | **NOT MET** |
| Interruption detection in live sessions | **NOT MET** |
| Health score accuracy validated | **NOT MET** |
| CORS locked to production domain | Pending configuration |
| JWT secret set as stable env var | Pending configuration |

> A "release" that ships before speaker attribution accuracy is validated should be explicitly scoped as an **evaluation / pilot release** with documented limitations, not a general-availability production release.

---

*This checklist reflects the repository state as of 2026-08-18. It must be updated before each deployment.*
