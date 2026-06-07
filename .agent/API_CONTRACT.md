# TalkSense AI — API Contract & Schema Specifications

This document defines the interface boundary between the backend (FastAPI) and frontend (React) services for TalkSense AI. It serves as the single source of truth for both REST APIs and real-time WebSocket channels.

---

## 🎛️ Protocols and Formats

### REST Base Configuration
- **Request Format**: JSON (for resource creation) or Multipart/Form-Data (for audio upload in legacy mode).
- **Response Format**: JSON (UTF-8).
- **Base URL**: `http://localhost:8000` (Local Development).

### Audio Ingestion Stream Requirements
Audio sent to the ingestion channel must comply with the following specification:
- **Encoding**: Linear PCM (Raw)
- **Sample Rate**: 16 kHz (16000 samples/sec)
- **Channels**: 1 (Mono)
- **Bit Depth**: 16-bit (Signed Integer)
- **Endianness**: Little-Endian (Browser default)
- **Chunk Duration**: 100–250ms per binary frame (buffer flushes when ~1000ms speech is accumulated).

---

## 🔑 Authentication
- **Token Type**: Bearer JWT.
- **Authorization Header**: `Authorization: Bearer <JWT_TOKEN>`
- **Active Phase Constraint**: Session lifecycle endpoints (`/sessions/*` and `/ws/*`) do not require authentication headers in Phase 1-4. They are keyed by a unique, secure UUIDv4 `session_id`. Auth requirements apply to `/clients` and `/auth` endpoints.

---

## 🌐 HTTP REST Endpoints

### 1. Health Check
Checks backend service availability.
- **Route**: `/health`
- **Method**: `GET`
- **Auth Required**: No
- **Headers**: None
- **Response (200 OK)**:
```json
{
  "status": "ok",
  "service": "TalkSense AI",
  "version": "4.0.0"
}
```

---

### 2. Create Session
Creates a new active session context.
- **Route**: `/sessions`
- **Method**: `POST`
- **Auth Required**: No
- **Query Parameters**:
  - `mode` (string): Options are `meeting` (default), `sales`, or `interview`.
  - `client_id` (string, optional): Target client UUIDv4 for memory snapshots.
- **Response (200 OK)**:
```json
{
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "mode": "sales",
  "status": "created",
  "ws": {
    "audio": "/ws/audio/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "transcript": "/ws/transcript/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "metrics": "/ws/metrics/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "alerts": "/ws/alerts/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
    "status": "/ws/status/9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d"
  }
}
```
- **Errors**:
  - `400 Bad Request` (Invalid mode provided)

---

### 3. Get Active Session State
Retrieve current status of a running session.
- **Route**: `/sessions/{session_id}`
- **Method**: `GET`
- **Auth Required**: No
- **Response (200 OK)**:
```json
{
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "mode": "sales",
  "status": "active",
  "elapsed_seconds": 124.5,
  "health_score": 88,
  "sentiment": "positive"
}
```
- **Errors**:
  - `404 Not Found`:
    ```json
    { "error": "Session not found" }
    ```

---

### 4. End Session
Terminates a running session, prompting final report calculations and snapshots.
- **Route**: `/sessions/{session_id}`
- **Method**: `DELETE`
- **Auth Required**: No
- **Response (200 OK)**:
```json
{
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "status": "completed"
}
```
- **Errors**:
  - `404 Not Found` (Session not found)

---

### 5. Get Dashboard Snapshot (Reconnect)
Retrieves the complete state needed to restore the React UI upon reconnection.
- **Route**: `/dashboard/{session_id}`
- **Method**: `GET`
- **Auth Required**: No
- **Response (200 OK)**:
```json
{
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "mode": "sales",
  "status": "active",
  "elapsed_seconds": 124.5,
  "health_score": 88,
  "sentiment": "positive",
  "sentiment_score": 0.75,
  "speaking_ratio": "60/40",
  "participation": {
    "Speaker A": 60,
    "Speaker B": 40
  },
  "filler_count": 3,
  "objections": ["pricing"],
  "buying_signals": ["demo request"],
  "active_alerts": [
    {
      "level": "warning",
      "message": "Long silence detected (>15s)",
      "timestamp": 1717754388.0
    }
  ],
  "transcript_segments": [
    {
      "speaker": "Speaker A",
      "text": "Hello, thank you for meeting today.",
      "start": 0.0,
      "end": 2.5,
      "sentiment": 0.8,
      "sentiment_label": "Positive"
    }
  ]
}
```
- **Errors**:
  - `404 Not Found`

---

### 6. Legacy Batch Analysis
Batch analysis endpoint.
- **Route**: `/analyze`
- **Method**: `POST`
- **Auth Required**: No
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `file`: (Binary audio file file)
  - `mode`: `meeting` (default) or `sales`
