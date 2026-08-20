# TalkSense AI — Testing Checklist

**Status as of:** 2026-08-18
**Architecture reference:** `.agent/ARCHITECTURE.md`
**Project status reference:** `.agent/PROJECT_STATUS.md`

> **Critical distinction applied throughout this document:**
>
> **FUNCTIONAL TEST** — "Did the feature execute without error?"
> **ACCURACY TEST** — "Was the AI result correct?"
>
> These are not equivalent. A test passing does not imply a result is accurate.

---

## How to Read This Checklist

Each item is tagged with one or more of:

- `IMPLEMENTED` — test exists and is collected by pytest / Playwright
- `FUNCTIONAL ONLY` — test verifies execution, not correctness of AI output
- `ACCURACY VERIFIED` — test compares against ground truth
- `NOT VERIFIED` — no test exists for this area
- `MANUAL ONLY` — requires a human to observe behaviour
- `BROKEN` — infrastructure exists but test cannot currently run

---

## 1. Audio Ingestion Pipeline

### VAD (Silero VAD)

- [ ] **VAD speech/silence classification** — `NOT VERIFIED`
  - No unit test exists for `vad.is_speech()`.
  - Manual observation only: silence suppression during pause visible in server logs.

- [ ] **Buffer accumulation math** — `NOT VERIFIED`
  - No unit test verifies `AudioBuffer` PCM byte accumulation.
  - Buffer flushes at `TARGET_DURATION_MS = 2000ms` of speech (not 1000ms).
  - Silence-gap flush at `SILENCE_GAP_MS = 600ms`.
  - Minimum flush rejected below `MIN_FLUSH_MS = 800ms`.

- [ ] **Overlap retention on partial flush** — `NOT VERIFIED`
  - `OVERLAP_MS = 1000ms` retained on partial flushes.
  - No test verifies overlap byte count or that trailing speech is not dropped.

- [ ] **WAV file lifecycle** — `NOT VERIFIED`
  - No test verifies WAV header rewrite on `flush_remaining()`.
  - No test verifies session WAV file is created, written, and closed correctly.

### Whisper Transcription

- [ ] **Whisper execution** — `NOT VERIFIED` (integration)
  - No automated test runs Whisper against real or synthetic audio.
  - CI runs with `WHISPER_DEVICE=cpu` and no audio fixtures, so Whisper is never actually invoked in CI.

- [ ] **`initial_prompt` conditioning** — `NOT VERIFIED` (accuracy)
  - Code passes `prev_text[-200:]` as `initial_prompt` to Whisper for context conditioning.
  - **Note:** This is NOT the same as setting `initial_prompt=None`. The previous-text prompt injection is still active.
  - No regression test verifies whether prompt conditioning reduces or introduces hallucination.

- [ ] **Timestamp accuracy** — `NOT VERIFIED`
  - No test compares Whisper-produced segment timestamps against known-correct timing.

- [ ] **Transcript overlap deduplication** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - `tests/test_fixes.py::test_transcript_merge` — verifies `_merge_overlapping_text()` on 5 text-level cases.
  - Does NOT verify acoustic timestamp alignment or behaviour when Whisper transcribes the same audio differently across chunks.

### Long Silence Detection

- [ ] **Long silence trigger** — `NOT VERIFIED`
  - `AlertEngine._check_long_silence()` fires when `state.last_silence_seconds > 8`.
  - The `last_silence_seconds` value is populated from the audio byte clock + VAD state.
  - No automated test injects silence and verifies the alert fires at the correct threshold.

---

## 2. Backend Analytics Engine

### Health Score

- [ ] **Scoring formula boundary test** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - `tests/test_meeting_health.py::test_meeting_health_scenarios` tests 5 scenarios against `evaluate_meeting_health()`.
  - Verifies logic branches (blockers, decisions, sentiment, override) for meeting mode.
  - Does NOT test sales or interview mode profiles.
  - Does NOT test `compute_health_score()` directly or its `[0, 100]` clamp.

- [ ] **Meeting quality (`compute_meeting_quality_v2`)** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - `tests/test_meeting_quality_refactor.py` — tests blockers, ownership, decision detection.
  - Tests logic branches only, not AI output accuracy.

### Alert Engine

- [ ] **Alert cooldown (30 seconds)** — `NOT VERIFIED`
  - `COOLDOWN_SECONDS = 30` applies to all alert types including speaking dominance.
  - No unit test verifies the cooldown prevents re-fire within the window.
  - The existing checklist note about a 30-second cooldown is **correct per current code**.

- [ ] **Alert cap at 3 active alerts** — `NOT VERIFIED`
  - `MAX_ACTIVE_ALERTS = 3` defined but eviction is handled via `alert_log` + `flushed_alert_ids`.
  - No test verifies that a 4th concurrent alert evicts the oldest.

