"""
TalkSense AI — WebSocket Audio Handler

Handles the real-time audio pipeline for a session:

  Browser Mic → WebSocket → VAD → AudioBuffer → Whisper → Pyannote
                                                         ↓
                                              ConversationEngine
                                                         ↓
                             broadcast_transcript + broadcast_metrics + broadcast_alert

Endpoint: GET /ws/audio/{session_id}

Audio contract enforced here:
  Binary message must be PCM, 16kHz, mono, 16-bit.
  Text messages are control commands: "end", "ping".

The endpoint validates session existence and status before accepting
binary frames. Invalid sessions are rejected with a close code 4004.
"""
import asyncio
import logging
import time

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from audio.buffer import AudioBuffer
from audio.diarizer import get_diarizer
from audio.transcriber import get_transcriber
from audio.vad import get_vad
from services.nlp_engine import get_nlp_engine
from ws.broadcast import broadcast_all, broadcast_status, broadcast_transcript
from ws.session_manager import SessionStatus, get_session_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# Maximum chunk size to accept (5 seconds of PCM = 160,000 bytes)
MAX_CHUNK_BYTES = 16_000 * 2 * 5


@router.websocket("/ws/audio/{session_id}")
async def audio_stream(websocket: WebSocket, session_id: str) -> None:
    """
    Accepts a binary stream of PCM audio chunks from the browser.

    Each binary message is one 100–250ms PCM chunk.
    Text messages:
      "end"  — client signals end of session
      "ping" — keep-alive, responds with "pong"
    """
    manager = get_session_manager()
    vad = get_vad()
    transcriber = get_transcriber()
    diarizer = get_diarizer()

    # ── Validate session ──────────────────────────────────────────────────────
    session = manager.get(session_id)
    if session is None:
        logger.warning(f"Audio WS: session {session_id[:8]}… not found — rejecting")
        await websocket.accept()
        await websocket.close(code=4004, reason="Session not found")
        return

    # Reject connections to already-terminated sessions
    terminal = {SessionStatus.COMPLETED, SessionStatus.FAILED,
                SessionStatus.INTERRUPTED, SessionStatus.EXPIRED}
    if session.status in terminal:
        logger.warning(
            f"Audio WS: session {session_id[:8]}… is {session.status.value} — rejecting"
        )
        await websocket.accept()
        await websocket.close(code=4009, reason="Session has ended")
        return

    await websocket.accept()
    logger.info(f"Session {session_id[:8]}…: audio WebSocket connected")

    async with session.lock:
        session.ws_audio = websocket
        session.status = SessionStatus.ACTIVE

    await broadcast_status(session.ws_status, "active")

    # ── Main receive loop ─────────────────────────────────────────────────────
    try:
        while True:
            message = await websocket.receive()

            if message["type"] == "websocket.disconnect":
                raise WebSocketDisconnect(code=message.get("code", 1000))

            # Text control message
            if message.get("text"):
                text = message["text"].strip()
                text_lower = text.lower()
                if text_lower == "end":
                    logger.info(f"Session {session_id[:8]}…: client sent 'end'")
                    break
                elif text_lower == "ping":
                    await websocket.send_text("pong")
                elif text_lower.startswith("inject:"):
                    # format: inject:Speaker Name|phrase text
                    parts = text[7:].split("|", 1)
                    speaker = parts[0] if len(parts) > 1 else "Speaker A"
                    phrase = parts[1] if len(parts) > 1 else parts[0]
                    logger.info(f"Session {session_id[:8]}…: injecting text: [{speaker}] {phrase}")
                    await _inject_phrase(session_id, speaker, phrase, manager)
                continue

            # Binary audio chunk
            pcm_bytes = message.get("bytes")
            if not pcm_bytes:
                continue

            # Guard: reject oversized chunks
            if len(pcm_bytes) > MAX_CHUNK_BYTES:
                logger.warning(
                    f"Session {session_id[:8]}…: chunk too large ({len(pcm_bytes)}B) — dropped"
                )
                continue

            logger.info(
                f"Session {session_id[:8]}…: received chunk {len(pcm_bytes)}B"
            )

            await _process_chunk(
                session_id=session_id,
                pcm_bytes=pcm_bytes,
                vad=vad,
                transcriber=transcriber,
                diarizer=diarizer,
                manager=manager,
            )

    except WebSocketDisconnect:
        logger.info(f"Session {session_id[:8]}…: audio WebSocket disconnected")
        await manager.set_status(session_id, SessionStatus.INTERRUPTED)
    except Exception as exc:
        logger.error(f"Session {session_id[:8]}…: audio handler error — {exc}", exc_info=True)
        await manager.set_status(session_id, SessionStatus.FAILED)
    finally:
        # Flush any remaining buffered audio
        await _flush_final(session_id, transcriber, diarizer, manager)
        await manager.end(session_id)
        await broadcast_status(session.ws_status, "completed")
        logger.info(f"Session {session_id[:8]}…: audio handler closed")


