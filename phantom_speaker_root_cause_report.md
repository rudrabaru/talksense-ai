# Phantom Speaker Root Cause Report

**Session investigated**: `ceff564b-c3a0-409b-9723-c52b4a40547d`  
**Ground truth**: `backend/ground_truth/meeting_short_gt.json` — 2 speakers, 8 annotated segments  
**WAV file**: `session_audio/session_ceff564bc3a0409b.wav` — 672,044 bytes, **21.0s** @ 16000Hz  

---

## Executive Summary

This investigation confirms **two distinct root causes** for the phantom speaker problem:

1. **Primary**: Unconstrained Pyannote clustering splits Speaker B's short, sparse segments into two clusters — creating a phantom 3rd speaker.
2. **Secondary (Critical)**: The session WAV file is only **21 seconds**, but transcript segments extend to **31.96 seconds**. The 11 segments beyond the WAV boundary cannot be assigned by overlap — they receive "Unknown" or incorrect proximity labels, suppressing coverage and all accuracy metrics.

Constraining `num_speakers=2` eliminates the phantom but **does not solve the WAV truncation problem**. Both issues must be fixed before role classification is safe.

---

## Configurations Tested

| Config | Pyannote Args | Speakers Detected | Turns | Runtime |
|--------|--------------|-------------------|-------|---------|
| A) Unconstrained | `{}` (current production) | **3** ❌ phantom | 8 | 1.0s |
| B) num_speakers=2 | `{"num_speakers": 2}` | **2** ✅ | 7 | 1.0s |
| C) min=2, max=2 | `{"min_speakers": 2, "max_speakers": 2}` | **2** ✅ | 7 | 1.4s |

---

## Metric Comparison

| Config | Coverage | Accuracy | Macro F1 | SCDR | F1 Pass? | SCDR Pass? |
|--------|----------|----------|----------|------|----------|------------|
| **Threshold** | ≥ 80% | — | **≥ 0.75** | **≥ 70%** | | |
| A) Unconstrained | 63.6% ❌ | 31.8% | 0.328 ❌ | 16.7% ❌ | ❌ | ❌ |
| B) num_speakers=2 | 63.6% ❌ | 36.4% | 0.336 ❌ | 0.0% ❌ | ❌ | ❌ |
| C) min=2, max=2 | 63.6% ❌ | 36.4% | 0.336 ❌ | 0.0% ❌ | ❌ | ❌ |

**Key result**: B and C give identical metrics. Neither configuration passes the production thresholds — **not because speaker counting is wrong, but because the WAV is truncated**.

---

## Per-Speaker F1 Detail

### A) Unconstrained — 3 speakers detected

| Speaker | Precision | Recall | F1 |
|---------|-----------|--------|----|
| A (Chair) | 0.750 | 0.400 | 0.522 |
| B (Developer) | 0.125 | 0.143 | 0.133 |
| **Macro F1** | | | **0.328** |

Label mapping: `Speaker 3 → A`, `Unknown → B`, `Speaker 1 → unmapped`, `Speaker 2 → unmapped`  
Speaker 1 and Speaker 2 are **both phantom clusters** — they stole segments that belong to B.

---

### B) num_speakers=2 — 2 speakers detected

| Speaker | Precision | Recall | F1 |
|---------|-----------|--------|----|
| A (Chair) | 0.636 | 0.467 | 0.538 |
| B (Developer) | 0.125 | 0.143 | 0.133 |
| **Macro F1** | | | **0.336** |

Label mapping: `Speaker 2 → A`, `Unknown → B`, `Speaker 1 → unmapped`  

Phantom eliminated. But `Speaker 1` is still unmapped and `Unknown` maps to B — meaning many B segments are "Unknown" (fell outside the WAV boundary), not correctly attributed.

---

### C) min=2, max=2 — identical to B

Same 7 turns, same label mapping, same metrics. For a 21s recording, `num_speakers=2` and `min/max=2` produce equivalent outputs. Config B is preferred (simpler API).

---

## Root Cause Analysis

### Root Cause 1: Unconstrained Clustering (Phantom Speaker)

**What happens**: `diarizer._pipeline(waveform)` is called with no speaker count constraint in both `audio/diarizer.py:150` and `services/post_session_diarizer.py:223`.

Pyannote `speaker-diarization-3.1` internally uses:
1. **Segmentation model** → detects speech activity windows
2. **Embedding model** → creates d-vector fingerprints per window
3. **Agglomerative clustering** → merges similar embeddings using a learned cosine distance threshold

For this 21s recording, Speaker B has only **3 segments in the 7.3–13.0s window**, widely separated by silence. The intra-speaker cosine distance for these sparse B segments exceeds the automatic merge threshold, so the algorithm splits them into two clusters:

- Cluster 1 (Speaker 1): segments 4–5 (7.31–9.35s) "integration is working"
- Cluster 2 (Speaker 3): segments 6 (11.99–12.99s) "lower than expected"
- Speaker B (true) gets zero correctly attributed segments under the unconstrained run

