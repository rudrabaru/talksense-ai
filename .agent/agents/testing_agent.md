# Testing Agent Specialist

## Authoritative References — Read These First

**The definitive record of what is and is not tested is in:**

`.agent/TESTING_CHECKLIST.md` — read this before any testing work.

Also read:
- `.agent/ARCHITECTURE.md` — to understand what each component does
- `.agent/PROJECT_STATUS.md` — to understand what is implemented
- `.agent/DEVELOPMENT_RULES.md` — PR merge requirements

---

## Scope of Responsibility

The testing agent owns test strategy, test selection, regression coverage, and the discipline of distinguishing functional from accuracy verification. It does not own the application under test.

---

## Fundamental Rule

```
TEST PASSES  ≠  AI RESULT IS ACCURATE
```

This distinction is critical for every AI-involving feature in TalkSense AI.

A test that calls `transcribe_async()` and receives a string proves the transcriber executed. It does not prove the transcript is correct, timestamps are accurate, or speaker assignment is right.

Every test claim in this document, in documentation, and in PR descriptions must explicitly state which level has been achieved:

| Level | Meaning |
|-------|---------|
| **FUNCTIONAL** | Feature executed without error |
| **ACCURACY VERIFIED** | Output compared against ground truth |
| **NOT VERIFIED** | No test exists for this area |

---

## How to Test a Backend Change

### Step 1 — Run the unit test suite

```bash
cd backend
pytest tests/ \
  --ignore=tests/smoke_test_ws.py \
  --ignore=tests/validate_pipeline.py \
  --ignore=tests/run_verification.py
```

Two tests will **fail to collect** without `google-genai` installed:
- `tests/test_llm_engine.py`
- `tests/test_post_session_pipeline.py`

This is a known environment gap. These require `google-genai` which is not in `requirements.txt`.

### Step 2 — Run the smoke test (requires live server + PostgreSQL)

```bash
# In a separate terminal: start the server
cd backend && uvicorn main:app

# Then run the smoke test
cd backend && python tests/smoke_test_ws.py
```

The smoke test verifies end-to-end session lifecycle using an `inject:` text command. It does **not** test real audio. It does **not** verify AI accuracy.

### Step 3 — Run the evaluation pipeline (if changes affect analytics)

```bash
cd backend
python evaluation/evaluate_analytics.py \
  --session-id <id> \
  --ground-truth evaluation/mock_ground_truth.json
```

**Note:** `mock_ground_truth.json` contains synthetic data seeded for development. Results against mock data confirm the evaluation pipeline runs — they do NOT constitute an accuracy benchmark.

---

## Test Existence Map

Consult `.agent/TESTING_CHECKLIST.md` for the full map. Summary:

| Area | Test Type | Exists? |
|------|-----------|---------|
| VAD speech/silence | Unit | ❌ NOT VERIFIED |
| Buffer flush thresholds | Unit | ❌ NOT VERIFIED |
| Whisper transcription (real audio) | Integration | ❌ NOT VERIFIED |
| Transcript overlap deduplication | Unit/Functional | ✅ `test_fixes.py` |
| Meeting health scoring | Unit/Functional | ✅ `test_meeting_health.py` |
| Alert cooldown enforcement | Unit | ❌ NOT VERIFIED |
| Alert cap (max 3) | Unit | ❌ NOT VERIFIED |
| Session lifecycle (post-session AI gating) | Unit/Functional | ✅ `test_session_manager_post_session_ai.py` |
| LLM response validation | Unit/Functional | ✅ `test_response_validator.py` |
| DB CRUD operations | Unit/Functional | ✅ `test_history_api.py`, `test_client_memory.py` |
| Audio file serving | Unit/Functional | ✅ `test_audio_playback.py` |
| WebSocket channel lifecycle | Integration | ❌ NOT VERIFIED (automated) |
| Speaker attribution accuracy | Accuracy | ❌ NOT VERIFIED |
| Interruption detection | Unit | ❌ NOT VERIFIED |
| Long silence threshold | Unit | ❌ NOT VERIFIED |
| Frontend routing | E2E/Functional | ✅ Playwright specs |
| Dashboard metrics render | E2E/Functional | ✅ Playwright (mocked WS) |
| WS reconnect + backoff | Unit | ❌ NOT VERIFIED |
| Sentiment accuracy | Accuracy | ❌ NOT VERIFIED |

