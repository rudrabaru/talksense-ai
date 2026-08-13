# TalkSense AI — Team Assignments & Responsibilities

This document outlines directory ownership, developer responsibilities, and merge conflict prevention rules for the TalkSense AI project.

---

## 👥 Developer Roles and Ownership

| Developer | Primary Focus | Owned Directories | Owned Files | Responsibilities | Forbidden Areas |
|---|---|---|---|---|---|
| **Rushabh** | Backend Core & AI Pipeline | `backend/audio/`<br>`backend/engine/`<br>`backend/db/`<br>`backend/ws/` | `backend/main.py`<br>`backend/requirements.txt`<br>`backend/.env.example` | - Implement real-time audio pipeline (VAD, buffer, Whisper).<br>- Build conversation engine, scoring weights, and alert engines.<br>- Maintain PostgreSQL with Alembic migrations and async SQLAlchemy.<br>- Maintain API contract and endpoint lifecycles.<br>- Integrate post-session Gemini AI pipeline. | `talksense-ui/` React codebase (except WS model alignment checks) and CSS styling sheets. |
| **Parthiv** | Frontend UI & Dashboards | `talksense-ui/src/components/`<br>`talksense-ui/src/pages/`<br>`talksense-ui/src/hooks/`<br>`talksense-ui/src/services/` | `talksense-ui/src/App.jsx`<br>`talksense-ui/src/index.css`<br>`talksense-ui/package.json` | - Build and maintain live React dashboard and session pages.<br>- Develop custom `useAudioCapture` and `useSessionWebSocket` hooks.<br>- Configure routing and API/WS client service calls.<br>- Style UI layouts using Tailwind CSS 3. | `backend/` core codebase (audio ingestion, ML model singletons, databases, and scoring profiles). |

---

## 🔒 Shared Directories and Shared Files
The following files require joint approval before modification:
- [.agent/](file:///e:/Work/SCET%20Hackathon/talksense-ai/.agent/): Control files (e.g. `API_CONTRACT.md`, `ARCHITECTURE.md`, `PROJECT_STATUS.md`).
- [docs/](file:///e:/Work/SCET%20Hackathon/talksense-ai/docs/): Active blueprints and guides.

---

## ⚠️ Merge Conflict Prevention Rules

### 1. API Contract-First Protocol
All endpoint additions or payload structural adjustments must be updated in [.agent/API_CONTRACT.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/.agent/API_CONTRACT.md) first. No code development on WebSocket channels or REST hooks may begin until both developers approve the API Contract modification.

### 2. Git Branching Rules
- **Backend Branches**: `feature/backend/<issue-desc>`
- **Frontend Branches**: `feature/frontend/<issue-desc>`
- **Protected Branch**: The `main` branch is strictly locked. Nothing should go to `main`.
- **Target Branch**: All code integration and pull requests must target the **`dev`** branch. At least one peer approval is required before merging.


### 3. Database Schema Modification Process
If **Rushabh** modifies `backend/db/models.py`:
- He must notify **Parthiv** immediately.
- Frontend developers must verify if metrics/report fetching services require schema alignment.
- Database schemas are managed by Alembic. Run `alembic upgrade head` to apply migrations.

### 4. Configuration and Environment File Hygiene
- Never commit active `.env` configuration files.
- Keep `.env.example` files fully up-to-date. When a new key-value pair is added (e.g., HF token, DB credentials, model names), append the placeholder key to the `.env.example` file immediately.
