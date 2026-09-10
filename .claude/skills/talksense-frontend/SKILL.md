---
name: talksense-frontend
description: >-
  Frontend specialist context for TalkSense AI. Use when changing the React app
  under talksense-ui/ — pages, components (including dashboard/), hooks
  (useAudioCapture.js, useSessionWebSocket.js), services/api.js, routing, or
  Playwright E2E specs. Covers the tech stack constraints, WebSocket channel
  policies, session-lifecycle UI rules, build requirements, and forbidden changes.
---

# TalkSense AI — Frontend Specialist

Start with [`.agent/SPECIALIST_PREAMBLE.md`](../../../.agent/SPECIALIST_PREAMBLE.md)
(shared invariants, control docs, verification ladder).

**Full detail:** [`.agent/agents/frontend_agent.md`](../../../.agent/agents/frontend_agent.md)
— canonical directory map, WS channel table, dashboard layout rules, and E2E spec
inventory. Read it before non-trivial frontend work.

## When this applies

Any change under `talksense-ui/`. Backend session state, metric computation, and the
API contract definition are out of scope (`talksense-backend`, `.agent/API_CONTRACT.md`).

## Hard stops

- Tailwind CSS 3 only — no second CSS framework, no raw CSS files for component styling.
- Do not compute intelligence metrics (health score, sentiment, speaker attribution)
  in the frontend. All intelligence comes from backend push.
- Do not bypass the `POST /sessions` → 4-channel WS connect flow.
- Do not make the frontend authoritative over session state (backend is source of truth).
- Do not remove the stale-close guard in WS subscription cleanup.
- Keep `useSessionWebSocket` reconnect on exponential backoff; metrics channel drops
  stale frames (keep latest), alerts and transcript channels never drop.

## Before merging

- `npm run lint` passes; `npm run build` succeeds.
- `npm run test:e2e` (Playwright, mocked APIs) passes.
- `ort-wasm-simd-threaded.wasm` present in `dist/` after build (missing WASM silently
  breaks browser VAD).
- API calls match `.agent/API_CONTRACT.md` shapes.
