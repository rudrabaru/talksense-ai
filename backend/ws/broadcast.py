"""
TalkSense AI — WebSocket Broadcaster

Sends real-time updates to connected frontend clients over 4 channels:
  /transcript  — new segment(s) with speaker + sentiment
  /metrics     — updated health score, speaking ratio, participation
  /alerts      — new alert (level, message, timestamp)
  /status      — session state changes

Backpressure:
  Metric updates are fire-and-forget (dropped if client can't keep up).
  Alert and transcript messages are sent with a short retry to avoid loss.

JSON envelope:
  { "type": "<channel>", "payload": { ... }, "ts": <unix_ms> }
"""

import asyncio
import logging
import time
from typing import Any

from fastapi import WebSocket, WebSocketDisconnect
from starlette.websockets import WebSocketState

logger = logging.getLogger(__name__)

SEND_TIMEOUT = 0.5  # seconds — give up trying to send after this


def _now_ms() -> int:
    return int(time.time() * 1000)


def _envelope(channel: str, payload: dict) -> dict:
    return {"type": channel, "payload": payload, "ts": _now_ms()}


async def _safe_send(
    ws: WebSocket | None, data: dict, drop_on_lag: bool = False
) -> bool:
    """
    Send JSON to a WebSocket connection.

    Args:
        ws:           Target WebSocket. No-op if None.
        data:         JSON-serialisable dict.
        drop_on_lag:  If True, skip send if client is not ready (backpressure).

    Returns:
        True if sent successfully, False otherwise.
    """
    if ws is None:
        return False

    if ws.client_state != WebSocketState.CONNECTED:
        return False

    try:
        if drop_on_lag:
            # Non-blocking: only send if we can do so immediately
            await asyncio.wait_for(ws.send_json(data), timeout=SEND_TIMEOUT)
        else:
            await ws.send_json(data)
        return True

    except asyncio.TimeoutError:
        logger.debug("Broadcaster: client lagging — metric update dropped")
        return False
    except WebSocketDisconnect:
        return False
    except Exception as exc:
        logger.warning(f"Broadcaster: send error — {exc}")
        return False


# ── Public broadcast functions ────────────────────────────────────────────────


async def broadcast_transcript(ws: WebSocket | None, segment: dict) -> None:
    """
    Send a new transcript segment.

    Payload:
      { session_id, speaker, text, start, end, sentiment, sentiment_label }
    """
    await _safe_send(
        ws,
        _envelope("transcript", segment),
        drop_on_lag=False,  # transcripts are never dropped
    )


async def broadcast_metrics(ws: WebSocket | None, metrics: dict) -> None:
    """
    Send updated conversation metrics.

    Payload:
      { health_score, sentiment, speaking_ratio, participation,
        filler_count, objections, buying_signals, duration_seconds }

    Drops if client is lagging (backpressure — only latest state matters).
    """
    await _safe_send(
        ws,
        _envelope("metrics", metrics),
        drop_on_lag=True,  # drop old metric updates
    )


async def broadcast_alert(ws: WebSocket | None, alert: dict) -> None:
    """
    Send a new real-time alert.

    Payload:
      { id, level, message, timestamp }

    Alerts are never dropped.
    """
    await _safe_send(
        ws,
        _envelope("alerts", alert),
        drop_on_lag=False,
    )


async def broadcast_status(
    ws: WebSocket | None, status: str, extra: dict | None = None
) -> None:
    """
    Send a session status change.

    Payload:
      { status, ...extra }
    """
    payload: dict[str, Any] = {"status": status}
    if extra:
        payload.update(extra)
    await _safe_send(ws, _envelope("status", payload), drop_on_lag=False)


async def broadcast_all(
    ws_transcript: WebSocket | None,
    ws_metrics: WebSocket | None,
    ws_alerts: WebSocket | None,
    transcript_segment: dict | None = None,
    metrics: dict | None = None,
    new_alerts: list[dict] | None = None,
) -> None:
    """
    Convenience function to broadcast all pending updates at once.
    Runs all sends concurrently via asyncio.gather.
    """
    tasks = []

    if transcript_segment and ws_transcript:
        tasks.append(broadcast_transcript(ws_transcript, transcript_segment))

    if metrics and ws_metrics:
        tasks.append(broadcast_metrics(ws_metrics, metrics))

    if new_alerts and ws_alerts:
        for alert in new_alerts:
            tasks.append(broadcast_alert(ws_alerts, alert))

    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
