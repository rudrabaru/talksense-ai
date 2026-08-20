# Frontend Agent Specialist

## Authoritative References — Read These First

Before making any frontend change, read:

- `.agent/API_CONTRACT.md` — all REST and WebSocket endpoint contracts the frontend must consume
- `.agent/ARCHITECTURE.md` — system design; backend is the source of truth for session state
- `.agent/DEVELOPMENT_RULES.md` — Tailwind CSS constraint, WS reconnect requirements, git workflow
- `.agent/TESTING_CHECKLIST.md` — what frontend testing currently exists

---

## Scope of Responsibility

The frontend agent owns the React application under `talksense-ui/`.

**Does NOT own:**
- Backend session state or metric computation → Backend Agent
- API contract definition → defined in `.agent/API_CONTRACT.md`
- Database schema → Database Agent
- CI/CD pipeline configuration → outside specialist scope

---

## Directory Ownership

```
talksense-ui/
├── src/
│   ├── App.jsx                           ← router root, route definitions
│   ├── main.jsx                          ← React 19 entry point
│   ├── pages/
│   │   ├── HomePage.jsx                  ← session start, mode/client selection
│   │   ├── DashboardPage.jsx             ← live session 3-panel layout
│   │   ├── SessionsPage.jsx              ← session history list
│   │   ├── ResultsPage.jsx               ← post-session report/summary
│   │   ├── ComparisonPage.jsx            ← session comparison view
│   │   ├── UploadPage.jsx                ← legacy batch audio upload
│   │   ├── SystemAudioTester.jsx         ← audio device diagnostic page
│   │   └── NotFoundPage.jsx              ← 404
│   ├── components/
│   │   ├── ClientBriefingCard.jsx        ← client memory display
│   │   ├── InsightCard.jsx               ← key insight display
│   │   ├── SentimentBadge.jsx            ← sentiment label pill
│   │   ├── TranscriptBlock.jsx           ← single transcript segment
│   │   └── dashboard/
│   │       ├── TranscriptPanel.jsx       ← left panel: live transcript feed
│   │       ├── MetricsPanel.jsx          ← centre panel: health, charts, ratios
│   │       ├── AlertsPanel.jsx           ← right panel: alert feed (max 3)
│   │       ├── CoachingPanel.jsx         ← coaching suggestions panel
│   │       ├── ConversationSidebar.jsx   ← conversation metadata sidebar
│   │       └── SessionStatusBar.jsx      ← top status bar
│   ├── hooks/
│   │   ├── useAudioCapture.js            ← browser-side VAD + PCM capture
│   │   └── useSessionWebSocket.js        ← 4-channel WS subscription hook
│   ├── services/
│   │   └── api.js                        ← REST API client (fetch wrappers)
│   └── audio/                            ← browser VAD WASM assets (if bundled)
├── tests/
│   └── e2e/                              ← Playwright E2E specs (8 files)
├── playwright.config.ts
└── package.json
```

**Important:** The old agent referenced `SessionStartPage.jsx` and `ReportPage.jsx` — these names do not exist. The actual pages are `HomePage.jsx` and `ResultsPage.jsx`.

---

## Tech Stack

- **React 19** — functional components only.
- **Tailwind CSS 3** — all styling must use Tailwind. Do not introduce additional CSS frameworks or raw CSS files for component styling.
- **react-router-dom v7** — client-side routing.
- **Browser VAD**: `@ricky0123/vad-web` (ONNX-based) — runs in the browser, classifies speech/silence, sends only speech PCM to the backend. This is NOT MediaRecorder-only; it requires the ONNX WASM assets to be present in the build output.
- **Audio format**: 16kHz, mono, 16-bit signed PCM chunks from `useAudioCapture.js`.
- **Build**: Vite (via `rolldown-vite` override).
- **E2E testing**: Playwright only. No unit test framework (Vitest/Jest) is configured.

---

## Key Architectural Invariants

### Backend Is Source of Truth for Session State

The backend `SessionManager` owns session lifecycle. The frontend:
- calls `POST /sessions` to create a session and receives `session_id` and `ws_token`.
- connects to the 4 WebSocket channels using that `session_id`.
- receives pushed state — it does NOT compute metrics, scores, or alerts locally.
- must reconcile its local UI state with the backend on reconnect using `GET /dashboard/{session_id}`.

