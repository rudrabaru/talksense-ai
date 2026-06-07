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
  4. Cleans up on disconnect

The actual push is done by broadcast.py, triggered by audio_handler.py.
"""
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from ws.session_manager import get_session_manager

logger = logging.getLogger(__name__)

router = APIRouter()


@router.websocket("/ws/transcript/{session_id}")
async def transcript_ws(websocket: WebSocket, session_id: str) -> None:
    """Subscribe to live transcript segments for a session."""
    manager = get_session_manager()
    session = manager.get(session_id)
    if session is None:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    async with session.lock:
        session.ws_transcript = websocket

    logger.info(f"Session {session_id[:8]}…: /transcript subscriber connected")
    try:
        while True:
            # Keep-alive: accept and discard any incoming messages
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with session.lock:
            session.ws_transcript = None
        logger.info(f"Session {session_id[:8]}…: /transcript subscriber disconnected")


@router.websocket("/ws/metrics/{session_id}")
async def metrics_ws(websocket: WebSocket, session_id: str) -> None:
    """Subscribe to live conversation metrics for a session."""
    manager = get_session_manager()
    session = manager.get(session_id)
    if session is None:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    async with session.lock:
        session.ws_metrics = websocket

    logger.info(f"Session {session_id[:8]}…: /metrics subscriber connected")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with session.lock:
            session.ws_metrics = None
        logger.info(f"Session {session_id[:8]}…: /metrics subscriber disconnected")


@router.websocket("/ws/alerts/{session_id}")
async def alerts_ws(websocket: WebSocket, session_id: str) -> None:
    """Subscribe to real-time alerts for a session."""
    manager = get_session_manager()
    session = manager.get(session_id)
    if session is None:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    async with session.lock:
        session.ws_alerts = websocket

    logger.info(f"Session {session_id[:8]}…: /alerts subscriber connected")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with session.lock:
            session.ws_alerts = None
        logger.info(f"Session {session_id[:8]}…: /alerts subscriber disconnected")


@router.websocket("/ws/status/{session_id}")
async def status_ws(websocket: WebSocket, session_id: str) -> None:
    """Subscribe to session lifecycle status changes."""
    manager = get_session_manager()
    session = manager.get(session_id)
    if session is None:
        await websocket.close(code=4004, reason="Session not found")
        return

    await websocket.accept()
    async with session.lock:
        session.ws_status = websocket

    logger.info(f"Session {session_id[:8]}…: /status subscriber connected")
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        async with session.lock:
            session.ws_status = None
        logger.info(f"Session {session_id[:8]}…: /status subscriber disconnected")
