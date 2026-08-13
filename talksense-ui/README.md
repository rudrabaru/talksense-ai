# TalkSense AI — Frontend

> **Real-time conversation intelligence dashboard built with React 19 + Vite.**

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Framework | React 19 |
| Build Tool | Vite (Rolldown) |
| Styling | Tailwind CSS 3 |
| Routing | React Router DOM 7 |
| Audio | Web Audio API, @ricky0123/vad-web |
| Testing | Playwright (E2E) |
| PDF Export | jsPDF + html2canvas |

---

## Pages

| Page | Route | Purpose |
|------|-------|---------|
| `HomePage` | `/` | Landing page with session creation |
| `DashboardPage` | `/dashboard/:id` | **Main product** — live 3-panel dashboard |
| `UploadPage` | `/upload` | Audio file upload for batch analysis |
| `ResultsPage` | `/results` | Batch analysis results display |
| `SessionsPage` | `/sessions` | Session history and management |
| `ComparisonPage` | `/compare` | Side-by-side session comparison |
| `SystemAudioTester` | `/audio-test` | Audio device testing utility |
| `NotFoundPage` | `*` | 404 handler |

---

## Quick Start

```bash
cd talksense-ui
npm ci
cp .env.example .env    # Default: VITE_API_URL=http://localhost:8000
npm run dev
```

Open http://localhost:5173

See the root [README.md](../README.md) and [docs/SETUP_GUIDE.md](../docs/SETUP_GUIDE.md) for full setup instructions.

---

## Project Structure

```
talksense-ui/
├── src/
│   ├── pages/            # 8 route-level pages
│   ├── components/       # Reusable UI components
│   │   └── dashboard/    # Live dashboard panels
│   ├── hooks/            # Custom React hooks (WebSocket, audio)
│   ├── audio/            # Audio source management (Mic, System, PCM)
│   └── services/         # HTTP API client (api.js)
├── tests/                # Playwright E2E tests
├── public/               # Static assets + ONNX WASM files
├── .env.example          # Environment template
└── package.json
```

---

## Development

```bash
npm run dev       # Start dev server
npm run lint      # ESLint
npm run build     # Production build
npm run test:e2e  # Playwright E2E tests
```