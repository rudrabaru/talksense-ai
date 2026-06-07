# TalkSense AI — Cleanup Audit Report

This report outlines repository hygiene recommendations, classification targets, and potential risks, updated as of the latest repository audit.

---

## 🔍 Systematic Audit Classifications

The following status codes are assigned based on import searches, reference tracking, and routing analysis:
- **`SAFE_TO_DELETE`**: No code, routing, or documentation references found.
- **`UNSAFE_TO_DELETE`**: Active code references or imports exist.
- **`REQUIRES_MANUAL_REVIEW`**: Safely removable from a code standpoint, but referenced in setup/documentation or protected by directory safety rules.

---

## 🛑 DELETE_CANDIDATE items

### SAFE_TO_DELETE

| Path | Reason | Confidence | Risk Level |
|---|---|---|---|
| [temp.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/temp.md) | Legacy WASM troubleshooting notes from a previous session. No imports, routes, or references found. | 98% | Low |
| `uploads/0001_Business_English_Conversations_ESL_Business_Meeting_Conversation.m4a` | Redundant audio file. The active file is stored under `sample_audio/`. No code references. | 95% | Low |
| `uploads/0001_Winner_Best_Pitch_Competition_Willy_Green_Party_on_Demand.m4a` | Redundant audio file. The active file is stored under `sample_audio/`. No code references. | 95% | Low |
| `uploads/BuisinessMeeting.mp3` | Redundant audio file. The active file is stored under `sample_audio/`. Code references point to `sample_audio/`. | 95% | Low |
| `uploads/SalesMeeting.mp3` | Redundant audio file. The active file is stored under `sample_audio/`. No code references. | 95% | Low |
| `uploads/meeting_messy.mp3` | Redundant audio file. The active file is stored under `sample_audio/`. No code references. | 95% | Low |
| `uploads/sales_ambiguous.mp3` | Redundant audio file. The active file is stored under `sample_audio/`. No code references. | 95% | Low |
| [all_output.txt](file:///e:/Work/SCET%20Hackathon/talksense-ai/docs/archive/all_output.txt) | Stale verify log. Referenced only within itself. | 95% | Low |
| [deal_killer_output.txt](file:///e:/Work/SCET%20Hackathon/talksense-ai/docs/archive/deal_killer_output.txt) | Stale verify log. No references found. | 95% | Low |
| [final_verify.txt](file:///e:/Work/SCET%20Hackathon/talksense-ai/docs/archive/final_verify.txt) | Stale verify log. No references found. | 95% | Low |

---

### REQUIRES_MANUAL_REVIEW

| Path | Reason | Confidence | Risk Level | Audit Classification |
|---|---|---|---|---|
| [error_log.txt](file:///e:/Work/SCET%20Hackathon/talksense-ai/error_log.txt) | Empty (0-byte) log file. Free of code imports/routes, but referenced in [SETUP_GUIDE.md:L448](file:///e:/Work/SCET%20Hackathon/talksense-ai/docs/SETUP_GUIDE.md#L448) as a target for checking backend errors. Deleting it requires updating the setup documentation. | 95% | Low | **REQUIRES_MANUAL_REVIEW** |
| `backend/models` | Unused empty folder. Real-time NLP singletons live in `audio/` and `services/`, and database models are designated for `backend/db/models.py`. However, because `models/` is a protected name in the directory manager safety constraints, manual developer confirmation is required before pruning the empty folder. | 90% | Low | **REQUIRES_MANUAL_REVIEW** |
| [package-lock.json](file:///e:/Work/SCET%20Hackathon/talksense-ai/package-lock.json) | Root lock file. It is completely empty (no parent package.json exists in root, only in talksense-ui/). Since safety constraints strictly protect files named `package-lock.json` from deletion, human review is required to verify if this root file can be safely removed. | 95% | Medium | **REQUIRES_MANUAL_REVIEW** |

---

## 📂 ARCHIVED ITEMS (Migration Complete)

These items have been successfully moved into the `archive/` directory structure.

| Archived Path | Original Path | Reason for Archiving |
|---|---|---|
| [SURGICAL_FIX.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/deprecated_docs/SURGICAL_FIX.md) | `docs/archive/SURGICAL_FIX.md` | Legacy documentation describing previous surgical fix steps. |
| [SURGICAL_FIX_COMPLETE.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/deprecated_docs/SURGICAL_FIX_COMPLETE.md) | `docs/archive/SURGICAL_FIX_COMPLETE.md` | Legacy documentation describing previous surgical fix completion. |
| [SURGICAL_FIX_TEST_GUIDE.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/deprecated_docs/SURGICAL_FIX_TEST_GUIDE.md) | `docs/archive/SURGICAL_FIX_TEST_GUIDE.md` | Test guide for legacy surgical fix. |
| [BEFORE_AFTER_COMPARISON.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/deprecated_docs/BEFORE_AFTER_COMPARISON.md) | `docs/archive/BEFORE_AFTER_COMPARISON.md` | Comparison notes on legacy scoring model changes. |
| [QUALITY_SIMPLIFICATION.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/deprecated_docs/QUALITY_SIMPLIFICATION.md) | `docs/archive/QUALITY_SIMPLIFICATION.md` | Legacy scoring logic simplification blueprint. |
| [SIGNAL_FREEZE_COMPLETE.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/deprecated_docs/SIGNAL_FREEZE_COMPLETE.md) | `docs/archive/SIGNAL_FREEZE_COMPLETE.md` | Legacy blueprint for freezing signals. |
| [MEETING_INTENT_IMPLEMENTATION.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/deprecated_docs/MEETING_INTENT_IMPLEMENTATION.md) | `docs/archive/MEETING_INTENT_IMPLEMENTATION.md` | Reference notes for meeting intent. |
| [FINAL_FIX_STRATEGY.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/old_plans/FINAL_FIX_STRATEGY.md) | `.agent/FINAL_FIX_STRATEGY.md` | Legacy v3 frozen signals strategy; superseded by `ARCHITECTURE.md`. |
| [FROZEN_SIGNALS_FIX.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/old_plans/FROZEN_SIGNALS_FIX.md) | `.agent/FROZEN_SIGNALS_FIX.md` | Legacy v3 frozen signals analysis; superseded by `ARCHITECTURE.md`. |
| [FROZEN_SIGNALS_QUICK_REF.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/old_plans/FROZEN_SIGNALS_QUICK_REF.md) | `.agent/FROZEN_SIGNALS_QUICK_REF.md` | Legacy v3 quick reference; superseded by `ARCHITECTURE.md`. |

---

## 🔍 REVIEW_REQUIRED (Code Files)

These files need manual review before any action is taken.

| Path | Reason | Confidence | Risk Level |
|---|---|---|---|
| [TranscriptLive.jsx](file:///e:/Work/SCET%20Hackathon/talksense-ai/talksense-ui/src/components/TranscriptLive.jsx) | Legacy prototype live view. Route references exist in `App.jsx`, but it is superseded by the upcoming Phase 4 `DashboardPage.jsx`. Maintain until Phase 4 dashboard is fully operational. | 80% | Medium |
| [export_prediction_dataset.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/scripts/export_prediction_dataset.py) | Unused ML pipeline dataset script. Confirm if any future model training relies on this. | 75% | Medium |
| [train_outcome_predictor.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/scripts/train_outcome_predictor.py) | Unused ML model training script. Confirm if any future model training relies on this. | 75% | Medium |
| [run_advanced_analysis.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/scripts/run_advanced_analysis.py) | Obsolete analysis run script. Verify if it has any utility for developers. | 75% | Medium |

---

## 📌 KEEP

Protected core files that must not be deleted or modified.

| Path | Reason | Confidence | Risk Level |
|---|---|---|---|
| [speech_to_text.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/services/speech_to_text.py) | Legacy Whisper batch transcriber. While superseded by `audio/transcriber.py` for real-time, it powers the `/analyze` route which the legacy `UploadPage` requires. | 98% | High |
| [context_analyzer.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/services/context_analyzer.py) | Contains locked business quality calculation functions reused by both batch and real-time engines. | 100% | High |
| [nlp_engine.py](file:///e:/Work/SCET%20Hackathon/talksense-ai/backend/services/nlp_engine.py) | Core NLP helper and sentiment pipeline. | 100% | High |
| `All root config and lock files` | Protected by safety constraints (`package.json`, `.env.example`, `requirements.txt`, etc.). | 100% | High |
