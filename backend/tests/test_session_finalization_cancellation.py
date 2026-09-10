"""
Lifecycle-correctness tests for SessionManager session finalization.

Focus: the detached-finalizer design in SessionManager.end() / _finalize().

  * end() is a thin shim that creates (or reuses) a per-session finalizer
    task registered in _flush_workers, then awaits it.
  * Caller cancellation propagates out of end() but does NOT cancel the
    detached finalizer, so the final flush, DB persistence, post-session AI
    scheduling and session removal still complete.
  * Concurrent end() callers reuse the same finalizer task.
  * A failed final flush leaves the session in place with _is_ending reset,
    so a later end() call can retry.
  * session.ws_audio is cleared once terminal status is committed.
  * stop_flusher() drains the detached finalizer before returning.

All synchronisation is done with asyncio.Event / task-state assertions —
no arbitrary sleeps, no polling-timeout changes.
"""

import asyncio
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

import ws.session_manager as sm
from core.config import get_settings
from ws.session_manager import SessionStatus, get_session_manager

pytestmark = pytest.mark.asyncio


# ── Fixtures ─────────────────────────────────────────────────────────────────


@pytest.fixture
async def sm_env():
    """
    Snapshot and restore the module-global flusher state, hand back a clean
    SessionManager, and install a real (non-None) _FLUSH_SEMAPHORE so the
    final-flush path is exercised.
    """
    saved_sema = sm._FLUSH_SEMAPHORE
    saved_task = sm._flush_task
    saved_workers = set(sm._flush_workers)

    manager = get_session_manager()
    saved_sessions = dict(manager._sessions)

    manager._sessions.clear()
    sm._flush_workers.clear()
    sm._FLUSH_SEMAPHORE = asyncio.Semaphore(1)
    sm._flush_task = None

    yield manager

    # Best-effort cleanup of any finalizer / pipeline tasks still pending.
    for task in list(sm._flush_workers):
        if not task.done():
            task.cancel()
    for task in list(sm._flush_workers):
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass

    manager._sessions.clear()
    manager._sessions.update(saved_sessions)
    sm._flush_workers.clear()
    sm._flush_workers.update(saved_workers)
    sm._FLUSH_SEMAPHORE = saved_sema
    sm._flush_task = saved_task


@pytest.fixture
def mock_db(monkeypatch):
    """Mock the DB layer used by _finalize Step 5 (status/audio-path persist)."""
    mock_crud = MagicMock()
    mock_crud.update_session_status = AsyncMock()
    mock_crud.update_session_audio_path = AsyncMock()
    mock_crud.get_session = AsyncMock(return_value=None)

    monkeypatch.setattr("db.crud", mock_crud, raising=False)
    if "db.crud" not in sys.modules:
        monkeypatch.setitem(sys.modules, "db.crud", mock_crud)

    monkeypatch.setattr(
        "db.database.AsyncSessionLocal",
        MagicMock(return_value=AsyncMock()),
        raising=False,
    )
    return mock_crud


@pytest.fixture
def post_ai_disabled(monkeypatch):
    monkeypatch.setattr(get_settings(), "enable_post_session_ai", False)


@pytest.fixture
def post_ai_enabled(monkeypatch):
    monkeypatch.setattr(get_settings(), "enable_post_session_ai", True)
    mock_run = AsyncMock()
    monkeypatch.setattr(
        "services.post_session_pipeline.run_post_session_pipeline",
        mock_run,
        raising=False,
    )
    return mock_run


# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_active_session(manager, mode: str = "meeting"):
    session = manager.create(mode)
    session.status = SessionStatus.ACTIVE
    return session


def _install_flush(monkeypatch, fn):
    monkeypatch.setattr("ws.session_manager._flush_session_final", fn, raising=True)


# ── 1. Normal end completes successfully ─────────────────────────────────────


async def test_normal_end_completes_and_removes_session(
    sm_env, mock_db, monkeypatch, post_ai_enabled
):
    manager = sm_env
    calls = []
    _install_flush(
        monkeypatch, AsyncMock(side_effect=lambda s: calls.append(s.session_id))
    )

    session = _make_active_session(manager)
    sid = session.session_id

    await manager.end(sid, SessionStatus.COMPLETED)

    assert calls == [sid], "final flush must run exactly once"
    assert manager.get(sid) is None, "completed session must be removed from memory"
    assert session._finalize_task is not None
    assert session._finalize_task.done()
    assert session._finalize_task.exception() is None
    assert session.speaker_attribution_status == "skipped"
    mock_db.update_session_status.assert_awaited_once()
    assert post_ai_enabled.call_count == 1, "post-session AI scheduled exactly once"


