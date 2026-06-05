# TalkSense AI v4

## Final Architecture & Implementation Blueprint

**Version:** 4.0
**Status:** Architecture Frozen
**Product Category:** AI-Powered Conversation Intelligence Platform

---

# 1. Vision

TalkSense AI is an AI-powered Conversation Intelligence Platform that analyzes conversations in real time and provides actionable insights before the conversation ends.

The platform is NOT:

* A transcription tool
* A meeting recorder
* A report generator

Those are supporting capabilities.

The primary value is:

> Understand conversations while they are happening and provide meaningful intelligence, alerts, and historical context.

---

# 2. Core Objectives

The system should:

1. Capture audio in real time
2. Transcribe conversations
3. Identify speakers
4. Analyze sentiment
5. Detect conversation patterns
6. Generate real-time alerts
7. Store session history
8. Build client memory
9. Generate post-session reports
10. Support Meeting, Sales, and Interview modes

---

# 3. Product Philosophy

## Real-Time First

Priority:

```text
Live Intelligence
    ↓
Reports
```

NOT

```text
Reports
    ↓
Live Intelligence
```

The report is a byproduct.

The dashboard is the product.

---

# 4. Supported Modes

Users explicitly select a mode before starting.

No auto mode detection exists in V1.

## Meeting Mode

Focus:

* Participation
* Engagement
* Speaking balance
* Action items
* Meeting health

---

## Sales Mode

Focus:

* Objection detection
* Buying signals
* Talk-to-listen ratio
* Sentiment trends
* Deal health

---

## Interview Mode

Focus:

* Confidence score
* Filler words
* Response quality
* Pause detection
* Speaking balance

---

# 5. Core Architecture

```text
Microphone
     ↓
Voice Activity Detection
     ↓
Audio Buffer
     ↓
Faster Whisper
     ↓
Pyannote
     ↓
Segment Assembler
     ↓
Conversation Engine
     ↓
Alert Engine
     ↓
WebSocket Layer
     ↓
Dashboard
     ↓
Persistence Layer
     ↓
Reports + Client Memory
```

---

# 6. Technology Stack

## Frontend

React

Responsibilities:

* Dashboard
* Reports
* History
* Client management
* Session controls

---

## Backend

FastAPI

Responsibilities:

* APIs
* WebSockets
* Session lifecycle
* Authentication
* Analytics

---

## Database

PostgreSQL

Responsibilities:

* Sessions
* Clients
* Reports
* Metrics
* Memory

---

## AI Stack

### Transcription

Faster Whisper

Configuration:

```text
Model: medium
Device: GPU
Precision: float16
```

---

### Speaker Diarization

Pyannote

Configuration:

```text
Device: GPU

Window: 4 sec

Stride: 1 sec
```

---

### Sentiment

Lightweight transformer

or

Rule-based sentiment engine

Requirements:

* Fast
* Explainable
* Deterministic

---

# 7. Audio Contract

Required format:

```text
PCM
16kHz
Mono
16-bit
```

Chunk Size:

```text
100–250ms
```

Reject unsupported formats immediately.

---

# 8. Voice Activity Detection

Mandatory.

Recommended:

Silero VAD

Benefits:

* Lower GPU load
* Ignore silence
* Faster processing

---

# 9. Latency Budget

Target:

```text
2–3 seconds
```

Breakdown:

```text
Buffer          1000ms
Whisper          700ms
Pyannote         700ms
Assembly          50ms
Analytics        100ms
Network           50ms
```

Expected:

```text
~2.5 sec
```

---

# 10. Conversation Engine

The Conversation Engine is the heart of the product.

Every mode uses the same engine.

---

## Responsibilities

* Sentiment
* Speaking ratio
* Participation
* Pauses
* Filler words
* Objections
* Buying signals
* Conversation health

---

## Output

Produces:

```json
{
  "sentiment": "positive",
  "speaking_ratio": "60/40",
  "health_score": 84,
  "alerts": []
}
```

---

# 11. Scoring Profiles

Profiles customize scoring.

The engine remains unchanged.

---

## Meeting Profile

Weights:

```text
Participation     40%
Engagement        30%
Balance           20%
Action Items      10%
```

---

## Sales Profile

Weights:

```text
Objections        35%
Sentiment         25%
Listening Ratio   20%
Signals           20%
```

---

## Interview Profile

Weights:

```text
Confidence        35%
Fillers           25%
Response Quality  25%
Pauses            15%
```

---

# 12. Alert Engine

Purpose:

Generate meaningful real-time alerts.

---

## Alert Levels

### Critical

Red

Examples:

* Client sentiment crash
* Severe speaking imbalance
* Repeated objections

---

### Warning

Yellow

Examples:

* Long silence
* Excessive fillers
* Reduced engagement

---

### Info

Blue

Examples:

* Buying signal
* Positive sentiment shift

---

# 13. Alert Cooldown System

Prevent alert spam.

Rules:

```text
Same alert:
Minimum 30 sec cooldown
```

---

Maximum active alerts:

```text
3
```

---

Duplicate alerts:

```text
Suppressed
```

---

# 14. Real-Time Dashboard

## Top Bar

Displays:

```text
Mode
Client
Session Timer
Health Score
```