- [ ] **Speaking dominance alert** — `NOT VERIFIED`
  - Fires when a single speaker exceeds 65% of total duration after 15s of conversation.
  - **Known limitation:** All live segments are labeled "Speaker 1" (diarizer is `None`), so this alert fires on "System" rather than a real speaker identity during live sessions.

- [ ] **Interruption alert** — `NOT VERIFIED`
  - Fires on `state.interruptions >= last_interruptions + 2`.
  - **Known limitation:** Interruption count is always 0 in live sessions because speaker differentiation is absent (all "Speaker 1").

- [ ] **Excessive filler alert** — `NOT VERIFIED`
  - Fires on a jump of ≥3 filler words since last fire.
  - No test provides filler-laden audio and verifies the alert triggers.

### Session Lifecycle

- [ ] **Session creation, status transitions, end** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - `tests/test_session_manager_post_session_ai.py` — 4 tests verify:
    - Post-session AI is NOT scheduled when feature flag is disabled.
    - Post-session AI IS scheduled as a named task when feature flag is enabled.
    - Pipeline is NOT scheduled on FAILED sessions (only COMPLETED).
    - Pipeline exception does not prevent session cleanup.
  - All DB and pipeline calls are mocked. No real DB is used.

- [ ] **5-second flush persistence** — `NOT VERIFIED`
  - `FLUSH_INTERVAL_SECONDS = 5.0` defined in session_manager.
  - No automated test verifies transcript/metric rows appear in PostgreSQL within 5 seconds of audio ingestion.

- [ ] **Session crash recovery** — `MANUAL ONLY`
  - `db/crud.recover_stale_sessions()` runs at startup to transition orphaned sessions.
  - No automated test simulates mid-session crash and verifies recovery.

### Post-Session AI Pipeline

- [ ] **Post-session pipeline invocation** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - Covered by `test_session_manager_post_session_ai.py` (mocked pipeline, not real LLM).

- [ ] **LLM response validation** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - `tests/test_response_validator.py` — 13 tests cover JSON extraction, schema validation, missing fields, wrong types, malformed JSON.
  - Tests validate the parsing layer. They do NOT verify that LLM outputs are semantically correct.

- [ ] **Post-session metric recomputation after diarization** — `NOT VERIFIED`
  - After post-session AI updates speaker labels, `speaking_ratio` and `participation` are recalculated from DB segments.
  - `health_score`, `interruptions`, `speaker_switches`, `roles` are **not** recomputed — they remain frozen at live-session values.
  - No test verifies that dashboard data is consistent after post-session AI completes.

### NLP / Sentiment

- [ ] **Sentiment logic** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - `tests/test_sentiment_logic.py::test_business_sentiment` — verifies business-context sentiment rules.
  - Does NOT verify Transformer model accuracy against labelled data.

- [ ] **Objection detection** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - `tests/test_objection_handling.py` — tests objection classification logic.
  - Keyword-matching accuracy against real speech is `NOT VERIFIED`.

---

## 3. WebSocket Communication

### Smoke / Integration Tests

- [ ] **WebSocket session lifecycle (requires running server)** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - `tests/smoke_test_ws.py` — excluded from CI unit-test run; requires live uvicorn + PostgreSQL.
  - Verifies: health endpoint, session creation, WebSocket connect/send/end, dashboard response, objection detection via `inject:` command.
  - Tests that the feature **executes**; does not verify that injected text produces accurate objection classification.

### WebSocket Channels

- [ ] **Channel subscription and disconnect** — `NOT VERIFIED`
  - 5 WebSocket channels: `/ws/audio/{id}`, `/ws/transcript/{id}`, `/ws/metrics/{id}`, `/ws/alerts/{id}`, `/ws/status/{id}`.
  - No unit test verifies registration/deregistration on disconnect.

- [ ] **Metrics backpressure (drop latest vs oldest)** — `NOT VERIFIED`
- [ ] **Alert delivery guarantee** — `NOT VERIFIED`
- [ ] **Ping/pong heartbeat** — `NOT VERIFIED`

---

## 4. Database & Persistence

- [ ] **CRUD helper correctness** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - `tests/test_history_api.py`, `tests/test_client_memory.py` — test CRUD operations with mocked or in-memory state.

- [ ] **Schema migration** — `IMPLEMENTED` (CI)
  - `alembic upgrade head` runs in CI against a real PostgreSQL instance.
  - Verifies schema can be applied without error. Does not verify data integrity or index presence.

- [ ] **Audio file persistence** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - `tests/test_audio_playback.py` — 5 tests cover audio file serving, missing session, no audio, missing file, path safety checks.

- [ ] **Client snapshot generation** — `NOT VERIFIED`
  - No test verifies that `client_snapshots` are populated after session end.

---

## 5. Frontend

### E2E Tests (Playwright — mocked APIs)

All Playwright tests mock backend API calls and WebSocket connections. They test UI behaviour with synthetic data only.

- [ ] **Navigation and routing** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - `tests/e2e/navigation.spec.ts`, `navigation_launch.spec.ts` — verify page routing.