Do NOT derive metric values in the frontend from raw audio data. All intelligence comes from backend push.

### WebSocket Channels

`useSessionWebSocket.js` manages 4 read-only channels per session:

| Channel | Path | Purpose |
|---------|------|---------|
| Transcript | `/ws/transcript/{session_id}` | Live segment push |
| Metrics | `/ws/metrics/{session_id}` | Metric snapshot push |
| Alerts | `/ws/alerts/{session_id}` | Alert event push |
| Status | `/ws/status/{session_id}` | Session state changes |

- Implement reconnect with **exponential backoff** — required per `.agent/DEVELOPMENT_RULES.md`.
- Metrics channel: **discard stale intermediate frames** if the client queue lags. Keep only the latest state.
- Alerts channel: **never drop** — all alert events must be delivered to the UI.
- WS token (`ws_token`) is returned by `POST /sessions`. **Note:** current backend does NOT verify this token on WS connect (security gap documented in Security Agent). The token should still be passed as designed for future enforcement.

### Session Lifecycle UI

- Session mode is selected on `HomePage.jsx` and sent with `POST /sessions`.
- Once session is created, navigate to `/dashboard/{session_id}`.
- Dashboard stays live until user ends the session or backend signals completion via the status channel.
- On `completed` status, the UI should transition gracefully (no freeze/blank).
- Session lifecycle UI bug (double-close causing freeze) was fixed — do not revert the `stale close ignored` guard in `subscriptions.py`.

### Dashboard 3-Panel Layout

- **Left** (`TranscriptPanel`): scrolling transcript feed, auto-scroll to latest segment.
- **Centre** (`MetricsPanel`): health score gauge, sentiment, speaking ratio, mode-specific KPIs.
- **Right** (`AlertsPanel`): max 3 active alerts, sorted by severity, entry animation on new alert.

---

## Frontend Testing

All automated tests are **Playwright E2E only** using **mocked APIs**.

| Spec | What It Tests |
|------|--------------|
| `navigation.spec.ts` | Page routing |
| `navigation_launch.spec.ts` | Session launch navigation |
| `recording.spec.ts` | Start → Pause → History flow |
| `dashboard_metrics.spec.ts` | Mock WS metrics render in DOM |
| `transcript.spec.ts` | Transcript segment rendering |
| `error_handling.spec.ts` | UI error states |
| `history.spec.ts` | Sessions list from mock data |
| `dashboard.spec.ts` | Dashboard page load |

All tests mock backend REST and WebSocket calls — they **do not** test against a live backend.

**No component unit tests exist** (no Vitest or Jest configured).

`useAudioCapture.js` and `useSessionWebSocket.js` reconnect behaviour are **NOT VERIFIED** by automated tests.

---

## Build Requirements

- `npm run lint` must pass (ESLint) before PR merge.
- `npm run build` must succeed (Vite bundle) — CI validates this.
- `npm run test:e2e` runs Playwright — CI runs this in `frontend-ci.yml`.
- Verify `ort-wasm-simd-threaded.wasm` is present in `dist/` after build — missing WASM silently breaks browser VAD.
- `VITE_API_URL` and `VITE_WS_URL` must be set to production URLs before deploying (not `localhost`).

---

## Required Checks Before Merging Frontend Changes

- [ ] All styling uses Tailwind CSS — no additional CSS frameworks introduced
- [ ] `useSessionWebSocket` reconnect with exponential backoff preserved
- [ ] Metric backpressure (drop stale, keep latest) preserved
- [ ] Alert delivery (never drop) preserved
- [ ] API calls match `.agent/API_CONTRACT.md` shapes
- [ ] ESLint passes (`npm run lint`)
- [ ] Build succeeds (`npm run build`)
- [ ] Playwright E2E passes

---

## Forbidden Changes

- Do not introduce a second CSS framework alongside Tailwind.
- Do not compute intelligence metrics (health score, sentiment, speaker attribution) in the frontend.
- Do not bypass the `POST /sessions` → WS connect flow for session creation.
- Do not make the frontend authoritative over session state (backend is source of truth).
- Do not remove the stale-close guard in WS subscription cleanup.