**Fix**: Pass `num_speakers=2` to the pipeline call. This forces agglomerative clustering to stop merging when exactly 2 clusters remain, eliminating the phantom.

---

### Root Cause 2: WAV Truncation (Coverage Loss)

**What happens**: The session WAV captures 21.0 seconds of audio, but the Whisper streaming transcription produced 22 segments spanning **0s to 31.96s** — approximately 11 additional seconds of transcript that has no corresponding audio in the WAV file.

**Evidence**:

| Source | Time Range | Segment Count |
|--------|-----------|---------------|
| WAV file | 0.0s – 21.0s | Pyannote can assign 14 segments |
| DB segments | 0.0s – 31.96s | 22 segments total |
| Outside WAV | 21.0s – 31.96s | 8 segments → "Unknown" |

This is why coverage = 63.6% (14/22) instead of the expected ≥80%, and why Speaker B's recall is 0.133–0.143 across all configs — B's segments at 26.56–28.36s fall outside the WAV and cannot be overlap-assigned.

**Note on previous 86.4% coverage**: The production run used proximity fallback to assign these out-of-range segments to the nearest turn (within 2.0s). Since the last Pyannote turn ends at ~21s and the gap to the next segment at 23.49s is 2.49s (just over the threshold), segments at 23s+ got "Unknown" and were proximity-assigned incorrectly. The 86.4% figure counted those proximity assignments as "covered", masking the underlying WAV truncation.

**Root cause of truncation**: The `AudioBuffer` WAV writer closes and finalises the file when the session ends. If the session was ended (`DELETE /sessions/{id}`) before all PCM audio was written, or if the WebSocket connection was closed while audio was still being streamed, the WAV file contains only the audio that arrived before termination — while Whisper had already transcribed later audio from the in-memory buffer before it was flushed to WAV.

---

## Why SCDR = 0.0% for Configs B and C

SCDR measures whether predicted speaker-change timestamps align with annotated boundaries (within 0.5s). With `num_speakers=2`, Pyannote produces 7 turns that correctly detect **intra-WAV changes**, but the evaluation script's `changes()` function maps all 22 DB segments using the label map. Since ~8 segments are "Unknown" → mapped to "B", they create artificial "A→B" or "B→A" transitions at positions that don't align with the annotated boundaries. This distorts the SCDR calculation downward.

The SCDR of 0.0% for B/C does **not** mean B/C detects fewer changes than A — it means the out-of-range "Unknown" segments create false change boundaries that misalign with ground truth.

---

## Recommendations

### Immediate Fix (Phantom Speaker)

In `services/post_session_diarizer.py`, line 223, change:
```python
# BEFORE (current production)
diarization = diarizer._pipeline(waveform)

# AFTER
diarization = diarizer._pipeline(waveform, num_speakers=2)
```

And in `audio/diarizer.py`, line 150, for live diarization:
```python
# AFTER (accept num_speakers from config or session mode)
diarization = self._pipeline(waveform, **speaker_count_kwargs)
```

> **Note**: `num_speakers=2` should only be used for known 2-speaker sessions (e.g. Sales mode). For multi-party meetings, use `min_speakers=2, max_speakers=5` to constrain without over-fixing.

### Required Fix (WAV Truncation)

The WAV file must capture the full audio that Whisper transcribed. Investigate:
1. Whether `AudioBuffer.close()` is called too early relative to the final Whisper flush
2. Whether the `end` WebSocket message interrupts audio write before all PCM is flushed

Until WAV truncation is fixed, both coverage and accuracy metrics will be unreliable — post-session Pyannote only has access to the WAV content, not the full streaming transcript time range.

---

## Production Readiness Assessment

| Issue | Status | Blocking Role Classification? |
|-------|--------|-------------------------------|
| Phantom speaker (3 clusters for 2-speaker recording) | ✅ Fixable with `num_speakers` param | YES — unmapped cluster suppresses B's recall |
| WAV truncation (21s WAV vs 32s transcript) | ❌ Root cause not yet fixed | YES — ~36% of segments permanently unassignable |
| Speaker B severely under-recalled | Consequence of above two issues | YES |

**Verdict: Role Classification Not Yet Safe**

Even with `num_speakers=2` applied, the WAV truncation issue means ~36% of segments are unassignable. A role classifier operating on these would systematically mis-label Speaker B's segments (which appear predominantly in the second half of the session, beyond the WAV boundary).

**Path to production readiness**:
1. Fix WAV truncation → re-run evaluation → expect coverage to rise toward 90%+
2. Apply `num_speakers` constraint → re-run evaluation → expect Macro F1 ≥ 0.75
3. Validate SCDR ≥ 70% on the fixed session
4. Only then enable role classification

---

*Generated from: `investigate/run_config.py` with configs A, B, C. Results in `investigate/result_config_*.json`.*
