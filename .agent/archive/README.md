# .agent/archive — Historical Documents

These documents were archived on 2026-08-18 during the Batch 5 documentation cleanup.

They contain **historical project information** and are preserved for reference. They are **NOT operational instructions** and should NOT be treated as current by AI agents.

## Contents

| File | Original Purpose | Why Archived |
|------|-----------------|--------------|
| `FEATURE_TRACKER.md` | Phase-by-phase feature completion tracking | Fully superseded by `.agent/PROJECT_STATUS.md`. Contains stale buffer constant (1000ms vs actual 2000ms). |
| `PHASE3_DB_TASKS.md` | Phase 3 Database & Persistence task list | Phase 3 is complete. Contains stale `create_all()` instructions (Alembic is now used). Historical implementation notes marked inline. |
| `PHASE4_DASHBOARD_TASKS.md` | Phase 4 Live Dashboard task list | Phase 4 is complete. Contains stale page names (`SessionStartPage.jsx` → actual `HomePage.jsx`). Design requirements are historical. |
| `DAILY_STANDUP.md` | Team daily standup log | Single entry from June 7, 2026. No active coordination. References Pyannote testing that was later abandoned. |
| `QUICK_REFERENCE.md` | Meeting quality logic quick reference (locked v2 functions) | Logic is locked in `context_analyzer.py`. Duplicates information now in ARCHITECTURE.md and DECISION_LOG.md. |

### Archived 2026-09-10 (Claude Code efficiency audit, P0)

These were point-in-time audit *outputs*, not standing instructions. They were being mistaken for current directives in `.agent/`. Content is preserved verbatim; a future audit run may regenerate a fresh copy at `.agent/` root.

| File | Original Purpose | Why Archived |
|------|-----------------|--------------|
| `ARCHITECTURE_DRIFT_REPORT.md` | Snapshot of frozen-blueprint compliance (flagged the scikit-learn `scripts/train_outcome_predictor.py` drift) | Dated audit output. Re-run drift detection to regenerate; do not treat as a live checklist. |
| `DUPLICATE_DOCS_REPORT.md` | Snapshot of overlapping docs after the Batch 5 cleanup | Dated audit output. The cleanup it describes is complete. |
| `CHANGELOG_NEGATIVE_DECISIONS.md` | 2026-01-04 record of one negative-form-decision fix to `context_analyzer.py` | Historical. The behaviour is now covered by the locked-function status in `ARCHITECTURE.md`. |

## Authoritative Replacements

For current information, use:

- `.agent/PROJECT_STATUS.md` — replaces FEATURE_TRACKER.md
- `.agent/agents/database_agent.md` — replaces PHASE3_DB_TASKS.md
- `.agent/agents/frontend_agent.md` — replaces PHASE4_DASHBOARD_TASKS.md
- `.agent/ARCHITECTURE.md` — replaces QUICK_REFERENCE.md, CHANGELOG_NEGATIVE_DECISIONS.md
- `.agent/DECISION_LOG.md` — replaces QUICK_REFERENCE.md
- `.agent/agents/directory_manager_agent.md` — the workflow that regenerates ARCHITECTURE_DRIFT_REPORT.md / DUPLICATE_DOCS_REPORT.md / CLEANUP_AUDIT.md
