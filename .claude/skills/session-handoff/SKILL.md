---
name: session-handoff
description: >-
  TalkSense AI end-of-session handoff. Use when the user says "session handoff",
  "wrap up session", "hand off", "handoff summary", "summarize before I clear", or
  is about to /clear. Produces a chat-only context-handoff artifact for a fresh
  Claude Code session: repository state, completed and outstanding Pn.n work,
  decisions and constraints, files touched, verification evidence with L1-L5
  ladder level and CI status, and the exact next action.
---

# Session Handoff — TalkSense AI

Produce a repeatable end-of-session summary so the user can `/clear` and start a
fresh agent without losing continuity. The next agent must be able to pick up by
reading this summary alone.

This is a **context-handoff artifact**, not a stakeholder status report. The
audience is a future instance of you working in a clean context.

Related project context (do not re-read as a set; consult only if a section needs
it): [`CLAUDE.md`](../../../CLAUDE.md) Tier-0 rules,
[`.agent/DEVELOPMENT_RULES.md`](../../../.agent/DEVELOPMENT_RULES.md) §1 plan gate
and §3 review gate, [`.agent/SPECIALIST_PREAMBLE.md`](../../../.agent/SPECIALIST_PREAMBLE.md)
verification ladder.

## When to invoke

User says: "session handoff", "wrap up session", "hand off", "handoff summary",
"let's wrap up", "summarize before I clear", or any near-equivalent. Also invoke
proactively if the user says they are about to `/clear` without having run it yet.

## How to produce the summary

1. **Review the full conversation**, not just the last few turns. Handoffs miss
   things when they only summarize recent context.
2. **Pull state from these sources (in order):**
   - Plan files referenced this session (your Claude Code plans directory, e.g.
     `~/.claude/plans/`, if a plan was mentioned).
   - TodoWrite state — any in-progress or pending tasks.
   - Background processes you started with `run_in_background` — shell IDs are
     load-bearing for the next agent.
   - Files created or modified this session — you know what you touched; do not
     grep to re-discover.
   - Any Claude Code project-memory files you wrote or updated this session —
     reference them by name, not by an assumed filesystem path.
   - Unresolved questions — things you asked the user that never got a clear
     answer, or things the user asked that got deflected.
3. **Limited repository audit is allowed and required.** Run exactly these three
   read-only commands to capture ground truth for the "Repository state" section,
   and nothing broader (no wide `Glob`/`grep` sweeps, no history spelunking):
   - `git -C "<repo>" log --oneline -5`
   - `git -C "<repo>" status --short`
   - `git -C "<repo>" rev-list --left-right --count origin/dev...dev`
   Never write a commit SHA, version, flag, or branch name from memory — take it
   from command output.
4. **Produce the output in chat.** Do not write a file and do not update memory
   from this skill. If the user separately asks to persist the handoff (the repo
   keeps forensic `SESSION_HANDOFF_*.md` docs at root), that is a distinct action
   they must request explicitly.

## Output template — use exactly this structure, every time

