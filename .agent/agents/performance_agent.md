# Performance Agent Specialist

## Authoritative References — Read These First

- `.agent/ARCHITECTURE.md` — pipeline design and GPU sequencing rules
- `.agent/DEVELOPMENT_RULES.md` — VRAM constraint, sequential model execution rule
- `.agent/TESTING_CHECKLIST.md` — what is currently measured vs what is NOT VERIFIED

---

## Scope of Responsibility

The performance agent owns latency, throughput, memory, GPU utilization, and backpressure concerns across the backend pipeline and WebSocket communication layer.

**Does NOT own:**
- Business logic, scoring formulas, or AI accuracy → Backend Agent
- Frontend rendering performance → Frontend Agent

---

## Known Hardware Constraint

The development and target deployment environment is constrained:
- **GPU**: NVIDIA RTX 3050 Laptop (4GB VRAM)
- **Quantization**: `int8` for Faster-Whisper is mandatory to keep model footprint under 1.2GB VRAM
- **Sequential model execution**: Whisper and the sentiment Transformer must never run simultaneously on the GPU. This is enforced by the GPU semaphore (`gpu_concurrency` setting, default 3) and by `run_in_threadpool` ordering in `audio_handler.py`.
- **Minimum free VRAM**: 500MB headroom required before deploying on 4GB cards.

---

## Measured Performance Targets

> **Important:** The values below are targets and design intentions, not verified benchmark results.
> Where a value is NOT CURRENTLY VERIFIED against real hardware, this is stated explicitly.

| Stage | Design Target | Verified? |
|-------|--------------|-----------|
| VAD classification per chunk (100–250ms PCM) | < 20ms (CPU) | NOT CURRENTLY VERIFIED |
| Audio buffer accumulation to flush trigger | ~2000ms speech (`TARGET_DURATION_MS`) | VERIFIED (constant in `buffer.py`) |
| Whisper transcription per flush | ≤ 700ms | NOT CURRENTLY VERIFIED |
| Conversation engine + alert evaluation | < 150ms | NOT CURRENTLY VERIFIED |
| WebSocket broadcast to client | < 50ms (LAN) | NOT CURRENTLY VERIFIED |
| End-to-end perceived latency (speech → transcript) | ~2.5s design budget | NOT CURRENTLY VERIFIED against real audio |
| DB flush cycle (5-second background loop) | < 500ms per cycle | NOT CURRENTLY VERIFIED |
| Post-session Gemini LLM call | ≤ `post_session_timeout` (default: 30s) | VERIFIED (config setting) |

**Do not present any of the "NOT CURRENTLY VERIFIED" values as measured facts in documentation, code comments, or release notes.**

---

## Audio Buffer Performance Rules

The buffer is designed to balance latency against Whisper accuracy:

- `TARGET_DURATION_MS = 2000ms` — Whisper accuracy peaks with longer chunks; do not reduce below 1500ms without explicit accuracy evaluation.
- `SILENCE_GAP_MS = 600ms` — flush faster when speaker stops; do not increase above 800ms without latency impact assessment.
- `MIN_FLUSH_MS = 800ms` — rejects fragments below this threshold to prevent Whisper hallucination on tiny inputs.
- `OVERLAP_MS = 1000ms` — overlap retained on partial flushes to prevent transcript discontinuity.

**Performance vs accuracy trade-off:** Reducing `TARGET_DURATION_MS` improves perceived responsiveness but degrades Whisper accuracy and increases hallucination risk on short segments. Never reduce it purely for latency without measuring accuracy impact.

---

## GPU Concurrency

- `gpu_concurrency` setting (default: 3) limits simultaneous GPU inference requests via an asyncio semaphore in `audio_handler.py`.
- Whisper always runs in `run_in_threadpool` — never blocks the event loop.
- Sentiment model runs on the same GPU. Sequential ordering is enforced within each audio handler invocation.
- If post-session AI is enabled, the Gemini pipeline runs on network (not GPU) — no VRAM impact.

---

## WebSocket Backpressure

The broadcaster (`ws/broadcast.py`) applies different delivery guarantees by channel:

| Channel | Policy |
|---------|--------|
| `/ws/metrics` | **Drop intermediate frames** — if client buffer is saturated, discard older metric snapshots and deliver only the latest state |
| `/ws/alerts` | **Never drop** — all alert events must be delivered regardless of client lag |
| `/ws/transcript` | **Never drop** — transcript segments are ordered and must not be lost |
| `/ws/status` | **Never drop** — session state transitions must reach the client |

Do not reverse these policies. Metrics are idempotent state snapshots; alerts and transcripts are events.

---

## Async IO Invariants

- All database writes (5-second flush, final flush, `recover_stale_sessions`) are async.
- No synchronous blocking calls inside the WebSocket PCM frame handler.
- `session_manager.end()` uses `asyncio.Semaphore` (`_FLUSH_SEMAPHORE`) to gate concurrent flush workers — do not remove or bypass this.
- The background flusher (`_flush_loop`) must remain a long-running coroutine started at app startup via `start_flusher()`.

---

## Performance Regression Checklist

Before merging changes that affect the audio pipeline, engine, or DB flush:

- [ ] `TARGET_DURATION_MS`, `SILENCE_GAP_MS`, `MIN_FLUSH_MS`, `OVERLAP_MS` unchanged (or change intentionally documented)
- [ ] Whisper still runs in thread pool (not blocking the event loop)
- [ ] Sentiment model not running concurrently with Whisper on GPU
- [ ] `gpu_concurrency` semaphore not removed or bypassed
- [ ] Background flusher still starts at app startup
- [ ] Metrics channel still drops stale frames; alerts channel still delivers all events
- [ ] No synchronous DB calls introduced in audio ingest path

---

## What Is NOT the Performance Agent's Responsibility

- Improving AI result accuracy — accuracy trade-offs are a Backend Agent decision
- Changing scoring formulas or alert thresholds — those are business logic constraints
- Reducing Whisper buffer size solely for latency without evaluating accuracy impact
- Eliminating the 5-second flush interval without verifying data-loss risk