# ── Internal helpers ──────────────────────────────────────────────────────────

async def _process_chunk(
    session_id: str,
    pcm_bytes: bytes,
    vad,
    transcriber,
    diarizer,
    manager,
) -> None:
    """Run one PCM chunk through the full pipeline."""
    session = manager.get(session_id)
    if session is None:
        return

    # 1. Voice Activity Detection (CPU, synchronous, fast)
    is_speech = vad.is_speech(pcm_bytes)
    logger.info(
        f"Session {session_id[:8]}…: VAD → speech={is_speech} "
        f"({len(pcm_bytes)}B, buffer={session.audio_buffer.buffered_ms:.0f}ms)"
    )

    # 2. Push to buffer; check if a flush is triggered
    flushed_data = session.audio_buffer.push(pcm_bytes, is_speech)
    if flushed_data is None:
        return  # buffer not ready yet

    flushed, time_offset = flushed_data

    logger.info(
        f"Session {session_id[:8]}…: buffer flushed {len(flushed)}B → sending to Whisper"
    )

    await _transcribe_and_enrich(
        session=session,
        session_id=session_id,
        flushed=flushed,
        time_offset=time_offset,
        transcriber=transcriber,
        diarizer=diarizer,
    )


async def _transcribe_and_enrich(
    session,
    session_id: str,
    flushed: bytes,
    time_offset: float,
    transcriber,
    diarizer,
) -> None:
    """Transcribe audio bytes, perform speaker diarization, enrichment, and broadcast updates."""
    # 4. Transcribe (GPU, async via thread pool)
    raw_segments = await transcriber.transcribe_async(
        flushed,
        time_offset=max(0.0, time_offset),
    )

    logger.info(
        f"Session {session_id[:8]}…: Whisper returned {len(raw_segments)} segment(s)"
    )

    if not raw_segments:
        return

    # 5. Speaker diarization (GPU, sequential after Whisper)
    prev_speaker = "Speaker 1"
    async with session.lock:
        if session.conversation.transcript_segments:
            prev_speaker = session.conversation.transcript_segments[-1].get("speaker", "Speaker 1")

    loop = asyncio.get_running_loop()
    diarized = await loop.run_in_executor(
        None,
        lambda: diarizer.assign_speakers(raw_segments, flushed, max(0.0, time_offset), prev_speaker),
    )

    # 6. NLP enrichment (sentiment per segment)
    nlp = get_nlp_engine()  # returns the module-level singleton; no model reload

    raw_dicts = [{"text": s.text, "start": s.start, "end": s.end} for s in diarized]
    enriched = await loop.run_in_executor(None, nlp.enrich_transcript, raw_dicts)

    # Merge enrichment back onto diarized segments
    for i, seg in enumerate(diarized):
        if i < len(enriched):
            seg.__dict__.update({
                "sentiment": enriched[i].get("sentiment", 0.0),
                "sentiment_label": enriched[i].get("sentiment_label", "Neutral"),
                "sentiment_confidence": enriched[i].get("sentiment_confidence", 0.0),
                "keywords": enriched[i].get("keywords", []),
            })

    # 7. Update ConversationEngine and generate alerts
    from engine.conversation_engine import get_conversation_engine
    engine = get_conversation_engine()

    async with session.lock:
        # Append to transcript
        for seg in diarized:
            session.conversation.transcript_segments.append(seg.__dict__)

        updated_metrics, new_alerts = engine.process_segments(
            diarized, session.conversation, session.mode
        )
        session.conversation = updated_metrics

    # 8. Broadcast all updates
    for seg in diarized:
        seg_dict = {
            "session_id": session_id,
            "speaker": seg.speaker,
            "text": seg.text,
            "start": seg.start,
            "end": seg.end,
            "sentiment": getattr(seg, "sentiment", 0.0),
            "sentiment_label": getattr(seg, "sentiment_label", "Neutral"),
        }
        await broadcast_transcript(session.ws_transcript, seg_dict)

    metrics_dict = {
        "health_score": updated_metrics.health_score,
        "sentiment": updated_metrics.sentiment,
        "speaking_ratio": updated_metrics.speaking_ratio,
        "participation": updated_metrics.participation,
        "filler_count": updated_metrics.filler_count,
        "objections": updated_metrics.objections,
        "buying_signals": updated_metrics.buying_signals,
        "duration_seconds": session.elapsed_seconds,
    }

    await broadcast_all(
        ws_transcript=None,  # already sent above
        ws_metrics=session.ws_metrics,
        ws_alerts=session.ws_alerts,
        metrics=metrics_dict,
        new_alerts=new_alerts,
    )


