# TalkSense AI — Architecture Drift Report

This report evaluates compliance with the frozen TalkSense AI v4 architecture blueprint.

---

## 🔍 Drift Analysis Summary

| System / Tech Stack | Approved Spec | Current Status | Drift Level | Notes |
|---|---|---|---|---|
| **Backend Framework** | FastAPI | Compliant | ✅ None | FastAPI router and endpoint mapping align with specs. |
| **Frontend Styling** | Tailwind CSS 3 | Compliant | ✅ None | `index.css` includes Tailwind directives and `tailwindcss` is a devDependency. |
| **Database Stack** | PostgreSQL 16+ | Compliant | ✅ None | SQLAlchemy models setup configured for port 5432. |
| **Database Migrations** | Alembic | Compliant | ✅ None | `alembic` is in `requirements.txt` and migration scripts exist in `backend/alembic/`. `create_all()` is NOT used. |
| **AI Models & Pipeline** | Faster-Whisper, Silero VAD | Compliant | ✅ None | Pipeline is correctly implemented sequentially for VRAM safety. |
| **Speaker Diarization** | Experimental Only | Compliant | ✅ None | Pyannote/Diart code exists only in `experimental/diart/`. NOT imported by production code. |
| **Predictive Engines** | Heuristic Analytics + Sentiment | Potential Drift | ⚠️ Minor | Scripts like `train_outcome_predictor.py` introduce scikit-learn random forest models, which deviate from the core explainable NLP and sentiment engines. |

---

## 🚫 Flagged Violations

### 1. Machine Learning Pipeline Experiments
- **Path**: `scripts/train_outcome_predictor.py`, `scripts/export_prediction_dataset.py`
- **Violation**: These scripts introduce scikit-learn models for predicting conversation outcomes, representing an unapproved alternative framework to the frozen analytics rules.
- **Recommended Action**: Classify these files as `REVIEW_REQUIRED` or `DELETE_CANDIDATE`. Do not deploy them in production.
