---
name: accuracy
description: >-
  Accuracy-critical verification gate for TalkSense AI ASR/Whisper/VAD, streaming and
  buffering/overlap, diarization, and scoring/metric changes. Invoke with /accuracy
  before making any WER/CER/F1/SCDR/accuracy claim or merging a change on the
  accuracy-critical surface. Enforces the L1-L5 ladder, ground-truth evidence tags,
  the L4 requirement for metric-moving changes, and flags changes that need a deeper
  design review.
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
---

# /accuracy — Accuracy-Critical Gate

A passing test is not an accuracy result. This gate decides what evidence a change
needs and refuses to let an accuracy claim stand without it.

Tracked changes: !`git diff --stat HEAD` · untracked files: !`git status --short -uall`
Scope hint (paths or proposed change), if given: $ARGUMENTS

Evaluate every path from both lists — tracked and untracked — in the scope check
below; a newly created file that has not been staged still counts.

Canonical references (consult, do not restate):
[`talksense-testing`](../talksense-testing/SKILL.md) hard stops ·
[`testing_agent.md`](../../../.agent/agents/testing_agent.md) "Testing Requirements for
Specific Feature Types" · [`backend_agent.md`](../../../.agent/agents/backend_agent.md)
"Escalation Conditions" · [`SPECIALIST_PREAMBLE.md`](../../../.agent/SPECIALIST_PREAMBLE.md)
ladder + audio-buffer invariants · [`DEVELOPMENT_RULES.md`](../../../.agent/DEVELOPMENT_RULES.md) §1.

## Step 1 — scope check (canonical accuracy-critical surface)

This list is the canonical accuracy-critical surface; `/verify` defers to it. The
change is on the surface if any tracked or untracked changed path is:

- `backend/audio/**` — Whisper model/params/device/language, VAD threshold or
  windowing, `audio/buffer.py` constants or overlap/merge logic;
- `backend/ws/audio_handler.py` — segment transcription, `_merge_overlapping_text`,
  transcript enrich, streaming/commit strategy;
- diarization code, or the `backend/services/nlp_engine.py` sentiment pipeline;
- `backend/engine/**` metric or scoring code, including
  `engine/conversation_engine.py` and `engine/scoring_profiles.py` weights;
- `backend/services/context_analyzer.py` — the locked functions or any other
  metric / scoring / insight code in that file;
- `backend/config/**` keyword or scoring data (e.g. `backend/config/keywords.json`);
- `backend/benchmark_dataset/**`, or any ground-truth file.

- No -> say so, defer to `/verify`, stop.
- Yes -> continue.

## Step 2 — metric-movement classification

- **Metric-moving** — can alter WER/CER, diarization F1/precision/recall/SCDR,
  sentiment labels, or any health/quality/ratio/interruption formula output.
  **L4 accuracy benchmark is required.** Name each metric that can move and its
  evidence source. Standing repo fact: no harness is wired to the live
  VAD -> Whisper -> Gemini path and WER is unbenchmarked, so a real ground-truth
  comparison must be built, not assumed; `backend/analytics_benchmark/` covers only
  the deterministic engine.
- **Non-metric-moving** — refactor with identical output/logging/typing. L1-L3
  acceptable, but the report must assert output-equivalence (same inputs -> identical
  outputs before and after).

## Step 3 — required evidence per surface

`testing_agent.md` "Testing Requirements for Specific Feature Types" is canonical.
Minimum, by surface:

- Transcription / `audio/buffer.py` / `initial_prompt`: WER before and after on a
  fixed audio file with a ground-truth transcript; timestamps compared against
  known-correct timing.
- Speaker attribution: F1, precision, recall, SCDR before and after on labelled audio.
- Scoring / locked `context_analyzer` functions: boundary tests (0 and 100 per
  dimension, output stays in [0, 100]) + meeting/sales/interview coverage + lock
  approval (`.agent/ACTIVE_FILES.md`).

## Step 4 — evidence tags and anti-fabrication

Tag every claim: `FUNCTIONAL` (ran without error) · `ACCURACY VERIFIED (<metric>,
<before> -> <after>)` · `NOT VERIFIED` (no test exists — state it, never omit).
Smoke and functional runs are never accuracy evidence.
`evaluation/mock_ground_truth.json` is synthetic dev data, not a benchmark.

1. Never state a WER/CER/F1/SCDR number not produced by a run in this session against
   real ground truth.
2. If no ground truth exists for the changed area, output `ACCURACY NOT VERIFIED` and
   stop. Do not estimate, interpolate, or infer a number.

## Step 5 — deeper-review trigger

Output `REQUIRES DESIGN REVIEW`, and do not present a lightweight check as
sufficient, for any change matching `backend_agent.md` "Escalation Conditions"
(canonical). That set includes: buffer flush thresholds or overlap strategy;
`initial_prompt` / `condition_on_previous_text` behavior; introducing real-time
speaker diarization; post-session pipeline prompt or response-schema changes; adding
an ML model to the startup sequence; scoring-profile weight changes
(meeting/sales/interview); or any edit to a locked `context_analyzer.py` function.
Also map the change to `DEVELOPMENT_RULES.md` §1.

## TARGET_DURATION_MS clause

`TARGET_DURATION_MS = 2000` in `backend/audio/buffer.py` is the **current
implementation value, not a permanent lock**. If an approved ASR/streaming design
changes it, the implementation plus the approved design become the source of truth
and the documentation (`.agent/SPECIALIST_PREAMBLE.md`, `.agent/agents/backend_agent.md`,
`CLAUDE.md`) must follow. Once an approved design exists, divergence from the old
documented value is not a violation. Absent an approved design, do not change it or
the other buffer constants.

## Report (fixed template)

```
## /accuracy report
- Surface: <on accuracy-critical surface? which changed paths (tracked + untracked)>
- Classification: <metric-moving | non-metric-moving>; metrics that can move: <list>
- Required evidence: <per surface, from Step 3>
- Evidence collected this session: <tag each: FUNCTIONAL | ACCURACY VERIFIED (metric, before -> after) | NOT VERIFIED>
- Ladder level reached: <L1..L4> (per SPECIALIST_PREAMBLE.md)
- Design review: <REQUIRES DESIGN REVIEW + reason | not triggered>
- Verdict: <ACCURACY VERIFIED | ACCURACY NOT VERIFIED | BLOCKED>
```
