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

- **REST Endpoints**: NOT AUTHENTICATED. No auth dependency, no token check, no middleware on any REST route.
- **WebSocket Subscriptions** (transcript, metrics, alerts, status): JWT token verification via `?token=` query parameter. Server calls `verify_ws_token(token, session_id)` and closes with code 1008 if invalid.
- **WebSocket Audio** (`/ws/audio/{id}`): NOT AUTHENTICATED. Frontend sends the token but backend does not verify it.
- **Token Lifecycle**: Created on `POST /sessions` → stored in localStorage → sent as query param on WS connect.

---

## 🌐 HTTP REST Endpoints

### 1. Health Check
Checks backend service availability.
- **Route**: `/health`
- **Method**: `GET`
- **Auth Required**: No
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
- **Request Body (JSON)**:
```json
{
  "mode": "meeting",
  "client_id": null
}
```
- **Supported modes**: `meeting`, `sales`, `interview`
- **Response (200 OK)**:
```json
{
  "session_id": "9b1deb4d-3b7d-4bad-9bdd-2b0d7b3dcb6d",
  "mode": "sales",
  "status": "created",
  "ws_token": "eyJhbGciOiJIUzI1NiIs...",
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

> **Important:** The `ws_token` field is critical. The frontend must store it and include it as `?token=` when connecting to WebSocket subscription channels.

---

### 3. List Sessions
Retrieve all sessions.
- **Route**: `/sessions`
- **Method**: `GET`
- **Auth Required**: No
- **Response (200 OK)**: Array of session summary objects.

---

### 4. Get Session State
Retrieve current status of a session.
- **Route**: `/sessions/{session_id}`
- **Method**: `GET`
- **Auth Required**: No
- **Errors**:
  - `404 Not Found`

---

### 5. End Session
Terminates a running session, triggering post-session pipeline if enabled.
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

### 6. Compare Sessions
Compare two sessions side-by-side.
- **Route**: `/sessions/compare`
- **Method**: `GET`
- **Auth Required**: No

---

### 7. Get Session Audio
Retrieve audio recording for a session.
- **Route**: `/sessions/{session_id}/audio`
- **Method**: `GET`
- **Auth Required**: No

---

### 8. Get Dashboard Snapshot (Reconnect)
Retrieves the complete state needed to restore the React UI upon reconnection.
- **Route**: `/dashboard/{session_id}`
- **Method**: `GET`
- **Auth Required**: No
- **Errors**:
  - `404 Not Found`

---

### 9. Client Management

#### Create Client
- **Route**: `/clients`
- **Method**: `POST`
- **Auth Required**: No

#### List Clients
- **Route**: `/clients`
- **Method**: `GET`
- **Auth Required**: No

#### Get Client
- **Route**: `/clients/{client_id}`
- **Method**: `GET`
- **Auth Required**: No

---

### 10. Legacy Batch Analysis
Batch analysis endpoint for audio file uploads.
- **Route**: `/analyze`
- **Method**: `POST`
- **Auth Required**: No
- **Content-Type**: `multipart/form-data`
- **Form Fields**:
  - `file`: (Binary audio file)
  - `mode`: `meeting` (default) or `sales`

---

## 🔌 WebSocket Channels

### 1. Inbound Audio Ingestion
- **Route**: `/ws/audio/{session_id}`
- **Auth**: NOT ENFORCED (token sent but ignored)
- **Protocol**: Binary & Text Messages.
- **Client Operations**:
  - Sends raw PCM bytes (mono, 16kHz, 16-bit).
  - Sends Text: `"end"` to terminate session.
  - Sends Text: `"ping"` to check availability (Server responds with `"pong"`).
- **Server Actions**: Closes connection with Code `4004` if session does not exist.

---

### 2. Outbound Transcript Feed
- **Route**: `/ws/transcript/{session_id}?token=<JWT>`
- **Auth**: JWT ENFORCED via `verify_ws_token()`
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
- **Route**: `/ws/metrics/{session_id}?token=<JWT>`
- **Auth**: JWT ENFORCED via `verify_ws_token()`
- **Protocol**: Text (Push events from server).
- **Backpressure Handling**: Server will drop old metric payloads when client queue is full; only the latest state is preserved.

---

### 4. Outbound Alerts Feed
- **Route**: `/ws/alerts/{session_id}?token=<JWT>`
- **Auth**: JWT ENFORCED via `verify_ws_token()`
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
- **Route**: `/ws/status/{session_id}?token=<JWT>`
- **Auth**: JWT ENFORCED via `verify_ws_token()`
- **Protocol**: Text (Push events from server).
- **Values**: `created`, `connecting`, `active`, `processing`, `completed`, `failed`, `interrupted`, `expired`.
- **Push Event Format**:
```json
{
  "status": "active",
  "elapsed_seconds": 124.5
}
```
