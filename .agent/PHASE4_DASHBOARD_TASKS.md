# Phase 4 — Live React Dashboard

## Goal

Build the main product face: a 3-panel real-time dashboard that shows live transcript, conversation metrics, and alerts — connected to the WebSocket pipeline.

## Pre-conditions

- Phase 1 (Audio Pipeline) must be working
- Phase 2 (Conversation Engine) must be working
- Phase 3 (Database) should be done for full persistence, but Phase 4 can run with in-memory sessions

## Dashboard Layout

```
┌─────────────────────────────────────────────────────┐
│  Top Bar: Mode | Client | Timer | Health Score       │
├──────────────┬──────────────────┬───────────────────┤
│ LEFT         │ CENTER           │ RIGHT             │
│ Live         │ Conversation     │ Alert Feed        │
│ Transcript   │ Intelligence     │                   │
│              │                  │ 🔴 Critical       │
│ Speaker A    │ Sentiment: +72   │ 🟡 Warning        │
│ Speaker B    │ Health: 84       │ 🔵 Info           │
│ Speaker A    │ Talk Ratio: 60/40│                   │
└──────────────┴──────────────────┴───────────────────┘
```

## Task List

### Hooks (build first — others depend on these)

- [ ] **4.1 — `useAudioCapture.js`**
  - `talksense-ui/src/hooks/useAudioCapture.js`
  - Uses `AudioWorklet` (preferred) or `MediaRecorder` API
  - Converts mic input → PCM 16kHz mono 16-bit
  - Streams 250ms chunks to `/ws/audio/{session_id}`
  - `start()`, `stop()`, `isCapturing` state
  - Handles mic permission denial gracefully (shows error, doesn't crash)

- [ ] **4.2 — `useSessionWebSocket.js`**
  - `talksense-ui/src/hooks/useSessionWebSocket.js`
  - Opens 4 WebSocket connections: transcript, metrics, alerts, status
  - Auto-reconnect on drop (exponential backoff, max 5 retries)
  - Exposes: `transcript[]`, `metrics{}`, `alerts[]`, `status`
  - For metrics: only keep latest state (never accumulate old metric frames)
  - For transcript: append new segments to array
  - For alerts: append, sorted by severity

### Components

- [ ] **4.3 — `TranscriptPanel.jsx`**
  - `talksense-ui/src/components/dashboard/TranscriptPanel.jsx`
  - Receives `transcript[]` from hook
  - Color-codes each segment by speaker (Speaker A = blue, Speaker B = purple, etc.)
  - Shows sentiment badge per segment (🟢 positive, 🔴 negative, ⚪ neutral)
  - Highlights filler words in yellow
  - Auto-scrolls to latest segment
  - Smooth scroll, not jump

- [ ] **4.4 — `IntelligencePanel.jsx`**
  - `talksense-ui/src/components/dashboard/IntelligencePanel.jsx`
  - Receives `metrics{}` from hook
  - Animated Health Score gauge (0–100, green/yellow/red by range)
  - Sentiment trend sparkline (last 20 data points)
  - Speaking ratio bar (Speaker A vs B)
  - Participation donut chart
  - Mode-specific cards:
    - Sales mode: objection count, buying signals
    - Meeting mode: action items, filler count
    - Interview mode: confidence score, pause count

- [ ] **4.5 — `AlertPanel.jsx`**
  - `talksense-ui/src/components/dashboard/AlertPanel.jsx`
  - Receives `alerts[]` from hook
  - Sorted by severity (Critical first)
  - Toast-style entry animation (slide in from right)
  - Alert age indicator (e.g., "2m ago")
  - Max 3 visible, older ones fade out with animation
  - Color-coded: 🔴 Critical (red), 🟡 Warning (amber), 🔵 Info (blue)

### Pages

- [ ] **4.6 — `SessionStartPage.jsx`**
  - `talksense-ui/src/pages/SessionStartPage.jsx`
  - Step 1: Select mode (Meeting / Sales / Interview) — big card buttons
  - Step 2: Select or create client (dropdown + inline create)
  - Step 3: If returning client, show `ClientBriefingCard` (placeholder for Phase 5)
  - Start button → `POST /sessions` → navigate to `/dashboard/:sessionId`

- [ ] **4.7 — `DashboardPage.jsx`** ← MAIN PRODUCT
  - `talksense-ui/src/pages/DashboardPage.jsx`
  - Mounts `useSessionWebSocket` and `useAudioCapture` hooks
  - Renders 3-panel layout
  - Top bar: mode badge, client name, elapsed timer, health score
  - Left: `<TranscriptPanel />`
  - Center: `<IntelligencePanel />`
  - Right: `<AlertPanel />`
  - End Session button → `DELETE /sessions/{id}` → navigate to `/report/:id`
  - On mount: request mic permission
  - Reconnect on WebSocket drop (handled by hook)

### App.jsx Routes Update

- [ ] **4.8 — Update `App.jsx`**
  - Replace old route config with:
    ```
    /                  → HomePage
    /start             → SessionStartPage
    /dashboard/:id     → DashboardPage
    /upload            → UploadPage (keep)
    /results           → ResultsPage (keep)
    /history           → SessionHistoryPage (placeholder, Phase 5)
    /clients           → ClientsPage (placeholder, Phase 5)
    /report/:id        → ReportPage (placeholder, Phase 5)
    ```

## Files to Create

| File | Status |
|------|--------|
| `talksense-ui/src/hooks/useAudioCapture.js` | ❌ TODO |
| `talksense-ui/src/hooks/useSessionWebSocket.js` | ❌ TODO |
| `talksense-ui/src/components/dashboard/TranscriptPanel.jsx` | ❌ TODO |
| `talksense-ui/src/components/dashboard/IntelligencePanel.jsx` | ❌ TODO |
| `talksense-ui/src/components/dashboard/AlertPanel.jsx` | ❌ TODO |
| `talksense-ui/src/pages/SessionStartPage.jsx` | ❌ TODO |
| `talksense-ui/src/pages/DashboardPage.jsx` | ❌ TODO |

## Files to Modify

| File | Change |
|------|--------|
| `talksense-ui/src/App.jsx` | Replace route config |

## Design Requirements

- Dark mode dashboard (dark background, high contrast)
- Micro-animations: health score gauge animates on update, alerts slide in
- Responsive: works at 1280px+ width minimum
- No external component libraries — use vanilla CSS + existing design system in `index.css`
- Speaker colors: consistent per session (assign on first segment, persist)

## Verification Checklist

- [ ] Dashboard opens, mic permission dialog appears
- [ ] Speak → transcript appears within 3 seconds
- [ ] Speaker A and Speaker B are color-differentiated
- [ ] Health score updates as transcript grows
- [ ] At least one alert fires in a 2-minute test conversation
- [ ] End Session → navigates to /report/:id (even if report page is placeholder)
- [ ] Page is visually polished (not MVP-looking)