- **Response (200 OK)**:
```json
{
  "filename": "SalesMeeting.mp3",
  "mode": "sales",
  "transcript": {
    "text": "Full transcript content goes here...",
    "segments": [
      {
        "text": "Hello, this is the transcript line.",
        "start": 0.0,
        "end": 3.4,
        "sentiment": 0.6,
        "sentiment_label": "Positive",
        "keywords": ["transcript"]
      }
    ]
  },
  "insights": {
    "sentiment": "positive",
    "objections": ["pricing"],
    "buying_signals": [],
    "sales_quality": 84
  }
}
```

---

### 7. Client Management endpoints

#### Create Client
- **Route**: `/clients`
- **Method**: `POST`
- **Auth Required**: Yes
- **Request Body (JSON)**:
```json
{
  "name": "Acme Corporation",
  "industry": "Software"
}
```
- **Response (201 Created)**:
```json
{
  "id": "c1a603a1-7788-4444-8888-c70a9ab0cd1a",
  "name": "Acme Corporation",
  "industry": "Software",
  "created_at": "2026-06-07T18:39:00Z"
}
```

#### List Clients
- **Route**: `/clients`
- **Method**: `GET`
- **Auth Required**: Yes
- **Response (200 OK)**:
```json
[
  {
    "id": "c1a603a1-7788-4444-8888-c70a9ab0cd1a",
    "name": "Acme Corporation",
    "industry": "Software",
    "created_at": "2026-06-07T18:39:00Z"
  }
]
```

#### Get Client Briefing Card
- **Route**: `/clients/{client_id}`
- **Method**: `GET`
- **Auth Required**: Yes
- **Response (200 OK)**:
```json
{
  "client_id": "c1a603a1-7788-4444-8888-c70a9ab0cd1a",
  "name": "Acme Corporation",
  "meetings_count": 6,
  "sentiment_trend": "improving",
  "common_objections": ["pricing", "integration"],
  "last_meeting_date": "2026-05-24T10:15:00Z"
}
```

---

### 8. Get Post-Session Report
- **Route**: `/reports/{session_id}`
- **Method**: `GET`
- **Auth Required**: No
- **Response (200 OK)**:
```json
{
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "health_score": 88,
  "summary": "Meeting summary goes here...",
  "report_json": {
    "decisions": ["Integrate database by Phase 3"],
    "action_items": ["Verify PCM streaming rate"],
    "sentiment_timeline": [0.2, 0.4, 0.8]
  },
  "transcript": [
    {
      "speaker": "Speaker A",
      "text": "Hello, thank you for meeting today.",
      "start": 0.0,
      "end": 2.5,
      "sentiment": 0.8
    }
  ]
}
```

---

## 🔌 WebSockets Channels

### 1. Inbound Audio Ingestion
- **Route**: `/ws/audio/{session_id}`
- **Protocol**: Binary & Text Messages.
- **Client Operations**:
  - Sends raw PCM bytes (mono, 16kHz, 16-bit).
  - Sends Text: `"end"` to terminate session.
  - Sends Text: `"ping"` to check availability (Server responds with `"pong"`).
- **Server Actions**: Closes connection with Code `4004` if session does not exist.

---

### 2. Outbound Transcript Feed
- **Route**: `/ws/transcript/{session_id}`
- **Protocol**: Text (Push events from server).
- **Push Event Format**:
```json
{
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "speaker": "Speaker A",
  "text": "So let's finalize the timeline for next week.",
  "start": 12.4,
  "end": 15.6,
  "sentiment": 0.4,
  "sentiment_label": "Positive"
}
```

---

### 3. Outbound Metrics Feed
- **Route**: `/ws/metrics/{session_id}`
- **Protocol**: Text (Push events from server).
- **Backpressure Handling**: Server will drop old metric payloads when client queue is full; only the latest state is preserved.
- **Push Event Format**:
```json
{
  "health_score": 88,
  "sentiment": "positive",
  "speaking_ratio": "60/40",
  "participation": {
    "Speaker A": 60,
    "Speaker B": 40
  },
  "filler_count": 3,
  "duration_seconds": 124.5
}
```

---

### 4. Outbound Alerts Feed
- **Route**: `/ws/alerts/{session_id}`
- **Protocol**: Text (Push events from server).
- **Backpressure Handling**: **Never dropped**. All alerts must be delivered.
- **Push Event Format**:
```json
{
  "level": "critical",
  "message": "Client sentiment crash detected",
  "timestamp": 1717754388.0
}
```

---

### 5. Outbound Lifecycle Status Feed
- **Route**: `/ws/status/{session_id}`
- **Protocol**: Text (Push events from server).
- **Values**: `active`, `processing`, `completed`, `failed`, `interrupted`, `expired`.
- **Push Event Format**:
```json
{
  "status": "active",
  "elapsed_seconds": 124.5
}
```