---

## Left Panel

Live Transcript

```text
Speaker A
Speaker B
Speaker A
```

---

## Center Panel

Conversation Intelligence

Displays:

* Sentiment
* Health score
* Participation
* Speaking ratio

---

## Right Panel

Alert Feed

Displays:

```text
Critical
Warning
Info
```

sorted by severity.

---

# 15. Conversation Health Score

Unified score.

Range:

```text
0–100
```

Factors:

* Sentiment
* Participation
* Balance
* Confidence
* Engagement

---

# 16. Client Memory

Core differentiator.

---

## Stores

* Past meetings
* Objections
* Topics
* Trends
* Sentiment

---

## Client Briefing Card

Before session:

```text
Client:
ABC Corp

Meetings:
6

Sentiment:
Improving

Common Objections:
Pricing
Integration
```

---

# 17. Database Schema

## users

```sql
id
email
password_hash
created_at
```

---

## clients

```sql
id
user_id
name
industry
created_at
```

---

## sessions

```sql
id
client_id
mode
title
started_at
ended_at
duration
status
```

---

## transcript_segments

```sql
id
session_id
speaker_id
start_time
end_time
text
sentiment
```

---

## session_metrics

```sql
id
session_id
metric_name
metric_value
```

---

## analysis_results

```sql
id
session_id
health_score
summary
report_json
```

---

## alerts

```sql
id
session_id
type
severity
message
timestamp
```

---

## client_snapshots

```sql
id
client_id
snapshot_date
summary
sentiment_score
```

---

# 18. Required Indexes

```sql
sessions(client_id)

transcript_segments(session_id)

alerts(session_id)

client_snapshots(client_id)
```

---

# 19. WebSocket Architecture

Channels:

```text
/transcript

/metrics

/alerts

/status
```

---

# 20. Backpressure Handling

Mandatory.

If frontend lags:

```text
Drop old metric updates
Keep latest state
```

Never queue indefinitely.

---

# 21. Session Lifecycle

```text
Created
 ↓
Connecting
 ↓
Active
 ↓
Processing
 ↓
Completed
```

---

Failure states:

```text
Failed
Interrupted
Expired
```

---

# 22. Failure Recovery

Handle:

* GPU crashes
* Browser disconnects
* WebSocket drops
* Audio interruptions

---

Recovery Strategy:

```text
Persist every 5 seconds
```

---

# 23. GPU Safety

Monitor:

```text
VRAM
GPU utilization
Temperature
```

---

If OOM:

```text
Switch to smaller model
```

or

```text
Pause diarization
```

---

# 24. Security

Authentication:

JWT

Password:

bcrypt

---

Security Requirements:

* HTTPS only
* Rate limiting
* Input validation
* SQL injection protection

---

# 25. Logging

Store:

* Session events
* Errors
* Alerts
* Model latency

---

Retention:

```text
30 days
```

---

# 26. Monitoring

Track:

* Average latency
* GPU usage
* WebSocket disconnect rate
* Failed sessions
* Alert frequency

---

# 27. Testing Strategy

## Unit Tests

Coverage:

* Alert logic
* Metrics
* Scoring

---

## Integration Tests

Coverage:

* Whisper
* Pyannote
* DB

---

## End-to-End Tests

Coverage:

```text
Audio
 ↓
Transcript
 ↓
Dashboard
 ↓
Report
```

---

# 28. API Endpoints

## Session

```http
POST /sessions
GET /sessions/{id}
DELETE /sessions/{id}
```

---

## Clients

```http
POST /clients
GET /clients
GET /clients/{id}
```

---

## Reports

```http
GET /reports/{session_id}
```

---

## Dashboard

```http
GET /dashboard/{session_id}
```

---

# 29. Development Roadmap

## Week 1

Build:

* FastAPI
* React
* WebSocket
* Faster Whisper
* Session lifecycle

Goal:

Live transcript.

---

## Week 2

Build:

* Pyannote
* Speaker tracking
* Sentiment
* Metrics

Goal:

Live conversation analysis.

---

## Week 3

Build:

* Alert engine
* Dashboard
* Profiles
* Reports

Goal:

Conversation intelligence.

---

## Week 4

Build:

* Client memory
* History
* Testing
* Optimization

Goal:

Production-ready MVP.

---

# 30. Features Deferred

Phase 2:

* Auto mode detection
* Deal prediction
* LLM coaching
* Topic clustering
* Multi-user teams
* Slack integration
* Zoom integration

---

# 31. Production Readiness Checklist

Before launch:

✅ Transcription stable

✅ Diarization stable

✅ Dashboard stable

✅ Alert cooldowns

✅ Recovery handling

✅ Client memory working

✅ Tests passing

✅ Monitoring enabled

---

# 32. Final CTO Verdict

TalkSense AI should be positioned as:

> AI-Powered Conversation Intelligence Platform

not:

> Meeting Analyzer

not:

> Interview Analyzer

not:

> Transcription Tool

The competitive advantage is:

1. Real-time intelligence
2. Client memory
3. Shared conversation engine
4. Explainable analytics
5. Unified Meeting, Sales, and Interview workflows

Architecture Status:

**Approved for Implementation**

No further redesign is recommended.

Begin development.
