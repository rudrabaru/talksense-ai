# TalkSense AI — Architecture Drift Report

This report evaluates compliance with the frozen TalkSense AI v4 architecture blueprint.

---

## 🔍 Drift Analysis Summary

| System / Tech Stack | Approved Spec | Current Status | Drift Level | Notes |
|---|---|---|---|---|
| **Backend Framework** | FastAPI | Compliant | ✅ None | FastAPI router and endpoint mapping align with specs. |
| **Frontend Styling** | Vanilla CSS | Partially Compliant | ⚠️ Minor | DevDependencies and `index.css` include Tailwind CSS directives (`@tailwind base`, etc.). The codebase guidelines prefer vanilla CSS, indicating a styling drift. |
| **Database Stack** | PostgreSQL 17.5 | Compliant | ✅ None | SQL Alchemy models setup configured for port 5432. |
| **Database Migrations** | `create_all()` (No Alembic) | Potential Drift | ⚠️ Minor | `alembic` is present in `requirements.txt` despite the architecture freeze specifying not to use Alembic for initial setup. |
| **AI Models & Pipeline** | Faster-Whisper, Pyannote 3.1, Silero VAD | Compliant | ✅ None | Pipeline is correctly implemented sequentially for VRAM safety. |
| **Predictive Engines** | Heuristic Analytics + Sentiment | Potential Drift | ⚠️ Minor | Scripts like `train_outcome_predictor.py` introduce scikit-learn random forest models, which deviate from the core explainable NLP and sentiment engines. |

---

## 🚫 Flagged Violations

### 1. Tailwind CSS Integration in CSS Design System
- **Path**: [index.css](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/src/index.css#L3-L5) & [package.json](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/package.json#L32)
- **Violation**: The styling guidelines stipulate Vanilla CSS for maximum control and suggest avoiding TailwindCSS unless requested. The template uses `@tailwind` directives and tailwind dev dependencies.
- **Recommended Action**: Retain tailwind configuration for existing components to prevent UI breakage, but ensure future UI panels write pure Vanilla CSS.

### 2. Machine Learning Pipeline Experiments
- **Path**: `scripts/train_outcome_predictor.py`, `scripts/export_prediction_dataset.py`
- **Violation**: These scripts introduce scikit-learn models for predicting conversation outcomes, representing an unapproved alternative framework to the frozen analytics rules.
- **Recommended Action**: Classify these files as `REVIEW_REQUIRED` or `DELETE_CANDIDATE`. Do not deploy them in production.