# ── 2. Caller cancellation does not cancel detached finalization ─────────────
# ── 3. Final DB flush/commit still occurs after caller cancellation ─────────


async def test_caller_cancellation_does_not_abort_finalizer(
    sm_env, mock_db, monkeypatch, post_ai_disabled
):
    manager = sm_env
    flush_started = asyncio.Event()
    release = asyncio.Event()
    committed = []

    async def parked_flush(session):
        flush_started.set()
        await release.wait()
        committed.append(session.session_id)

    _install_flush(monkeypatch, parked_flush)

    session = _make_active_session(manager)
    sid = session.session_id

    caller = asyncio.create_task(manager.end(sid, SessionStatus.COMPLETED))

    # Wait until the detached finalizer is parked inside the final flush.
    await flush_started.wait()
    finalizer = session._finalize_task
    assert finalizer is not None and not finalizer.done()

    # Cancel the caller while the finalizer is mid-flush.
    caller.cancel()
    with pytest.raises(asyncio.CancelledError):
        await caller

    # (3) The flush has NOT been lost — it is still pending, not yet committed.
    assert committed == []
    assert not finalizer.done(), "finalizer must survive caller cancellation"
    assert manager.get(sid) is not None, "session not removed until finalizer finishes"

    # Let the flush finish; the detached finalizer must run to completion.
    release.set()
    await finalizer

    assert committed == [sid], "final flush/commit completes after caller cancellation"
    assert manager.get(sid) is None, "session removed by the detached finalizer"
    assert finalizer.exception() is None


async def test_db_persist_runs_after_caller_cancellation(
    sm_env, mock_db, monkeypatch, post_ai_disabled
):
    """Step 5 (terminal-status / audio-path DB persistence) must still run when
    the caller was cancelled mid-finalization."""
    manager = sm_env
    flush_started = asyncio.Event()
    release = asyncio.Event()

    async def parked_flush(session):
        flush_started.set()
        await release.wait()

    _install_flush(monkeypatch, parked_flush)

    session = _make_active_session(manager)
    sid = session.session_id

    caller = asyncio.create_task(manager.end(sid, SessionStatus.COMPLETED))
    await flush_started.wait()
    finalizer = session._finalize_task

    caller.cancel()
    with pytest.raises(asyncio.CancelledError):
        await caller

    # DB persistence has not happened yet — the flush is still parked.
    mock_db.update_session_status.assert_not_awaited()

    release.set()
    await finalizer

    # The detached finalizer reached Step 5 and persisted terminal status.
    mock_db.update_session_status.assert_awaited_once()
    assert mock_db.update_session_status.await_args.args[2] == "completed"
    assert manager.get(sid) is None


# ── 4. Session removed after successful detached finalization ────────────────


async def test_session_removed_after_detached_finalization(
    sm_env, mock_db, monkeypatch, post_ai_disabled
):
    manager = sm_env
    _install_flush(monkeypatch, AsyncMock())

    session = _make_active_session(manager)
    sid = session.session_id
    assert sid in manager._sessions

    caller = asyncio.create_task(manager.end(sid, SessionStatus.COMPLETED))
    await caller

    assert sid not in manager._sessions
    assert manager.get(sid) is None


# ── 5. Concurrent end() calls do not duplicate finalization ─────────────────


async def test_concurrent_end_calls_reuse_single_finalizer(
    sm_env, mock_db, monkeypatch, post_ai_enabled
):
    manager = sm_env

    flush_calls = []
    gate = asyncio.Event()

    async def gated_flush(session):
        flush_calls.append(session.session_id)
        await gate.wait()

    _install_flush(monkeypatch, gated_flush)

    registered = []
    real_register = sm._register_flush_worker

    def spy_register(task):
        registered.append(task)
        real_register(task)

    monkeypatch.setattr("ws.session_manager._register_flush_worker", spy_register)

    session = _make_active_session(manager)
    sid = session.session_id

    callers = [
        asyncio.create_task(manager.end(sid, SessionStatus.COMPLETED)) for _ in range(4)
    ]
    # Give all four end() shims a turn to run through the create-or-reuse block.
    await asyncio.sleep(0)

    finalize_tasks = [t for t in registered if t.get_name().startswith("finalize-")]
    assert len(finalize_tasks) == 1, "exactly one finalizer task for the session"
    assert session._finalize_task is finalize_tasks[0]

    gate.set()
    await asyncio.gather(*callers)

    assert flush_calls == [sid], "final flush executed exactly once"
    mock_db.update_session_status.assert_awaited_once()
    assert post_ai_enabled.call_count == 1, "post-session AI scheduled exactly once"
    assert manager.get(sid) is None


