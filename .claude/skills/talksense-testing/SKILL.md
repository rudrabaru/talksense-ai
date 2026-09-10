---
name: talksense-testing
description: >-
  Testing specialist context for TalkSense AI. Use when selecting tests, judging
  regression coverage, writing tests, or making any test/verification claim —
  especially the distinction between FUNCTIONAL, ACCURACY VERIFIED, and NOT
  VERIFIED. Covers how to test a backend change, the test-existence map, per-feature
  testing requirements (transcription, speaker attribution, alert engine, scoring),
  and frontend E2E.
---

# TalkSense AI — Testing Specialist

Start with [`.agent/SPECIALIST_PREAMBLE.md`](../../../.agent/SPECIALIST_PREAMBLE.md)
(shared invariants, control docs, verification ladder L1–L5).

**Full detail:** [`.agent/agents/testing_agent.md`](../../../.agent/agents/testing_agent.md)
and [`.agent/TESTING_CHECKLIST.md`](../../../.agent/TESTING_CHECKLIST.md) — the
canonical test-existence map and per-feature evidence requirements.

## When this applies

Test strategy, test selection, regression discipline, and any verification claim in a
PR description or report.

## Fundamental rule

`TEST PASSES ≠ AI RESULT IS ACCURATE`. Every claim states its level:

- **FUNCTIONAL** — feature executed without error.
- **ACCURACY VERIFIED** — output compared against ground truth (state the metric:
  WER, speaker-attribution F1/precision/recall/SCDR, etc., before and after).
- **NOT VERIFIED** — no test exists for this area; say so explicitly, do not omit it.

## Hard stops

- Do not claim transcription / speaker / sentiment / health-score / interruption
  accuracy without ground-truth comparison evidence.
- Do not treat `evaluation/mock_ground_truth.json` results as an accuracy benchmark —
  it is synthetic dev data; it only proves the pipeline runs.
- Changes to `audio/transcriber.py`, `audio/buffer.py`, `initial_prompt` handling, or
  the locked `context_analyzer.py` functions require the evidence levels in the full
  document — never skip L4.

## Commands

Unit suite and E2E commands are in `CLAUDE.md` ("Verification commands").
`test_llm_engine.py` and `test_post_session_pipeline.py` fail to collect without
`google-genai` installed — known environment gap.
