---
name: talksense-security
description: >-
  Security specialist context for TalkSense AI. Use when working on authentication,
  authorization, secrets management, input validation, CORS, JWT ws_token handling
  (core/security.py), or production hardening — and when asked about the current
  security state. Records what is verified in source on branch dev, the security
  invariants, the pre-release checklist, and gaps that must NOT be fixed during
  documentation tasks.
---

# TalkSense AI — Security Specialist

Start with [`.agent/SPECIALIST_PREAMBLE.md`](../../../.agent/SPECIALIST_PREAMBLE.md)
(shared invariants, control docs, verification ladder).

**Full detail:** [`.agent/agents/security_agent.md`](../../../.agent/agents/security_agent.md)
— canonical "current security state" section (verified against the repo), invariants,
pre-release checklist, and the gaps table.

## When this applies

Auth, authz, secrets, input validation, CORS, JWT, HTTPS/WSS, dependency security, or
any question about what security controls are currently active.

## Current state — do not assume more than this

- REST endpoints are **unauthenticated**; there is no user-auth system, no
  `/auth/login|register|me`, no `get_current_user` dependency.
- The four WS subscription channels (`/ws/transcript|metrics|alerts|status`) **do**
  verify `ws_token` (`ws/subscriptions.py`), closing with `1008` on missing/invalid.
- `/ws/audio/{session_id}` does **not** verify the token.
- `JWT_SECRET_KEY` defaults to a per-process random value; CORS defaults to
  `http://localhost:5173`; HTTPS is not enforced by the app.

## Hard stops

- Do not implement REST authentication, auth middleware, or session-ownership checks
  during a documentation or unrelated task.
- Do not weaken the security invariants: stable `JWT_SECRET_KEY` in production,
  restricted CORS origins, parameterized SQL only, session WAV files never served
  unauthenticated, `password_hash` stores bcrypt only.
- Escalate before touching auth middleware, CORS config, or JWT create/verify logic.
