---
name: talksense-performance
description: >-
  Performance specialist context for TalkSense AI. Use when working on latency,
  throughput, memory, GPU utilization, or WebSocket backpressure across the backend
  pipeline — the 4 GB VRAM constraint, the gpu_concurrency semaphore, sequential
  Whisper/sentiment execution, the audio buffer latency-vs-accuracy trade-off, the
  5-second flush loop, and per-channel delivery guarantees.
---

# TalkSense AI — Performance Specialist

Start with [`.agent/SPECIALIST_PREAMBLE.md`](../../../.agent/SPECIALIST_PREAMBLE.md)
(shared invariants, control docs, verification ladder).

**Full detail:** [`.agent/agents/performance_agent.md`](../../../.agent/agents/performance_agent.md)
— canonical hardware constraints, the design-target table (with VERIFIED vs NOT
VERIFIED marked per row), and the regression checklist.

## When this applies

Latency/throughput/memory/GPU/backpressure concerns. AI accuracy trade-offs and
scoring formulas are backend business logic, not performance (`talksense-backend`).

## Hard stops

- 4 GB VRAM target (RTX 3050). Faster-Whisper runs `int8` — mandatory. 500 MB free
  VRAM headroom required.
- Whisper and the sentiment Transformer must never run concurrently on the GPU.
- Do not remove or bypass the `gpu_concurrency` semaphore (`audio/gpu_manager.py`).
- Do not reduce `TARGET_DURATION_MS` for latency without an accuracy evaluation; do
  not change buffer constants outside an approved design.
- Do not present a "NOT CURRENTLY VERIFIED" design target as a measured fact.
- Keep the background flusher (`_flush_loop`) a long-running coroutine started at
  app startup; keep `_FLUSH_SEMAPHORE` gating concurrent flush workers.

## Before merging

- Buffer constants unchanged (or the change is intentionally documented).
- Whisper still runs in threadpool; no synchronous calls in the audio ingest path.
- Channel policies intact: `/ws/metrics` drops stale frames; `/ws/alerts`,
  `/ws/transcript`, `/ws/status` never drop.