# ── 6. Finalization is retryable after a flush failure ──────────────────────


async def test_finalization_retryable_after_flush_failure(
    sm_env, mock_db, monkeypatch, post_ai_disabled
):
    manager = sm_env
    attempts = {"n": 0}

    async def flaky_flush(session):
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise RuntimeError("simulated final-flush DB failure")

    _install_flush(monkeypatch, flaky_flush)

    session = _make_active_session(manager)
    sid = session.session_id

    # First attempt: the final-flush failure must propagate to the caller and
    # must NOT remove the session or leave _is_ending latched.
    with pytest.raises(RuntimeError, match="simulated final-flush DB failure"):
        await manager.end(sid, SessionStatus.COMPLETED)

    assert (
        manager.get(sid) is session
    ), "failed finalization must not remove the session"
    assert session._is_ending is False, "_is_ending reset so a retry can proceed"
    assert session._finalize_task.done()

    # Second attempt: a fresh finalizer runs and completes.
    await manager.end(sid, SessionStatus.COMPLETED)

    assert attempts["n"] == 2
    assert manager.get(sid) is None, "retry finalizes and removes the session"


# ── 7. ws_audio is cleared after terminal finalization ─────────────────────


async def test_ws_audio_cleared_after_finalization(
    sm_env, mock_db, monkeypatch, post_ai_disabled
):
    manager = sm_env
    _install_flush(monkeypatch, AsyncMock())

    session = _make_active_session(manager)
    session.ws_audio = MagicMock(name="fake-audio-socket")
    sid = session.session_id

    await manager.end(sid, SessionStatus.COMPLETED, from_audio_handler=True)

    assert session.ws_audio is None, "audio socket reference cleared on finalization"
    assert manager.get(sid) is None


# ── 8. REST/shutdown can finalize a session after ws_audio has been cleared ─


async def test_rest_path_finalizes_when_ws_audio_already_cleared(
    sm_env, mock_db, monkeypatch, post_ai_disabled
):
    manager = sm_env
    flush_calls = []
    _install_flush(
        monkeypatch,
        AsyncMock(side_effect=lambda s: flush_calls.append(s.session_id)),
    )

    session = _make_active_session(manager)
    session.ws_audio = None  # WebSocket already gone
    sid = session.session_id

    # from_audio_handler=False → REST DELETE / shutdown path.  With ws_audio
    # cleared this must NOT take the Step 0 delegation branch; it must finalize.
    await manager.end(sid, SessionStatus.COMPLETED, from_audio_handler=False)

    assert flush_calls == [sid], "finalizer ran (delegation path was not taken)"
    assert manager.get(sid) is None


# ── 9. Shutdown drains the detached finalizer ──────────────────────────────


async def test_stop_flusher_drains_detached_finalizer(
    sm_env, mock_db, monkeypatch, post_ai_disabled
):
    manager = sm_env
    flush_started = asyncio.Event()
    release = asyncio.Event()
    finished = []

    async def parked_flush(session):
        flush_started.set()
        await release.wait()
        finished.append(session.session_id)

    _install_flush(monkeypatch, parked_flush)

    session = _make_active_session(manager)
    sid = session.session_id

    caller = asyncio.create_task(manager.end(sid, SessionStatus.COMPLETED))
    await flush_started.wait()

    finalizer = session._finalize_task
    assert finalizer in sm._flush_workers
    assert not finalizer.done()

    # Release the flush on the next loop tick so stop_flusher()'s drain can
    # observe the finalizer complete rather than time out.
    async def _release_soon():
        release.set()

    releaser = asyncio.create_task(_release_soon())

    await sm.stop_flusher()

    assert finalizer.done(), "stop_flusher must not return until the finalizer drains"
    assert finished == [sid]
    assert manager.get(sid) is None

    await caller
    await releaser


# ── 10. Shutdown can finalize leftover active sessions ─────────────────────


async def test_end_all_active_sessions_finalizes_leftovers(
    sm_env, mock_db, monkeypatch, post_ai_disabled
):
    manager = sm_env
    flushed = set()
    _install_flush(
        monkeypatch,
        AsyncMock(side_effect=lambda s: flushed.add(s.session_id)),
    )

    s1 = _make_active_session(manager)
    s2 = _make_active_session(manager)

    await manager.end_all_active_sessions()

    assert manager.get(s1.session_id) is None
    assert manager.get(s2.session_id) is None
    assert flushed == {s1.session_id, s2.session_id}

    assert mock_db.update_session_status.await_count == 2
    persisted_status = {
        call.args[2] for call in mock_db.update_session_status.await_args_list
    }
    assert persisted_status == {"interrupted"}, "shutdown persists INTERRUPTED status"
