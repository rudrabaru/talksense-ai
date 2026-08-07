"""
TalkSense AI — WebSocket Subscription Endpoints

The frontend connects to 4 read-only WebSocket channels per session.
These are separate from the audio input stream.

  /ws/transcript/{session_id}  — receives transcript push events
  /ws/metrics/{session_id}     — receives metrics push events
  /ws/alerts/{session_id}      — receives alert push events
  /ws/status/{session_id}      — receives session status events

Each endpoint:
  1. Validates session exists
  2. Registers the WebSocket on the SessionState
  3. Waits (keeps connection open)
  4. Cleans up on disconnect — ONLY if the closing WebSocket is still
     the currently registered one.  Stale closes from a previously
     superseded connection are ignored to prevent the orphan-subscriber
     race condition described below.

Race condition fixed (2026-06-11):
  When React StrictMode double-mounts (or the user rapidly reconnects):
    t0: ws1 connects → session.ws_<ch> = ws1
    t1: ws2 connects → session.ws_<ch> = ws2   (ws1 is superseded)
    t2: ws1's async close event fires
    t3: without the guard, finally block runs → session.ws_<ch> = None
        ws2 is now orphaned; broadcasts stop; dashboard freezes.

  Fix: in every finally block, compare the closing websocket instance to
  the currently registered reference.  Clear only on identity match:

    if session.ws_<ch> is websocket:
        session.ws_<ch> = None
        logger.info("…: reference cleared")
    else:
        logger.info("…: stale close ignored — active reference preserved")

The actual push is done by broadcast.py, triggered by audio_handler.py.
"""

import logging
import uuid
import time as _time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ws.session_manager import get_session_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/transcript/{session_id}")
async def transcript_ws(websocket: WebSocket, session_id: uuid.UUID) -> None:
    """Subscribe to live transcript segments for a session."""
    session_id = str(session_id)
    manager = get_session_manager()
    session = manager.get(session_id)
    if session is None:
        await websocket.accept()
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()

    token = websocket.query_params.get("token")
    from core.security import verify_ws_token
    if not verify_ws_token(token, session_id):
        logger.warning(f"Unauthorized WS connection attempt for session {session_id}")
        await websocket.close(code=1008, reason="Unauthorized")
        return
    async with session.lock:
        session.ws_transcript = websocket

    logger.info(
        f"Session {session_id[:8]}…: /transcript subscriber accepted "
        f"(ws_id={id(websocket)})"
    )
    try:
        while True:
            # Keep-alive: accept and discard any incoming messages
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError) as exc:
        if isinstance(exc, RuntimeError) and not (
            "Cannot call" in str(exc) and "disconnect" in str(exc)
        ):
            raise exc
    finally:
        async with session.lock:
            if session.ws_transcript is websocket:
                session.ws_transcript = None
                logger.info(
                    f"Session {session_id[:8]}…: /transcript subscriber closed "
                    f"(ws_id={id(websocket)}) — reference cleared"
                )
            else:
                logger.info(
                    f"Session {session_id[:8]}…: /transcript subscriber closed "
                    f"(ws_id={id(websocket)}) — stale close, active reference preserved "  # noqa: E501
                    f"(active_ws_id={id(session.ws_transcript)})"
                )


@router.websocket("/ws/metrics/{session_id}")
async def metrics_ws(websocket: WebSocket, session_id: uuid.UUID) -> None:
    """Subscribe to live conversation metrics for a session."""
    session_id = str(session_id)
    manager = get_session_manager()
    session = manager.get(session_id)
    if session is None:
        await websocket.accept()
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()

    token = websocket.query_params.get("token")
    from core.security import verify_ws_token
    if not verify_ws_token(token, session_id):
        logger.warning(f"Unauthorized WS connection attempt for session {session_id}")
        await websocket.close(code=1008, reason="Unauthorized")
        return
    async with session.lock:
        session.ws_metrics = websocket

    logger.info(
        f"Session {session_id[:8]}…: /metrics subscriber accepted "
        f"(ws_id={id(websocket)})"
    )
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError) as exc:
        if isinstance(exc, RuntimeError) and not (
            "Cannot call" in str(exc) and "disconnect" in str(exc)
        ):
            raise exc
    finally:
        async with session.lock:
            if session.ws_metrics is websocket:
                session.ws_metrics = None
                logger.info(
                    f"Session {session_id[:8]}…: /metrics subscriber closed "
                    f"(ws_id={id(websocket)}) — reference cleared"
                )
            else:
                logger.info(
                    f"Session {session_id[:8]}…: /metrics subscriber closed "
                    f"(ws_id={id(websocket)}) — stale close, active reference preserved "  # noqa: E501
                    f"(active_ws_id={id(session.ws_metrics)})"
                )