- [ ] **Session lifecycle UI** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - `tests/e2e/recording.spec.ts` — verifies Start → Pause → History navigation flow.

- [ ] **Dashboard metrics rendering** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - `tests/e2e/dashboard_metrics.spec.ts` — sends mock WebSocket metrics payload, verifies values appear in DOM.

- [ ] **Transcript rendering** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - `tests/e2e/transcript.spec.ts` — verifies transcript segments render from mock data.

- [ ] **Error handling** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - `tests/e2e/error_handling.spec.ts` — tests UI error states.

- [ ] **History / sessions page** — `IMPLEMENTED` / `FUNCTIONAL ONLY`
  - `tests/e2e/history.spec.ts` — verifies session list rendering from mock data.

### Not Covered by Automated Tests

- [ ] `useAudioCapture` hook (PCM conversion) — `NOT VERIFIED`
- [ ] `useSessionWebSocket` reconnect with exponential backoff — `NOT VERIFIED`
- [ ] Responsive layout at various viewport widths — `MANUAL ONLY`
- [ ] Alert animation on critical alert — `MANUAL ONLY`
- [ ] Auto-scroll in transcript panel — `MANUAL ONLY`
- [ ] ONNX WASM asset loading (`ort-wasm-simd-threaded.wasm`) — `NOT VERIFIED` (automated)

---

## 6. Speaker Attribution & Diarization

> **This section requires particular attention because speaker attribution is the source of cascading errors across multiple metrics.**

- [ ] **Live speaker differentiation** — `NOT VERIFIED` / `KNOWN BROKEN`
  - The real-time diarizer is `None`. All live segments are assigned to "Speaker 1".
  - This makes speaking ratio, interruptions, speaker switches, roles, and health score incorrect during live sessions.

- [ ] **Post-session speaker attribution accuracy** — `NOT VERIFIED`
  - Post-session AI (Gemini LLM) re-attributes speakers from transcript text only (no audio signal).
  - No evaluation has been run against a ground-truth labelled audio dataset.
  - `evaluate_speaker_accuracy.py` exists and has been restored. `latest_metrics.json` has been populated with a single-sample mock run (not a real benchmark).

- [ ] **SCDR (Speaker Change Detection Rate)** — `NOT VERIFIED`
  - `compute_scdr()` function is defined in `evaluate_speaker_accuracy.py`.
  - No real session has produced a non-zero SCDR value.
  - Live sessions always produce SCDR = 0 (no speaker changes detected).

- [ ] **Timestamp alignment (DB segments vs WAV file)** — `NOT VERIFIED`
  - DB segment timestamps are derived from buffer byte positions, which include silence.
  - No test verifies timestamp coherence across overlapping chunks.

---

## 7. CI Pipeline Coverage

| Stage | What It Tests | Accuracy |
|-------|---------------|----------|
| `backend-ci.yml` — pytest | Unit tests (mocked DB, mocked pipeline) | Functional only |
| `backend-ci.yml` — Black/Ruff/Pyright | Code style and type correctness | N/A |
| `backend-ci.yml` — Alembic | Schema migration applies without error | Functional only |
| `frontend-ci.yml` — ESLint | JS linting | N/A |
| `frontend-ci.yml` — Playwright | UI behaviour with mocked APIs | Functional only |
| `qa_pipeline.yml` — smoke_test_ws.py | Live server WebSocket integration | Functional only |
| `integration-ci.yml` | (Not inspected in this audit) | Unknown |

> **Note:** Two test files currently fail collection in the local environment:
> - `tests/test_llm_engine.py` — `ModuleNotFoundError: No module named 'google.genai'`
> - `tests/test_post_session_pipeline.py` — same root cause
>
> These require `google-genai` installed. They are not in the standard `requirements.txt`.
> They are excluded from the CI ignore list and may fail in environments without this package.

---

## 8. Accuracy Gaps Summary (Items Requiring Human Validation)

The following accuracy claims cannot currently be validated by any automated test:

| Area | Current Status |
|------|----------------|
| Whisper transcription word error rate | NOT VERIFIED |
| Whisper timestamp accuracy | NOT VERIFIED |
| Speaker attribution F1 / SCDR | NOT VERIFIED (benchmark pipeline not run against real data) |
| Sentiment label correctness | NOT VERIFIED |
| Objection detection precision/recall | NOT VERIFIED |
| Buying signal detection precision/recall | NOT VERIFIED |
| Health score validity (is 72 actually "good"?) | NOT VERIFIED |
| Interruption detection accuracy | NOT VERIFIED (and known broken in live sessions) |
| Long silence threshold correctness (8s) | NOT VERIFIED |
| Speaking dominance threshold (65%) | NOT VERIFIED |
| Alert message relevance | NOT VERIFIED |

---

*This checklist reflects the repository state as of 2026-08-18. It must be updated when new tests are added or accuracy benchmarks are run.*