```
# Session Handoff — <one-line title of what this session was about>

## Where it started
<2-3 sentences: what the user asked for, the milestone ID if any (e.g. P1.2),
key framing or constraints that emerged>

## Repository state
- Branch: <name>  |  HEAD: <sha> <subject line>  (from git log, not memory)
- Unpushed: <N> commit(s) ahead of origin/dev  (from rev-list --count)
- `git status --short`: <exact expected output>
- Pre-existing, NOT this session's work (leave untouched): <files/dirs> — or "none"

## Decisions locked + what shipped
- <decision or change> — <why, and where it lives (absolute path if a file)>
- Review gate (DEVELOPMENT_RULES.md §3): <in-session peer review done? / pending>
- ...

## Outstanding work
- <Pn.n or task> — <what remains, blocking dependency if any>
- ...

## Decisions & constraints carried forward
- Plan-before-edit gate (DEVELOPMENT_RULES.md §1): <relevant? / satisfied how>
- Accuracy is non-negotiable — do NOT start ASR/Whisper/VAD/streaming/accuracy
  work unless the user explicitly authorized it this session.
- `TARGET_DURATION_MS = 2000` (backend/audio/buffer.py) is the CURRENT value, not
  a permanent lock. If an approved ASR/streaming design changes it, the
  implementation plus the approved design become the source of truth and the
  documentation must follow.
- <any other constraint that shaped this session>

## Key files for next session
- `<absolute path>` — <why the next agent should read this first>
- Plan file: `<path>` (if a plan drove the session) — read before anything else
- Project-memory files touched this session: <names> (if any)

## Running state
- Background processes: <shell IDs + what they are + how to kill> — or "none"
- Dev servers / ports: <url + port> — or "none"
- Open worktrees / branches: <paths> — or "none"

## Verification — evidence and how to confirm
- <change> — ladder level reached: <L1 static | L2 focused | L3 regression |
  L4 accuracy benchmark | L5 architecture/release>; evidence tag where an AI
  result is claimed: <FUNCTIONAL | ACCURACY VERIFIED (state metric + before/after)
  | NOT VERIFIED>
- CI: Backend <PASS/FAIL/unknown>  |  Integration <...>  |  Frontend <...>
- Re-run commands (from CLAUDE.md "Verification commands"):
  `<command>` — <expected outcome>

## Deferred + open questions
- Deferred: <item> — <why pushed to later>
- Open: <question needing the user's input> — <context>

## Pick up here
<1-2 sentences: the single most likely next concrete action for a fresh agent,
with the exact command or file if known>
```

## Hard rules

1. **Chat output only.** Never write the handoff to a file and never update memory
   from this skill.
2. **Never invent state.** If a section has nothing to report, write "none" — do
   not omit the section. Structure stability is the whole point.
3. **Absolute paths always.** The next agent may have a different working
   directory. Repo-relative paths are acceptable only inside `git status` output
   quoted verbatim.
4. **SHAs, versions, flags, branch names come from command output, never memory.**
5. **If a plan file drove the session, name it first** in "Key files" so the next
   agent reads it before anything else.
6. **Never present ASR / Whisper / VAD / streaming / accuracy-critical work as the
   next action** unless the user explicitly authorized it this session. The
   accuracy-critical surface is `backend/audio/`, `ws/audio_handler.py`, the
   locked `context_analyzer.py` functions, `backend/benchmark_dataset/`, and any
   ground truth.
7. **Never state an accuracy result without ground-truth evidence.** Use the
   evidence tags `FUNCTIONAL`, `ACCURACY VERIFIED` (with metric and before/after),
   or `NOT VERIFIED`. Any change that can move WER, diarization, sentiment, or a
   metric formula must cite L4.
8. **Record the review gate.** DEVELOPMENT_RULES.md §3 requires one peer review
   before a `dev` merge; state whether it happened in-session or is still pending.
9. **Background process IDs are critical.** If you started any `run_in_background`
   shells, their IDs must appear in "Running state" with the kill command — the
   next agent cannot find them otherwise.
10. **No emojis, no em-dashes in prose beyond the template's, no hype, no "great
    job" summaries.** Terse and concrete: paths, commands, SHAs, decisions. Match
    the tone of a seasoned engineer handing off at end-of-shift.

## Anti-patterns — do not do these

- Summarizing the last 3 turns and calling it a handoff.
- Listing files by bare relative path outside quoted command output.
- Writing a SHA or version "from memory" instead of from `git log`.
- Skipping "Running state" or "Repository state" because "nothing changed" — write
  the explicit expected output instead.
- Writing the summary to a file or to project memory. Chat-only by design unless
  the user explicitly asks for a `SESSION_HANDOFF_*.md`.
- Adding a "what went well / what went poorly" retrospective. This is not a retro.
- Recommending a slate of next steps beyond the single "Pick up here" action. The
  next agent decides; you just hand off.
- Broad filesystem or history auditing beyond the three allowed git commands.
