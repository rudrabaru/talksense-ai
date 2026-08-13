# TalkSense AI — Architectural Decision Log

This document serves as the permanent project memory, recording core design decisions, hardware adaptations, and architectural path selections.

---

## 🪵 Decisions Log

### 1. Database Engine Selection
- **Date**: 2026-06-06
- **Decision**: Adopt **PostgreSQL 17.5** on `localhost:5432` as the central persistence layer.
- **Reason**: Already installed, configured, and operational on developer workstations, eliminating bootstrap overhead.
- **Impact**: Provides robust support for relational entities (users, clients, sessions, reports) with optimized index lookup performance.
- **Owner**: CTO / Architecture Board

> *Note (2026-08-13): CI workflows target `postgres:16`. The current supported minimum is PostgreSQL 16+. The original decision record above is preserved as-is.*

---

### 2. Async DB Access Layer
- **Date**: 2026-06-06
- **Decision**: Implement **SQLAlchemy 2.x declarative async ORM** with the **`asyncpg`** driver.
- **Reason**: FastAPI operates asynchronously. Blocking database drivers would choke the server under load or interrupt real-time binary audio streams.
- **Impact**: High-concurrency operations on sessions and transcript flushes do not block main server loops.
- **Owner**: CTO

---

### 3. GPU Constraints & Model Quantization
- **Date**: 2026-06-06
- **Decision**: Constrain local execution to target an **RTX 3050 Laptop GPU (4GB VRAM)**, utilizing **Faster-Whisper with `int8` quantization**.
- **Reason**: Standard development laptops have a 4GB VRAM budget. Default `float16` or simultaneous execution of Whisper and Pyannote leads to Out-Of-Memory (OOM) crashes.
- **Impact**: Quantization reduces VRAM footprints to safe levels (~1.2GB for Whisper). Enables sequential model execution with GPU hand-offs.
- **Owner**: CTO

---

### 4. PyTorch Build Re-alignment
- **Date**: 2026-06-06
- **Decision**: Explicitly reinstall PyTorch using the **CUDA 12.x wheels** rather than the default `+cpu` installation.
- **Reason**: The initial package manager setup loaded `2.9.1+cpu`, rendering GPU acceleration unavailable.
- **Impact**: Boosts audio transcribing and diarization throughput by 10x, enabling the pipeline to hit the 2.5s latency budget.
- **Owner**: CTO

---

### 5. CPU-bound Voice Activity Detection
- **Date**: 2026-06-06
- **Decision**: Integrate **Silero VAD** running exclusively on the **CPU**.
- **Reason**: Silero is lightweight and highly accurate, and running it on CPU preserves valuable GPU VRAM for transcription tasks.
- **Impact**: Blocks silence/background noise from entering the transcription queue, preventing empty GPU model execution.
- **Owner**: CTO

---

### 6. Heuristic Speaker Fallback
- **Date**: 2026-06-06
- **Decision**: Design a sequential/rolling window diarizer with a **heuristic turn-boundary fallback** if HuggingFace tokens are missing or VRAM falls below 500MB.
- **Reason**: Prevents system-wide application failure if a user is offline or the GPU runs out of memory.
- **Impact**: Application degrades gracefully, labeling speakers by conversational alternation rather than crashing.
- **Owner**: CTO

---

### 7. WebSocket Channel Segregation
- **Date**: 2026-06-06
- **Decision**: Segregate the frontend-backend WebSocket interface into **5 distinct channels**: 1 inbound (`/ws/audio`) and 4 outbound (`/ws/transcript`, `/ws/metrics`, `/ws/alerts`, `/ws/status`).
- **Reason**: Prevents message processing delays and simplifies React subscription hooks by isolating data types.
- **Impact**: Allows backpressure rule enforcement (discarding old `/metrics` frames while guaranteeing delivery of `/alerts`).
- **Owner**: CTO

---

### 8. Heuristics over Machine Learning Predictors
- **Date**: 2026-06-06
- **Decision**: Freeze the conversation engine evaluation rules to use **deterministic heuristics** (scoring profiles JSON) rather than Random Forest predictors.
- **Reason**: Ensures conversation health scoring is transparent, explainable, and deterministic. Avoids importing bloated ML libraries.
- **Impact**: Scoring profiles are configuration-driven, and results are 100% reproducible.
- **Owner**: Architecture Board

---

### 9. Branch Lock and Integration Target
- **Date**: 2026-06-07
- **Decision**: Lock the `main` branch from direct commits and merges, designating **`dev`** as the base integration branch.
- **Reason**: Simplifies code integration for the 2-person team, isolating the release candidate state from active development.
- **Impact**: All feature pull requests merge into `dev`, leaving `main` in a clean, stable state.
- **Owner**: DevOps / CTO
