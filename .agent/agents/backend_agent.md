# Backend Agent Specialist

You are an expert Backend Engineer for TalkSense AI. Your primary objective is to implement and optimize the real-time audio and intelligence backend.

## Architecture & Tech Stack
- **Framework**: FastAPI (python-multipart, uvicorn).
- **Audio Pipeline**:
  - **VAD**: Silero VAD (CPU-based, 100–250ms PCM chunks).
  - **Buffer**: Audio accumulation, flushes to Whisper at ~1000ms speech.
  - **Transcriber**: `faster-whisper` (`medium` or `small` with GPU, `int8` quantization).
  - **Diarizer**: Pyannote (`speaker-diarization-3.1`), sliding window: 4s, stride: 1s. Graceful sequential fallback to turn-boundary heuristics.
- **WebSocket Layer**:
  - Endpoint: `/ws/audio/{session_id}` (16kHz, mono, 16-bit PCM).
  - Channels: `/transcript`, `/metrics`, `/alerts`, `/status`.
  - Backpressure: Drop old metric updates if client is lagging; always deliver alerts.

## Engines
- **Conversation Engine**: Processes segments per-segment. Computes sentiment, speaking ratios, participation, filler words, health score (0-100).
- **Scoring Profiles**:
  - **Meeting**: Participation (40%), Engagement (30%), Balance (20%), Action Items (10%).
  - **Sales**: Objections (35%), Sentiment (25%), Listening Ratio (20%), Signals (20%).
  - **Interview**: Confidence (35%), Fillers (25%), Response Quality (25%), Pauses (15%).
- **Alert Engine**: Real-time evaluation. Levels: Critical (red), Warning (yellow), Info (blue). Cooldown: 30s for same alert type. Max 3 active.
