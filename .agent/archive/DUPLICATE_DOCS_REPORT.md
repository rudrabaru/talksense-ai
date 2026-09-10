# TalkSense AI — Duplicate Documentation Report

This report identifies overlapping, redundant, or superseded documentation across `docs/`, `docs/archive/`, and `.agent/`.

---

## 🔍 Redundancy Analysis & Similarity Estimates

### 1. Legacy Surgical Fix Instructions
- **Files Involved**:
  - [SURGICAL_FIX.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/deprecated_docs/SURGICAL_FIX.md) (Archived)
  - [SURGICAL_FIX_COMPLETE.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/deprecated_docs/SURGICAL_FIX_COMPLETE.md) (Archived)
  - [SURGICAL_FIX_TEST_GUIDE.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/deprecated_docs/SURGICAL_FIX_TEST_GUIDE.md) (Archived)
- **Overlap/Similarity**: **~85% similarity**
- **Details**: All three files document the step-by-step resolution of legacy v3 meeting quality calculation bugs. They are redundant now that Phase 2 has frozen `context_analyzer.py`. They have been migrated into `archive/deprecated_docs/`.
- **Recommended Action**: Retain only `SURGICAL_FIX_COMPLETE.md` in `archive/deprecated_docs/` and schedule the others for deletion.

### 2. V3 Frozen Signals Agent Guides
- **Files Involved**:
  - [FINAL_FIX_STRATEGY.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/old_plans/FINAL_FIX_STRATEGY.md) (Archived)
  - [FROZEN_SIGNALS_FIX.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/old_plans/FROZEN_SIGNALS_FIX.md) (Archived)
  - [FROZEN_SIGNALS_QUICK_REF.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/archive/old_plans/FROZEN_SIGNALS_QUICK_REF.md) (Archived)
- **Overlap/Similarity**: **~75% similarity**
- **Details**: Overlapping guidelines regarding the frozen rules of the meeting quality algorithm. These guidelines have been fully integrated into the newer [ARCHITECTURE.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/.agent/ARCHITECTURE.md) and [SKILLS.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/.agent/SKILLS.md). They have been migrated into `archive/old_plans/`.
- **Recommended Action**: Retain for historical context only.

### 3. Architecture Blueprint and Implementation Plan
- **Files Involved**:
  - [TalkSenseAI_New_Plan.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/docs/archive/TalkSenseAI_New_Plan.md)
  - [new_implementation_plan.md](file:///e:/Work/SCET%20Hackathon/talksense-ai/docs/new_implementation_plan.md)
- **Overlap/Similarity**: **~40% similarity**
- **Details**: The implementation plan derives its tech stack table, WebSocket channel configurations, and database model schema details directly from the architecture blueprint.
- **Recommended Action**: **KEEP BOTH**. The blueprint represents the frozen design and vision, whereas the implementation plan is the active, phase-by-phase development guide.
