# TalkSense AI — Quality Assurance & Testing Checklist

This checklist defines testing requirements, verification criteria, and quality gates across the five core system domains of the TalkSense AI platform.

---

## 🎙️ 1. Audio Ingestion & ML Pipeline

### Unit Tests
- [ ] **VAD Chunk Detection**: Validate that `vad.is_speech()` returns `True` for active speech samples and `False` for silent bytes.
- [ ] **Accumulation Buffer Math**: Verify `AudioBuffer` accumulates PCM bytes accurately and triggers a flush condition when buffered speech reaches exactly 1000ms.
- [ ] **Buffer Boundary Flush**: Confirm that partial sentence flushes clean the buffer and do not drop trailing speech chunks.

### Integration Tests
- [ ] **Whisper GPU Execution**: Verify `Transcriber` loads the `small` or `medium` model on CUDA with `int8` compute types and returns timestamped transcription segments under the 700ms budget limit.
- [ ] **Pyannote Diarization**: Test speaker turn labeling overlaps under parallel loads. Verify sequential CUDA fallback if HuggingFace tokens are not set.

### Manual QA Checks
- [ ] **Silence Suppression**: Run a local microphone stream. Speak, pause for 10 seconds, and speak again. Confirm the terminal log shows no empty transcription invocations during the pause.
- [ ] **Diarization Heuristic Degradation**: Disable Pyannote (`PYANNOTE_ENABLED=false`) in `.env`. Stream audio from two speakers and verify that speaker labels alternate cleanly by turn boundary heuristic.

---

## ⚙️ 2. Backend API & Analytics Engines

### Unit Tests
- [ ] **Scoring Formula Limits**: Test `compute_health_score()` using boundary metrics (0 and 100 values) for all modes (Meeting, Sales, Interview) to verify results stay within the `[0, 100]` range.
- [ ] **Alert Engine Cooldown**: Validate that consecutive identical alerts trigger a suppression timer and do not dispatch within 30 seconds of the first.
- [ ] **Alert Overflow Control**: Ensure that if more than 3 alerts are generated, the oldest alert is automatically discarded, keeping the list length capped at 3.
- [ ] **Locked Quality Algorithm**: Verify `compute_meeting_quality_v2()` matches the deterministic quality matrix (ownership and execution logic matches).

### Integration Tests
- [ ] **Session Lifecycle APIs**: Execute `POST /sessions` to create a session context, verify status transitions to `created`, and ensure `DELETE /sessions/{id}` completes the session.
- [ ] **Legacy Analysis End-to-End**: Upload a sample wav file to `POST /analyze`. Verify response contains transcripts, sentiment labels, and meeting quality insights.

### Manual QA Checks
- [ ] **Scoring Response**: Run a sales session and speak key buying words (e.g. "pricing", "demo"). Verify that `/ws/metrics` updates the sales signals score.

---

## 🔌 3. WebSockets (Real-Time Communication)

### Unit Tests
- [ ] **Registry Add/Remove**: Verify `SessionManager` correctly registers WebSocket client subscriptions (`/ws/transcript`, `/ws/metrics`, `/ws/alerts`, `/ws/status`) and removes them upon disconnect.

### Integration Tests
- [ ] **Metrics Backpressure Handling**: Simulate a slow frontend client. Send 10 metric updates in rapid succession. Verify that intermediate metric frames are dropped and only the latest state is delivered.
- [ ] **Alert Delivery Guarantee**: Simulate a slow frontend client. Send 5 alerts. Verify that **none** of the alerts are dropped, and all are delivered to the alerts channel.

### Manual QA Checks
- [ ] **Subscription Heartbeat**: Open WebSocket channels in browser dev tools. Verify that connection is maintained indefinitely and responds to `"ping"` with `"pong"`.

---

## 🗄️ 4. Database & Session Persistence

### Unit Tests
- [ ] **Model CRUD Helper Logic**: Verify database CRUD functions successfully execute session inserts, clients lookup queries, and transcript segment saves.

### Integration Tests
- [ ] **5-Second Flush Persistence**: Start an active session and stream audio. Verify that transcripts and metrics are saved to the PostgreSQL database in the background every 5 seconds.
- [ ] **Snapshot Update Integration**: End a session and verify that client summaries (`client_snapshots`) are generated and the associated client records update in the DB.

### Manual QA Checks
- [ ] **Session Crash Recovery**: Kill the FastAPI server midway through an active audio stream. Restart the server, open the reconnect dashboard, and verify that all prior transcript segments and metrics are restored.

---

## 💻 5. Frontend (React UI Dashboard)

### Unit Tests
- [ ] **Routing Configurations**: Verify React router maps new routes (`/start`, `/dashboard/:id`, `/report/:id`) correctly.

### Integration Tests
- [ ] **useAudioCapture Hook**: Grant mic permissions. Verify the hook converts browser recording data into 16kHz PCM bytes.
- [ ] **useSessionWebSocket Hook**: Verify connection to all 4 WS channels. Test that if connection drops, the hook attempts to reconnect with exponential backoff.

### Manual QA Checks
- [ ] **Responsive 3-Panel Layout**: Resize the browser to 1280px width. Confirm the Left Transcript panel, Center Intelligence panel, and Right Alert feed remain fully visible.
- [ ] **Alert Entry Animations**: Trigger a Critical alert. Verify it slides in from the right with a red border toast animation.
- [ ] **Auto-Scroll Behavior**: Fill the Left Transcript panel with text. Verify it automatically scrolls smoothly to the latest speaker segment.
