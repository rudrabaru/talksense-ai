---
name: verify
description: >-
  Standardized, proportional verification workflow for TalkSense AI. Invoke with
  /verify before claiming a change is verified or before a dev merge. Classifies the
  change surface (docs/config-only vs application/runtime vs accuracy-critical), runs
  the matching subset of the CLAUDE.md verification commands, and reports exact
  commands, results, failures, and the L1-L5 ladder level reached.
disable-model-invocation: true
allowed-tools: Bash, Read, Grep, Glob
---

# /verify — Proportional Verification

Run the cheapest verification level that could disprove the change. Do not run
expensive checks for a change that cannot reach them.

## Inputs

- Tracked changes: !`git diff --stat HEAD`
- Untracked files: !`git status --short -uall`
- Scope hint (paths or description), if given: $ARGUMENTS

The **changed-file set** is every path in the tracked-changes stat PLUS every
untracked path listed above. Classify against that whole set. Never rely on
`git diff` alone — it does not show untracked files.

Canonical references (consult, do not restate):
[`CLAUDE.md`](../../../CLAUDE.md) "Verification commands" table (exact commands, run-from
dirs) · [`.agent/SPECIALIST_PREAMBLE.md`](../../../.agent/SPECIALIST_PREAMBLE.md)
"Verification ladder" (L1-L5 definitions) · [`accuracy`](../accuracy/SKILL.md) Step 1
(canonical accuracy-critical surface).

## Step 1 — classify the change (pick exactly one)

Evaluate every path in the changed-file set, tracked and untracked alike.

- **DOC/CONFIG-ONLY** — every changed path is documentation or inert metadata:
  `*.md`, `.agent/**`, `.claude/**`, `LICENSE`, editor/IDE dotfiles, or code
  comments only. It is **not** DOC/CONFIG-ONLY if any changed path is:
  - `backend/**/*.py`, `talksense-ui/src/**`, `backend/alembic/**`,
    `backend/prompts/**`;
  - runtime-loaded data or config: `backend/config/**` (e.g.
    `backend/config/keywords.json`), any keyword or scoring data file, `*.env*`;
  - frontend build/runtime config: `talksense-ui/vite.config.*`,
    `talksense-ui/*.config.*`, `talksense-ui/index.html`, `talksense-ui/public/**`;
  - dependency manifest or lockfile: `requirements*.txt`, `pyproject.toml`,
    `package.json`, `package-lock.json`;
  - CI or workflow config: `.github/**`.
  When unsure whether a path is inert, classify as APPLICATION/RUNTIME, not
  DOC/CONFIG-ONLY. Only a genuinely DOC/CONFIG-ONLY change skips Python/JS lint
  and tests.
- **APPLICATION/RUNTIME** — a changed path is application code, runtime-loaded
  config/data, a dependency manifest/lockfile, frontend build config, or CI
  config, and no accuracy-critical path (below) is touched. Run L1, then L2;
  escalate to L3 by risk.
- **ACCURACY-CRITICAL** — a changed path is on the accuracy-critical surface **as
  defined by `/accuracy` Step 1** ([`accuracy/SKILL.md`](../accuracy/SKILL.md)); do
  not maintain a second definition here. In brief that surface is `backend/audio/`,
  `backend/ws/audio_handler.py`, `nlp_engine.py` sentiment pipeline,
  `backend/engine/**` metric and scoring code including `scoring_profiles.py`,
  `backend/services/context_analyzer.py` metric/scoring code (locked functions and
  otherwise), `backend/benchmark_dataset/`, and any ground truth. Run L1-L3, then
  STOP and tell the user to run `/accuracy`; do not self-certify accuracy here. If
  unsure whether a path is on that surface, route to `/accuracy` and let it decide.

Defend the classification by listing which changed paths drove it.

## Step 2 — run the mapped subset

Use the commands from the `CLAUDE.md` "Verification commands" table by name; do not
invent flags or paths.

- **L1 static/lint** (APPLICATION/RUNTIME, ACCURACY-CRITICAL): Ruff check, Black
  `--check`, Pyright — argument `backend/`.
- **L2 focused tests**: the pytest unit suite from `backend/` with the three
  `--ignore` entries from the table; narrow with `-k` to the changed area when
  possible.
- **L3 broader regression**: full pytest unit suite (same ignores), no `-k` filter.
- **Frontend**: `npm run lint` then `npm run build` from `talksense-ui/` — only when
  a `talksense-ui/` path is in the changed-file set.

## Step 3 — report (fixed template)

```
## /verify report
- Change class: <DOC/CONFIG-ONLY | APPLICATION/RUNTIME | ACCURACY-CRITICAL>
  justification: <which changed paths (tracked + untracked) put it in this class>
- Commands run:
  - `<command verbatim>` (from <dir>) -> PASS | FAIL | BLOCKED
    <full failing output on FAIL; setup/import error is BLOCKED, never PASS>
- Ladder level reached: <none (docs/config-only) | L1 | L2 | L3>
  (per SPECIALIST_PREAMBLE.md)
- Not run: <level/command> - <reason>
- Accuracy note: <"routed to /accuracy" if ACCURACY-CRITICAL, else "n/a">
```

## Hard rules

1. Never mark a check passed unless it executed in this run and exited clean.
2. Never carry a result over from an earlier run or from memory.
3. A setup, collection, or import failure is `BLOCKED`, not `PASS`.
4. A `DOC/CONFIG-ONLY` classification must be justified against the full
   changed-file set (tracked + untracked), not assumed from the task description.
5. This skill does not modify the tree. No `Edit`, no `Write`, no staging, no commit.
6. Accuracy claims are out of scope here — `/verify` never states WER, CER, F1, or
   SCDR. Route accuracy-critical changes to `/accuracy`.