async def _flush_final(session_id: str, transcriber, diarizer, manager) -> None:
    """Flush any remaining buffered audio on session end."""
    session = manager.get(session_id)
    if session is None:
        return

    remaining_data = session.audio_buffer.flush_remaining()
    if remaining_data:
        flushed, time_offset = remaining_data
        logger.info(f"Session {session_id[:8]}…: flushing {len(flushed)}B remaining audio")
        await _transcribe_and_enrich(
            session=session,
            session_id=session_id,
            flushed=flushed,
            time_offset=time_offset,
            transcriber=transcriber,
            diarizer=diarizer,
        )


async def _inject_phrase(session_id: str, speaker: str, phrase: str, manager) -> None:
    """Mock process a text phrase as a transcript segment and update metrics."""
    session = manager.get(session_id)
    if session is None:
        return

    start_time = round(session.elapsed_seconds, 2)
    end_time = round(start_time + 2.0, 2)

    from services.nlp_engine import get_nlp_engine
    nlp = get_nlp_engine()
    raw_dicts = [{"text": phrase, "start": start_time, "end": end_time}]

    loop = asyncio.get_running_loop()
    enriched = await loop.run_in_executor(None, nlp.enrich_transcript, raw_dicts)

    seg_dict = {
        "speaker": speaker,
        "text": phrase,
        "start": start_time,
        "end": end_time,
        "sentiment": enriched[0].get("sentiment", 0.0) if enriched else 0.0,
        "sentiment_label": enriched[0].get("sentiment_label", "Neutral") if enriched else "Neutral",
    }

    from engine.conversation_engine import get_conversation_engine
    engine = get_conversation_engine()

    async with session.lock:
        session.conversation.transcript_segments.append(seg_dict)
        updated_metrics, new_alerts = engine.process_segments(
            [seg_dict], session.conversation, session.mode
        )
        session.conversation = updated_metrics

    # Broadcast segment to transcript websocket
    await broadcast_transcript(session.ws_transcript, {**seg_dict, "session_id": session_id})

    # Broadcast updated metrics including objections and buying_signals
    metrics_dict = {
        "health_score": updated_metrics.health_score,
        "sentiment": updated_metrics.sentiment,
        "speaking_ratio": updated_metrics.speaking_ratio,
        "participation": updated_metrics.participation,
        "filler_count": updated_metrics.filler_count,
        "objections": updated_metrics.objections,
        "buying_signals": updated_metrics.buying_signals,
        "duration_seconds": session.elapsed_seconds,
    }

    await broadcast_all(
        ws_transcript=None,
        ws_metrics=session.ws_metrics,
        ws_alerts=session.ws_alerts,
        metrics=metrics_dict,
        new_alerts=new_alerts,
    )
