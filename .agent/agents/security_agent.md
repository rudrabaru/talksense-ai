# Security Agent Specialist

## Authoritative References — Read These First

- `.agent/ARCHITECTURE.md` — system overview
- `.agent/API_CONTRACT.md` — endpoint list; all REST and WS endpoints
- `.agent/RELEASE_CHECKLIST.md` — production security gates
- `.agent/DEVELOPMENT_RULES.md` — architecture compliance rules

---

## Scope of Responsibility

The security agent owns authentication, authorization, secrets management, input validation, CORS policy, and production hardening.

**Does NOT own:**
- Application business logic → Backend Agent
- Database schema → Database Agent
- Frontend implementation → Frontend Agent

---

## CURRENT SECURITY STATE — Verified Against Repository

> Read this section carefully before assuming any security control is active.

### Authentication

**Status: PARTIALLY IMPLEMENTED — NOT ENFORCED**

What exists:
- `core/security.py` — contains `create_ws_token(session_id)` and `verify_ws_token(token, session_id)`.
- `POST /sessions` calls `create_ws_token()` and returns `ws_token` in the response body.
- JWT library (`python-jose`) is installed.

What does NOT exist:
- No user login endpoint (`POST /auth/login`) — listed in `main.py` docstring but NOT implemented as a route handler.
- No user registration endpoint (`POST /auth/register`) — same situation.
- No `GET /auth/me` endpoint.
- No `get_current_user` dependency.
- No `Depends(get_current_user)` on any REST route.
- `verify_ws_token()` exists in `core/security.py` but is **never called** in `ws/subscriptions.py` or anywhere else in the live request path.

**Practical result:** All REST endpoints and all WebSocket channels are currently **unauthenticated**. The `ws_token` is generated and returned but never verified.

This is a known gap. Do NOT implement authentication during a documentation task. Do NOT silently assume it is active.

---

### Authorization

**Status: NOT IMPLEMENTED**

No session ownership checks exist. Any client that knows a `session_id` can connect to its WebSocket channels or query its data.

---

### Rate Limiting

**Status: NOT IMPLEMENTED**

`requirements.txt` does not include `slowapi` or equivalent. No rate-limiting middleware is present in `main.py`.

---

### Input Validation

**Status: PARTIALLY IMPLEMENTED — via Pydantic**

- REST request bodies are validated by Pydantic models in `main.py` (e.g., `SessionCreateRequest`).
- Session mode is normalized and validated at the API boundary.
- SQL injection is mitigated by SQLAlchemy's parameterized queries — direct SQL string construction is not used.
- WebSocket binary PCM frames are not validated for content beyond being `bytes`. Malformed non-PCM binary data is passed to the VAD/buffer.
- `inject:` text command on the audio WebSocket is parsed by string prefix — any text starting with `inject:` is accepted without access control.

---

### CORS

**Status: IMPLEMENTED — misconfigured for production**

- `CORSMiddleware` is active in `main.py`.
- Default `cors_origins` = `"http://localhost:5173"`.
- Before any production deployment, `CORS_ORIGINS` env var must be set to the actual production frontend URL.
- Current config allows `allow_methods=["*"]` and `allow_headers=["*"]` — acceptable for development, review before production.

---

### Secrets Management

**Status: PARTIALLY IMPLEMENTED**

- `JWT_SECRET_KEY` defaults to `secrets.token_hex(32)` auto-generated at process start. In production, this invalidates all tokens on every restart. Must be set as a stable environment variable.
- `GEMINI_API_KEY` loaded from environment via `core/config.py`.
- `DATABASE_URL` loaded from environment. The default in `config.py` embeds `password` — ensure this is overridden before production.
- No secrets appear hardcoded in application source files (verified: no API key literals found).
- `.env` files are in `.gitignore` — do not commit secrets.

---

### HTTPS / WSS

**Status: NOT ENFORCED by the application**

The FastAPI application itself does not enforce HTTPS. This must be enforced at the reverse proxy / gateway layer (nginx, Caddy, etc.) before any production deployment. Without this:
- PCM audio streams transit unencrypted.
- JWT tokens transit unencrypted.

---

### Dependency Security

- `frontend-ci.yml` runs `npm audit --audit-level=high` (with `|| true` — warns, does not block build).
- No automated Python dependency audit is configured in CI.
- The `google-genai` package required by `test_llm_engine.py` is not in `requirements.txt` — this is an installation consistency gap, not a security issue.

---

## Security Invariants

These must not be weakened:

1. `JWT_SECRET_KEY` must be a stable, non-default value in production.
2. CORS origins must be restricted to the production frontend domain before deployment.
3. SQLAlchemy parameterized queries must be preserved — no raw SQL string formatting.
4. Session WAV files stored at `backend/session_audio/` must not be served over unauthenticated endpoints.
5. `password_hash` column in `users` table must store only bcrypt hashes — never plaintext passwords (the login system is not yet built, but the column design must be respected when it is).

---

## Pre-Release Security Checklist

- [ ] `JWT_SECRET_KEY` set as stable env var (not auto-generated)
- [ ] `CORS_ORIGINS` set to production frontend URL (not `localhost`)
- [ ] HTTPS enforced at reverse proxy for all HTTP and WS traffic
- [ ] `ENABLE_POST_SESSION_AI` and `GEMINI_API_KEY` set or disabled intentionally
- [ ] `DATABASE_URL` uses a strong password (not the default)
- [ ] Session WAV file directory is not publicly accessible
- [ ] `npm audit --audit-level=high` reviewed for critical issues
- [ ] No secrets present in committed source files

---

## Security Gaps Requiring Future Work (Do NOT implement during documentation tasks)

| Gap | Severity | Status |
|-----|----------|--------|
| `verify_ws_token()` not called on WS subscribe | High | NOT IMPLEMENTED |
| No user auth system (login/register) | High | NOT IMPLEMENTED |
| No session ownership check on REST endpoints | High | NOT IMPLEMENTED |
| No rate limiting on any endpoint | Medium | NOT IMPLEMENTED |
| `inject:` WS command has no access control | Medium | NOT IMPLEMENTED |
| Python dependency audit not in CI | Low | NOT IMPLEMENTED |

---

## Escalation Conditions

Escalate to team review before making changes that:

- Add or modify authentication middleware
- Change CORS configuration
- Modify JWT token generation or verification logic
- Add new endpoints that expose session data or audio files
- Introduce new environment variables containing secrets