---

## Testing Requirements for Specific Feature Types

### Transcription Changes

Any change to `audio/transcriber.py`, `audio/buffer.py`, or `initial_prompt` handling requires:

1. **Functional evidence**: smoke test passes with an injected text payload.
2. **Accuracy evidence** (if claiming improved accuracy): compare Whisper output against ground-truth transcript for the same audio file. State WER (word error rate) before and after. Do not claim accuracy improvement without this.
3. **Timestamp evidence**: if timestamps are affected, compare start/end offsets against known-correct timing.

### Speaker Attribution Changes

Any change to speaker label assignment (live or post-session) requires:

1. **Functional evidence**: pipeline runs without error.
2. **Accuracy evidence**: compare speaker labels against ground-truth labelled audio. State speaker-attribution F1, precision, recall, and SCDR before and after.
3. Do not claim "improved speaker attribution" without ground-truth comparison.

### Alert Engine Changes

Any change to `engine/alert_engine.py` requires tests covering all four cases:

1. **Trigger**: alert fires when condition threshold is crossed.
2. **Cooldown**: same alert type does not re-fire within `COOLDOWN_SECONDS = 30`.
3. **Resolution**: alert resolves when condition is no longer met.
4. **Duplicate suppression**: duplicate messages are not broadcast.

These four cases do not currently have automated unit tests. If you change the alert engine, write them first.

### Interruption Detection Changes

Currently all live sessions produce `interruptions = 0` because `diarizer = None`. Any future interruption detection work requires:

1. Synthetic controlled cases (speaker A interrupts speaker B mid-utterance).
2. False-positive cases (rapid turn-taking vs true interruption).
3. False-negative cases (clear interruption that should be detected).
4. Timestamp boundary cases (near-simultaneous segment end/start).

Do not restore or add interruption counting until speaker differentiation works in live sessions.

### Scoring Formula Changes

Any change to `compute_health_score()` or the three locked functions in `context_analyzer.py` requires:

- Explicit approval (these functions are locked per `ACTIVE_FILES.md`).
- Boundary test: inputs of 0 and 100 for all metric dimensions; output must remain in [0, 100].
- Mode coverage: meeting, sales, and interview profiles.

---

## Frontend Testing

Run Playwright E2E:

```bash
cd talksense-ui
npm run test:e2e
```

All Playwright tests mock backend APIs and WebSocket calls. They verify UI behaviour with synthetic data only. They are **functional tests**, not integration tests.

`useAudioCapture.js` and `useSessionWebSocket.js` are not covered by automated tests. Manual verification is required for:
- PCM capture correctness (16kHz, mono, 16-bit)
- WS reconnect with exponential backoff
- ONNX WASM asset loading

---

## Regression Testing Discipline

Before merging any change:

1. Run the full pytest suite (minus ignored files).
2. Run `npm run test:e2e` for any frontend change.
3. If the change touches the audio pipeline, transcription, or speaker attribution: explicitly state in the PR what level of verification was achieved (FUNCTIONAL / ACCURACY VERIFIED / NOT VERIFIED) and why.
4. If you are claiming accuracy improvement, attach ground-truth comparison evidence.
5. If no accuracy test infrastructure exists for the area you changed, state `ACCURACY NOT VERIFIED` in the PR description — do not omit it.

---

## What Testing Cannot Claim Without Evidence

- That transcription is accurate
- That speaker attribution is correct
- That sentiment labels are correct
- That health scores are valid
- That interruptions are correctly counted
- That long-silence threshold (8s) is correct for the use case
- That speaking-dominance threshold (65%) is correct
- That the evaluation pipeline produces meaningful results (current run uses mock data only)