@router.websocket("/ws/alerts/{session_id}")
async def alerts_ws(websocket: WebSocket, session_id: uuid.UUID) -> None:
    """Subscribe to real-time alerts for a session."""
    session_id = str(session_id)
    manager = get_session_manager()
    session = manager.get(session_id)
    if session is None:
        await websocket.accept()
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()

    token = websocket.query_params.get("token")
    from core.security import verify_ws_token
    if not verify_ws_token(token, session_id):
        logger.warning(f"Unauthorized WS connection attempt for session {session_id}")
        await websocket.close(code=1008, reason="Unauthorized")
        return
    async with session.lock:
        session.ws_alerts = websocket

    logger.info(
        f"Session {session_id[:8]}…: /alerts subscriber accepted "
        f"(ws_id={id(websocket)})"
    )
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError) as exc:
        if isinstance(exc, RuntimeError) and not (
            "Cannot call" in str(exc) and "disconnect" in str(exc)
        ):
            raise exc
    finally:
        async with session.lock:
            if session.ws_alerts is websocket:
                session.ws_alerts = None
                logger.info(
                    f"Session {session_id[:8]}…: /alerts subscriber closed "
                    f"(ws_id={id(websocket)}) — reference cleared"
                )
            else:
                logger.info(
                    f"Session {session_id[:8]}…: /alerts subscriber closed "
                    f"(ws_id={id(websocket)}) — stale close, active reference preserved "  # noqa: E501
                    f"(active_ws_id={id(session.ws_alerts)})"
                )


@router.websocket("/ws/status/{session_id}")
async def status_ws(websocket: WebSocket, session_id: uuid.UUID) -> None:
    """Subscribe to session lifecycle status changes."""
    session_id = str(session_id)
    manager = get_session_manager()
    session = manager.get(session_id)
    if session is None:
        await websocket.accept()
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()

    token = websocket.query_params.get("token")
    from core.security import verify_ws_token
    if not verify_ws_token(token, session_id):
        logger.warning(f"Unauthorized WS connection attempt for session {session_id}")
        await websocket.close(code=1008, reason="Unauthorized")
        return
    async with session.lock:
        session.ws_status = websocket

    logger.info(
        f"Session {session_id[:8]}…: /status subscriber accepted "
        f"(ws_id={id(websocket)})"
    )
    logger.warning(
        "[DEBUG-LIFECYCLE] STATUS WS ASSIGNED: session=%s ws_id=%s at t=%.4f",
        session_id[:8], id(websocket), _time.monotonic(),
    )
    try:
        while True:
            await websocket.receive_text()
    except (WebSocketDisconnect, RuntimeError) as exc:
        if isinstance(exc, RuntimeError) and not (
            "Cannot call" in str(exc) and "disconnect" in str(exc)
        ):
            raise exc
    finally:
        _t_close = _time.monotonic()
        logger.warning(
            "[DEBUG-LIFECYCLE] STATUS WS FINALLY entered: session=%s ws_id=%s at t=%.4f",
            session_id[:8], id(websocket), _t_close,
        )
        async with session.lock:
            if session.ws_status is websocket:
                session.ws_status = None
                logger.warning(
                    "[DEBUG-LIFECYCLE] STATUS WS CLEARED (ws_status=None): session=%s ws_id=%s at t=%.4f",
                    session_id[:8], id(websocket), _time.monotonic(),
                )
                logger.info(
                    f"Session {session_id[:8]}…: /status subscriber closed "
                    f"(ws_id={id(websocket)}) — reference cleared"
                )
            else:
                logger.warning(
                    "[DEBUG-LIFECYCLE] STATUS WS stale close — active ref preserved: session=%s closing_ws_id=%s active_ws_id=%s at t=%.4f",
                    session_id[:8], id(websocket),
                    id(session.ws_status) if session.ws_status is not None else "None",
                    _time.monotonic(),
                )
                logger.info(
                    f"Session {session_id[:8]}…: /status subscriber closed "
                    f"(ws_id={id(websocket)}) — stale close, active reference preserved "
                    f"(active_ws_id={id(session.ws_status)})"
                )
