# TalkSense AI — Production Release & Pre-Deployment Checklist

This checklist defines the operational verification steps required before deploying TalkSense AI v4 to a production-ready staging or live environment.

---

## 📋 Pre-Deployment Check

- [ ] **Git Branch Cleanliness**: Confirm all development features are integrated into the `dev` branch. Confirm no direct commits were pushed to the locked `main` branch.
- [ ] **Version Synchronization**: Update software version tags in both `backend/main.py` (`4.0.0`) and `talksense-ui/package.json`.
- [ ] **CI Pass Validation**: Ensure all backend unit/integration tests run successfully via `pytest` and the frontend builds without errors via `npm run build`.

---

## ⚙️ 1. Backend Release

- [ ] **Python Sandbox Alignment**: Verify the active python environment has all libraries in `backend/requirements.txt` installed.
- [ ] **Model Cold Warmup**: Test FastAPI service initialization. Verify that the startup lifespan successfully caches the Silero VAD, Faster-Whisper, and Sentiment transformer models without crashing.
- [ ] **Thread-Pool Offloader**: Confirm long-running model transcription calculations run inside non-blocking `run_in_threadpool` executors.

---

## 💻 2. Frontend Release

- [ ] **Production Build Bundler**: Compile assets using `npm run build`. Verify Vite outputs compiled bundles into the `talksense-ui/dist/` directory.
- [ ] **ONNX Runtime WASM Assets**: Verify that `ort-wasm-simd-threaded.wasm` and associated WASM support files are copied into the `talksense-ui/dist/vad/` (or public) folder to avoid WASM dynamic load 404 errors.
- [ ] **Production Base URL**: Confirm the frontend API service connector resolves URLs to the production API gateway (or environment-supplied endpoint) rather than `localhost:8000`.

---

## 🗄️ 3. Database Rollout

- [ ] **Relational PostgreSQL Setup**: Verify the target PostgreSQL database is active and running on Port 5432.
- [ ] **Schema Initialisation**: Run `alembic upgrade head` to create all database tables. Verify that all 8 relational tables (`users`, `clients`, `sessions`, `transcript_segments`, `session_metrics`, `analysis_results`, `alerts`, `client_snapshots`) are created.
- [ ] **Performance Indexes**: Confirm the following database indexes are applied:
  - `sessions(client_id)`
  - `transcript_segments(session_id)`
  - `alerts(session_id)`
  - `client_snapshots(client_id)`

---

## 🔑 4. Environment Variables Audit

Verify that the production environment contains the following keys with valid parameters:

- [ ] `DATABASE_URL`: Connection string (`postgresql+asyncpg://<user>:<pw>@<host>:5432/talksense`).
- [ ] `GEMINI_API_KEY`: Active Google AI Studio API key (required for post-session AI pipeline).
- [ ] `ENABLE_POST_SESSION_AI`: Set to `true` (enables post-session Gemini analysis).
- [ ] `WHISPER_MODEL`: Set to `small` (or `medium` depending on server GPU hardware capacity).
- [ ] `WHISPER_COMPUTE_TYPE`: Set to `int8` (to save VRAM memory).
- [ ] `WHISPER_DEVICE`: Set to `cuda` (or `cpu` for non-GPU staging).
- [ ] `JWT_SECRET_KEY`: Set to a secure, randomly generated 32-byte hexadecimal string.
- [ ] `ENV`: Set to `production` or `staging`.

---

## 🔒 5. Security Protocols

- [ ] **HTTPS Enforcements**: Enforce SSL connections at the gateway/reverse-proxy level. Enable secure WebSocket connections (`wss://`) for PCM audio streaming.
- [ ] **CORS Restrictions**: Limit origin domains in `CORS_ORIGINS` to the production frontend URL.
- [ ] **JWT Key Rotation**: Confirm the `JWT_SECRET_KEY` is retrieved from environment storage and is not a hardcoded fallback value.
- [ ] **Input Sanitization**: Ensure query fields and text segment streams filter SQL Injection strings and malicious payloads.

---

## ⚡ 6. Performance Optimization

- [ ] **VRAM Allocation Budget**: Verify the GPU maintains at least 500MB headroom to handle audio transcriber calculations.
- [ ] **WebSocket Backpressure**: Confirm the socket broadcaster drops metrics updates if a client connection buffer is saturated.
- [ ] **Sequential Model Pipeline**: Ensure Whisper and sentiment models do not run simultaneously on 4GB VRAM cards to prevent CUDA out-of-memory errors.

---

## 📊 7. Monitoring & Logging

- [ ] **Model Latency Logging**: Track Whisper processing times. Ensure warnings are triggered if speech segments take longer than 700ms to transcribe.
- [ ] **Error Redirects**: Set up error redirects to route application anomalies to persistent storage.
- [ ] **Log Retention**: Set up log rotation routines. Retain production logs for a minimum of 30 days.
