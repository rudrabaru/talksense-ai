# TalkSense AI — Project Work Done Report

This document details the features, components, architecture improvements, and evaluation frameworks implemented so far in the **TalkSense AI** platform.

---

## Table of Contents
1. [Overview](#overview)
2. [FastAPI Backend Core & Models](#fastapi-backend-core--models)
3. [Real-Time Audio Pipeline & WebSockets](#real-time-audio-pipeline--websockets)
4. [Conversation Intelligence & Context Analyzer](#conversation-intelligence--context-analyzer)
5. [Database & Persistence Layer (SQLAlchemy ORM)](#database--persistence-layer-sqlalchemy-orm)
6. [Post-Session Diarization & Refinement Pipeline](#post-session-diarization--refinement-pipeline)
7. [Advanced Sales Analytics & Objection Handling](#advanced-sales-analytics--objection-handling)
8. [React UI & Audio Capture Frontend](#react-ui--audio-capture-frontend)
9. [Evaluation & Diagnostics Frameworks](#evaluation--diagnostics-frameworks)
10. [Current Goal & Next Steps](#current-goal--next-steps)

---

## Overview

TalkSense AI is an **offline-first conversation intelligence platform** optimized for meetings and sales calls. The project is designed to capture audio streaming in real-time, perform local Speech-to-Text (STT) and Natural Language Processing (NLP) enrichment, apply rule-based context intelligence, and persist everything to a relational database for post-session analytics.

Recently, the codebase transitioned toward a robust **real-time WebSocket architecture** with advanced analytics pipelines (Speaker Attribution, Role Classification, Objection Handling, and Talk Ratio Timelines).

---

## FastAPI Backend Core & Models

The backend is built using **FastAPI** (`backend/main.py`), utilizing dynamic lifespan hooks for resource loading, warmup, and clean shutdown.

### 1. Model Initialization & Warmup
On startup, the system loads and warms up the following local AI models:
*   **VAD Model**: Silero VAD (Voice Activity Detection) loaded as a CPU-optimized singleton.
*   **Whisper Transcriber**: `faster-whisper` loaded on GPU (if CUDA is available) or CPU.
*   **Pyannote Diarizer**: Pyannote 3.1 speaker diarization pipeline (GPU/CPU) using Hugging Face authorization.
*   **Sentiment Classifier**: Multilingual sentiment analysis transformer (`tabularisai/multilingual-sentiment-analysis`) for per-segment inference.

### 2. Lifespan Coordination
*   Initializes the database connection pool.
*   Runs DB migrations (`Base.metadata.create_all`).
*   Runs startup recovery to clean up orphaned/active sessions left from prior crashes.
*   Launches a background flusher task loop to write session telemetry to the DB.
*   Graces shutdown by stopping the flusher, draining pending workers, and disposing of DB connection pools.

---

## Real-Time Audio Pipeline & WebSockets

The real-time streaming pipeline handles continuous binary audio capture and multi-channel telemetry broadcasting.

### 1. Inbound Audio WebSocket (`/ws/audio/{session_id}`)
*   Accepts continuous binary PCM audio streamed from the browser.
*   Validates session status and rejects connections to already-terminated sessions (returns code `4009`).
*   Supports text-based control commands:
    *   `end`: Triggers final buffer flushes, persists session duration, and starts post-session diarization.
    *   `ping`: Responds with `pong` to verify connection health.
    *   `inject:Speaker Name|phrase`: Allows testing by mocking transcript segment ingestion and metric updates.

### 2. Audio Accumulation & WAV Recording (`backend/audio/buffer.py`)
*   **WAV Timeline Synchronization**: Modified to write *all* incoming raw PCM frames directly to an on-disk WAV file. This keeps the physical WAV file length perfectly aligned with the live transcription timestamp timeline, fixing the **WAV Truncation Bug** where late-stage audio was cut off.
*   **Speech Buffer**: Uses VAD to buffer speech frames. It flushes either when target duration is reached or after a silence gap is detected.
*   **Time-Offset Tracking**: Returns the exact time offset where each flushed chunk starts relative to the session start, keeping STT alignment accurate.
*   **WAV Finalization**: Rewrites correct RIFF headers and data chunk sizes upon closing, making the WAV file compatible with Pyannote, ffmpeg, or other tools.

### 3. Outbound Subscription Channels (`backend/ws/subscriptions.py`)
Provides separate WebSocket routes for dashboard widgets:
*   `/ws/transcript/{session_id}`: Pushes live transcribed segments containing speaker labels, timestamps, and sentiment scores.
*   `/ws/metrics/{session_id}`: Pushes conversation metrics (health score, speaking ratios, participation, objections, buying signals).
*   `/ws/alerts/{session_id}`: Broadcasts real-time events (silences, high talking ratios, negative sentiment dips).
*   `/ws/status/{session_id}`: Broadcasts session state transitions.

---

## Conversation Intelligence & Context Analyzer

A rule-based evaluation layer parses incoming segments and computes metrics according to the conversation mode.

### 1. Conversation Engine (`backend/engine/conversation_engine.py`)
*   Accumulates segments and computes speaking metrics in real-time.
*   **Filler Word Detection**: Matches custom list of filler words ("like", "basically", "um", "uh", "you know").
*   **Objection Classification**: Categorizes objections dynamically. Supports nested keyword definitions in `keywords.json` to assign category tags (e.g., Price, Authority, Timing, Need).
*   **Alert Generation**: Raises alerts based on threshold configurations (e.g. silence exceeding 10 seconds, participant dominance > 70%).

### 2. Context Analyzer (`backend/services/context_analyzer.py`)
Contains structured analysis rules:
*   **Meeting Mode**:
    *   Meeting Quality Score (High/Medium/Low) based on decisions and action items.
    *   Action Item Detection: Extracts ownership signals, timeline statements, and task phrases.
    *   Tension points and blockers detection.
*   **Sales Mode**:
    *   Sales Quality Score based on buyer sentiment, buying signals, and objection status.
    *   Deal Risk Flags (e.g., lack of intent, authority gap).
    *   Hard Commitment tracking (timeline and next steps).

---

## Database & Persistence Layer (SQLAlchemy ORM)

The relational schema in `backend/db/models.py` uses SQLAlchemy 2.0 async declarative modeling with timezone-aware datetimes and JSONB columns.

### Relational Schema (8 Tables)
1.  **`users`**: Registered accounts (auth deferred to Phase 5).
2.  **`clients`**: Client profiles containing company and industry info.
3.  **`sessions`**: Active and completed meeting logs, binding the conversation mode and audio file paths.
4.  **`transcript_segments`**: Individual Whisper-transcribed segments (linked to `sessions` with CASCADE delete).
5.  **`session_metrics`**: History of metrics flushed periodically for timeline charts.
6.  **`analysis_results`**: One-to-one final report containing executive summaries, action items, and decision logs.
7.  **`alerts`**: Log of triggered system alerts.
8.  **`client_snapshots`**: Rollup metrics aggregated after sessions (total meetings, objection history, sentiment trends).

### Operations Layer (`backend/db/crud.py`)
*   **Transactional Boundaries**: Clean separation of write responsibilities. Route handlers commit transaction-scoped REST writes, while the background flusher aggregates and commits streaming telemetry.
*   **Optimized Upserts**: Uses PostgreSQL-native `ON CONFLICT DO UPDATE` (upserts) for final reports to prevent TOCTOU race conditions.
*   **Recovery Task**: Bulk-transitions orphaned sessions (`created`, `connecting`, `active`, `processing`) to `interrupted` status on startup.

---

## Post-Session Diarization & Refinement Pipeline

When a session ends, the system triggers an offline refinement worker (`backend/services/post_session_diarizer.py`) to align, attribute, and label speakers.

```
Session Ends → Finalize WAV → Pyannote (Single Pass) → Two-Stage Alignment → Speaker Roles & Talk Ratio
```

### 1. Two-Stage Alignment Algorithm
A custom assignment matching engine maps Pyannote turns back to database transcript segments:
*   **Stage 1 (Temporal Overlap)**: Calculates segment overlaps. The speaker turn with the highest overlap ratio wins.
*   **Stage 2 (Nearest-Turn Proximity)**: If a segment falls in a silence gap between Pyannote turns, it is mapped to the nearest turn boundary. This solves timestamp drift and keeps coverage high.

### 2. Speaker Counting & Constrained Clustering
*   **Phantom Speaker Bug Fix**: Constrains Pyannote's agglomerative clustering by passing `num_speakers=2` (or utilizing user boundaries) to prevent short, sparse segments from splitting into phantom 3rd or 4th speakers.

### 3. Role Classification (`backend/services/role_classifier.py`)
*   **V1 Heuristic Classifier**: Classifies speakers as `sales_rep` or `customer` using keyword indicator scores.
*   **V2 LLM Classifier**: Sends transcript samples to `gemini-2.0-flash` to evaluate speaking patterns, intent, and company representation. Returns roles, reasoning, and a confidence score.
*   **Fallback Logic**: downstream widgets default to V2 LLM results, falling back to V1 heuristics if the API key is missing or model queries fail.

### 4. Talk Ratio Timeline (`backend/services/talk_ratio_analyzer.py`)
*   Extracts duration statistics, monologue counts, silence gaps, and speaker switch rates.
*   Groups talking ratios into **30-second windows** to render a conversation balance grid on the frontend.
*   Computes monologue risk (High/Medium/Low) and dominance levels.

---

## Advanced Sales Analytics & Objection Handling

The platform aggregates advanced intelligence post-session to judge deal execution quality.

### Objection Handling Quality (`backend/services/objection_handler.py`)
*   Scours database transcripts to locate segments containing customer objections.
*   Locks onto the subsequent segment spoken by the identified `sales_rep`.
*   Calculates response delays and assigns a **4-tier handling score**:
    *   `ignored` (Score: `0.0`): Rep took >30 seconds to reply, or failed to reply.
    *   `acknowledged` (Score: `0.5`): Rep replied within 30s but didn't discuss details.
    *   `addressed` (Score: `0.8`): Rep replied within 30s and discussed the topic keywords (e.g. price, cost, timeline).
    *   `resolved` (Score: `1.0`): Customer expressed a positive buying signal within 60 seconds of the Rep's response.
*   Persists scores to the DB and surfaces them in the dashboard.

---

## React UI & Audio Capture Frontend

The React frontend has been upgraded with live dashboards and robust media capture hooks.

### 1. High-Performance Audio Capture Hook (`talksense-ui/src/hooks/useAudioCapture.js`)
*   Requests microphone access with constraints optimized for Whisper (16kHz mono).
*   Loads an **AudioWorklet processor** (`PCMProcessor`) inside a dedicated audio thread to downmix channels, resample audio via stateful linear interpolation, and scale float values to 16-bit signed PCM.
*   **Phase Continuity Fix**: Carries fractional phase parameters across block boundaries to eliminate the high-frequency buzzing injected by previous block-resampling methods.
*   **GC Memory Reuse**: Recycles array buffers returned by the main thread, lowering heap allocations and garbage collection pressure.

### 2. Multi-Channel WebSocket Hook (`talksense-ui/src/hooks/useSessionWebSocket.js`)
*   Connects to `/transcript`, `/metrics`, `/alerts`, and `/status` concurrently.
*   Uses **exponential backoff with jitter** for automatic channel reconnections.
*   **State Reconciliation**: On successful connection/reconnection, fetches a REST snapshot from `/dashboard/{session_id}` to reconcile missed messages.
*   **Envelope Unwrapping**: Parses envelope metadata (`type`, `payload`, `ts`) and routes data to the correct state hook.
*   **Deduplication**: Checks composite segment keys (speaker + start + end + text) to prevent duplicate transcript displays.

### 3. Dashboard Interface (`talksense-ui/src/pages/DashboardPage.jsx`)
*   Validates session existence on mount, auto-creating a new session if the URL session is stale.
*   Coordinates microphone control states (`idle`, `connecting`, `streaming`, `error`) and websocket connectivity banners.
*   Integrates dashboard panels:
    *   `TranscriptPanel`: Lists live scrolling transcript segments labeled with speakers and sentiments.
    *   `AlertsPanel`: Renders warnings and status flags.
    *   `MetricsPanel`: Visualizes conversation metrics (Health, speaking ratio, fillers) and adds advanced panels:
        *   **Objection Scorecard**: Renders categories, customer text, rep responses, delays, and resolution scores.
        *   **Talk Timeline**: A grid detailing participant speech percentages in 30-second windows.
        *   **Role Assignments**: Shows speaker-to-role mappings.
        *   **Benchmark Analytics Health**: Displays static subsystem validation states (PASS/FAIL).

---

## Evaluation & Diagnostics Frameworks

To guide development and check accuracy before pushing code to production, a batch evaluation pipeline was created:

### 1. Accuracy Evaluator (`backend/evaluate_speaker_accuracy.py`)
*   Aligns predicted database segments to course ground-truth segment annotations using maximum-overlap matching.
*   Resolves labels using a greedy majority-vote permutation matrix to map Pyannote names (e.g. Speaker 1) to canonical entities.
*   Generates detailed Markdown accuracy reports showing coverage, accuracy ratios, SCDR, per-speaker F1 metrics, and a failure log of misattributions.

### 2. CLI Batch Evaluator (`backend/evaluate_speaker_attribution.py`)
*   Command-line utility to run batch evaluations across multiple session IDs.
*   Compares results against expected speakers and turns, generating summary reports with role classification safety verdicts.

---

## Current Goal & Next Steps

1.  **Analytics Safety & Refinement**: The Analytics Accuracy Audit acts as a gatekeeper for semantic features. Current benchmarks indicate:
    *   *Speaker Attribution* is stable (~78% accuracy, 84% coverage).
    *   *Role Classification* (~25%) and *Objection Handling* (~10%) require further tuning before being marked safe.
2.  **LLM Intent Recognition Integration**: Plans are underway to rewrite the NLP extraction engine to transition from static keyword substring matching to semantic LLM classification for objections, buying signals, and role mapping.
3.  **Sales Rep Leaderboards**: Future UI pages will allow users to compare aggregated performance metrics and objection handling rates across multiple client histories.
