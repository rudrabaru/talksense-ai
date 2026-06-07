# TalkSense AI — Development Rules & Workflow

This document details the development rules, branching strategies, commit conventions, code reviews, and agent guidelines for the 2-person startup team (Parthiv & Rushabh).

---

## 🌿 Git Workflow

We use a lightweight, fast-paced branch-and-PR workflow to maintain speed without sacrificing stability.

### 1. Branch Naming Convention
- **Format**: `<type>/<owner>/<description>`
- **Types**:
  - `feature`: New features or implementation phases.
  - `bugfix`: Defect corrections.
  - `refactor`: Structural codebase improvements.
  - `chore`: Dependency updates, config, and repository hygiene.
- **Owners**: `parthiv` (Frontend) or `rushabh` (Backend).
- **Examples**:
  - `feature/parthiv/dashboard-ws-hook`
  - `feature/rushabh/sqlalchemy-async-models`
  - `bugfix/rushabh/whisper-vram-oom`

### 2. Commit Message Standard
We use simplified conventional commits to keep history searchable:
- `feat: <description>` (e.g., `feat: add useAudioCapture hook for raw PCM`)
- `fix: <description>` (e.g., `fix: catch Pyannote HuggingFace token validation error`)
- `refactor: <description>` (e.g., `refactor: extract scoring profile weights to config`)
- `chore: <description>` (e.g., `chore: clean uploads duplicate audio files`)

### 3. Pull Request & Merging Rules
- **No commits or merges to `main`**: The `main` branch is locked and reserved.
- **Base Integration Branch**: All features, bugfixes, and PRs must target and merge into the **`dev`** branch.
- **Review Requirement**: A PR targeting `dev` requires exactly **1 peer review** (Parthiv reviews Rushabh's code, Rushabh reviews Parthiv's code) before merge.
- **CI/Build Pass**: Local tests must pass (`pytest` for backend, `npm run build` for frontend verification) before PR is merged.
- **Merge Strategy**: Fast-forward merge or squash-and-merge to keep `dev` history clean.


---

## 🔍 Code Review Checklist

Reviewers must verify these target areas before clicking merge:

### Backend Checks (Reviewed by Parthiv)
- [ ] **API Compliance**: Payload structures match the specifications in [API_CONTRACT.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/.agent/API_CONTRACT.md).
- [ ] **GPU & Memory Protection**: Model loads are handled as singletons and run sequentially. Int8 quantization is preserved.
- [ ] **Non-blocking WS**: Database persistence writes are offloaded to background threads or async queues to avoid blocking the audio ingest.
- [ ] **No Alembic Migrations**: Local PostgreSQL models initialized via `create_all()`.

### Frontend Checks (Reviewed by Rushabh)
- [ ] **Vanilla CSS Only**: No new CSS frameworks (such as Tailwind or Bootstrap) introduced.
- [ ] **WS Reconnection**: Hooks implement reconnect logic with exponential backoff and correct status reporting.
- [ ] **Backpressure Handling**: Metric arrays are throttled/discarded if connection queue overflows.

---

## 🤖 Agent Usage Rules (For AI Coding Assistants)

AI Agents (including Antigravity) must follow these constraints:

1. **Plan Before Execution**: For complex tasks, the agent must research the target files, write an implementation plan to `implementation_plan.md`, and wait for developer approval.
2. **Directory Hygiene**: The agent must never delete or move files automatically. Cleanups must be logged in `CLEANUP_AUDIT.md` for human execution.
3. **Directory Constraints**: The agent must NOT create root-level folders unless specified in the active blueprint.
4. **Task Tracking**: The agent must maintain `task.md` during execution to mark progress.
5. **No Placeholders**: The agent must write complete, functional code, avoiding `// TODO` or shortened snippets.

---

## 🏗️ Architecture Compliance Rules

- **Locked Core Functions**: Do NOT alter `compute_meeting_quality_v2()`, `compose_executive_summary_v2()`, or `generate_key_insights_v2()` in `backend/services/context_analyzer.py`.
- **VRAM Constraint (4GB)**: Diarization must never run concurrently with transcription on the GPU. Switch speaker diarization to heuristic mode if VRAM drops below 500MB.
- **Heuristics Over Custom ML**: Do not introduce scikit-learn models or predictive neural nets for outcome tracking. Stick to approved explainable rule-based scoring profiles.
