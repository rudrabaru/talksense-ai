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
import difflib
import logging
import string
import time
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from audio.ib_shadow import ShadowRunner, shadow_enabled
from audio.transcriber import get_transcriber
from audio.vad import get_vad
from core.config import get_settings
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
    vad_factory = get_vad()
    vad = vad_factory.create_session_vad()
    transcriber = get_transcriber()
    diarizer = None
    shadow: ShadowRunner | None = None

    # ── Validate session ──────────────────────────────────────────────────────
    session = manager.get(session_id)
    if session is None:
        logger.warning(f"Audio WS: session {session_id[:8]}… not found — rejecting")
        await websocket.accept()
        await websocket.close(code=4004, reason="Session not found")
        return

    # Reject connections to already-terminated sessions
    terminal = {
        SessionStatus.COMPLETED,
        SessionStatus.FAILED,
        SessionStatus.INTERRUPTED,
        SessionStatus.EXPIRED,
    }
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
        import time

        session.recording_started_at = time.monotonic()

    await broadcast_status(session.ws_status, "active")

    # ── IB 1.5s shadow tap (inert; default OFF) ──────────────────────────────
    # Constructed only when the feature flag is on and a slot is free. When OFF
    # this block is skipped and `shadow` stays None — the production path below
    # is byte-for-byte unchanged. Never fatal to the session.
    if shadow_enabled(session_id):
        try:
            shadow = ShadowRunner(
                session_id,
                session.mode,
                session.audio_buffer.get_audio_file_path,
            )
            shadow.start()
        except Exception:
            shadow = None
            logger.warning(
                "Session %s…: IB shadow init failed; continuing without it",
                session_id[:8],
                exc_info=True,
            )

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
                    async with session.lock:
                        session.status = SessionStatus.COMPLETED
                    break
                elif text_lower == "pause":
                    logger.info(f"Session {session_id[:8]}…: client sent 'pause'")
                    import time

                    async with session.lock:
                        if session.recording_started_at is not None:
                            session._accumulated_recording_duration += (
                                time.monotonic() - session.recording_started_at
                            )
                            session.recording_started_at = None
                elif text_lower == "resume":
                    logger.info(f"Session {session_id[:8]}…: client sent 'resume'")
                    import time

                    async with session.lock:
                        session.recording_started_at = time.monotonic()
                elif text_lower == "ping":
                    await websocket.send_text("pong")
                elif text_lower.startswith("inject:"):
                    # format: inject:Speaker Name|phrase text
                    parts = text[7:].split("|", 1)
                    speaker = parts[0] if len(parts) > 1 else "Speaker A"
                    phrase = parts[1] if len(parts) > 1 else parts[0]
                    logger.info(
                        f"Session {session_id[:8]}…: injecting text: [{speaker}] {phrase}"  # noqa: E501
                    )
                    await _inject_phrase(session_id, speaker, phrase, manager)
                continue

            # Binary audio chunk
            pcm_bytes = message.get("bytes")
            if not pcm_bytes:
                continue

            # Guard: reject oversized chunks
            if len(pcm_bytes) > MAX_CHUNK_BYTES:
                logger.warning(
                    f"Session {session_id[:8]}…: chunk too large ({len(pcm_bytes)}B) — dropped"  # noqa: E501
                )
                continue

            # IB shadow tap (inert; no-op when shadow is None). Non-blocking:
            # enqueues the raw PCM ref and returns immediately, dropping on a
            # full bounded queue. Does not touch the production pipeline.
            if shadow is not None:
                shadow.feed(pcm_bytes, time.monotonic())

            logger.info(f"Session {session_id[:8]}…: received chunk {len(pcm_bytes)}B")

            await _process_chunk(
                session_id=session_id,
                pcm_bytes=pcm_bytes,
                vad=vad,
                transcriber=transcriber,
                diarizer=diarizer,
                manager=manager,
            )

    except (WebSocketDisconnect, RuntimeError) as exc:
        if isinstance(exc, RuntimeError) and not (
            "Cannot call" in str(exc) and "disconnect" in str(exc)
        ):
            logger.error(
                f"Session {session_id[:8]}…: audio handler error — {exc}", exc_info=True
            )
            await manager.set_status(session_id, SessionStatus.FAILED)
        else:
            logger.info(f"Session {session_id[:8]}…: audio WebSocket disconnected")
            # Only set INTERRUPTED if we haven't already marked it COMPLETED or FAILED
            async with session.lock:
                if session.status not in {
                    SessionStatus.COMPLETED,
                    SessionStatus.FAILED,
                }:
                    session.status = SessionStatus.INTERRUPTED
    except Exception as exc:
        logger.error(
            f"Session {session_id[:8]}…: audio handler error — {exc}", exc_info=True
        )
        await manager.set_status(session_id, SessionStatus.FAILED)
    finally:
        from utils.profiler import register_profiler

        register_profiler(session_id)

        # Flush any remaining buffered audio
        await _flush_final(session_id, transcriber, diarizer, manager)

        # IB shadow (inert): snapshot the production transcript, then drain the
        # shadow consumer BEFORE manager.end() removes the session. Never fatal.
        if shadow is not None:
            try:
                async with session.lock:
                    _prod_segments = list(session.conversation.transcript_segments)
                shadow.snapshot_prod_transcript(_prod_segments)
                await shadow.stop()
            except Exception:
                logger.warning(
                    "Session %s…: IB shadow teardown failed",
                    session_id[:8],
                    exc_info=True,
                )

        # Broadcast the actual terminal status (completed/interrupted/failed)
        terminal_status = (
            session.status.value
            if hasattr(session.status, "value")
            else str(session.status)
        )

        try:
            # 1. Guarantee delivery BEFORE cleanup removes the socket
            await broadcast_status(session.ws_status, terminal_status)
        except Exception as exc:
            logger.warning(
                "Session %s…: failed to broadcast terminal status — %s",
                session_id[:8],
                exc,
            )
        finally:
            # 2. Guarantee session destruction and socket cleanup even if broadcast fails
            # Pass the current session status to preserve interrupted/failed states in DB
            await manager.end(session_id, session.status, from_audio_handler=True)

        logger.info(
            f"Session {session_id[:8]}…: audio handler closed (status={terminal_status})"
        )


# ── Internal helpers ──────────────────────────────────────────────────────────


def _merge_overlapping_text(text1: str, text2: str) -> str:
    """
    Merge two text segments by finding a sliding overlap.
    Robust against Whisper transcription jitter (dropped words, punctuation).
    """
    if not text1:
        return text2
    if not text2:
        return text1

    words1 = text1.strip().split()
    words2 = text2.strip().split()

    # Normalize for comparison
    norm1 = [w.lower().strip(string.punctuation) for w in words1]
    norm2 = [w.lower().strip(string.punctuation) for w in words2]

    # We only care about the overlap between the END of text1 and START of text2.
    # Limit search window to improve performance (O(n) near the boundaries).
    SEARCH_WINDOW = 20
    search1 = norm1[-SEARCH_WINDOW:] if len(norm1) > SEARCH_WINDOW else norm1
    search2 = norm2[:SEARCH_WINDOW]

    matcher = difflib.SequenceMatcher(None, search1, search2)
    blocks = matcher.get_matching_blocks()

    best_overlap = None
    best_ratio = 0.0

    for start_idx in range(len(blocks) - 1):
        if blocks[start_idx].size == 0:
            continue

        for end_idx in range(start_idx, len(blocks) - 1):
            if blocks[end_idx].size == 0:
                continue

            first_block = blocks[start_idx]
            last_block = blocks[end_idx]

            region1_start = first_block.a
            region1_end = last_block.a + last_block.size
            region2_start = first_block.b
            region2_end = last_block.b + last_block.size

            # Constraint 1: Overlap must reach near the end of text1
            # Allow up to 3 dropped words at the very end
            if len(search1) - region1_end > 3:
                continue

            # Constraint 2: Overlap must start near the beginning of text2
            # Allow up to 3 dropped words at the very beginning
            if region2_start > 3:
                continue

            matching_words = sum(b.size for b in blocks[start_idx : end_idx + 1])
            region1_len = region1_end - region1_start
            region2_len = region2_end - region2_start

            if region1_len == 0 and region2_len == 0:
                continue

            ratio = (2.0 * matching_words) / (region1_len + region2_len)

            # Find the strongest overlapping bounding box
            if matching_words >= 2 and ratio >= 0.65:
                # Better ratio, or same ratio but longer overlap
                if ratio > best_ratio or (
                    ratio == best_ratio
                    and matching_words
                    > (best_overlap["matching_words"] if best_overlap else 0)
                ):
                    best_ratio = ratio
                    best_overlap = {
                        "orig2_end": region2_end,
                        "matching_words": matching_words,
                    }

            # Fallback for very short matches (1 word) but only if they are exactly at the boundaries
            elif (
                matching_words == 1
                and (len(search1) - region1_end) <= 1
                and region2_start <= 1
                and ratio >= 0.65
            ):
                if ratio > best_ratio:
                    best_ratio = ratio
                    best_overlap = {
                        "orig2_end": region2_end,
                        "matching_words": matching_words,
                    }

    if best_overlap:
        # Strategy: keep text1 entirely (preserves confirmed words), append non-overlapping part of text2
        append_words = words2[best_overlap["orig2_end"] :]
        if append_words:
            return " ".join(words1 + append_words)
        else:
            return " ".join(words1)

    # Safe concatenation fallback
    return text1 + " " + text2


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

    audio_time = session.audio_buffer._total_bytes_received / 32000.0

    async with session.lock:
        if is_speech:
            session.conversation.last_speech_time_seconds = audio_time
            session.conversation.last_silence_seconds = 0.0
        elif session.conversation.last_speech_time_seconds is not None:
            session.conversation.last_silence_seconds = (
                audio_time - session.conversation.last_speech_time_seconds
            )

    if flushed_data is None:
        async with session.lock:
            from engine.conversation_engine import get_conversation_engine

            engine = get_conversation_engine()
            new_alerts = engine.check_silence_alerts(session.conversation, session_id)
            if new_alerts:
                metrics_dict = {
                    "health_score": session.conversation.health_score,
                    "sentiment": session.conversation.sentiment,
                    "speaking_ratio": session.conversation.speaking_ratio,
                    "participation": session.conversation.participation,
                    "filler_count": session.conversation.filler_count,
                    "objections": session.conversation.objections,
                    "buying_signals": session.conversation.buying_signals,
                    "duration_seconds": session.elapsed_seconds,
                    "roles": session.conversation.roles,
                    "coaching_tips": session.conversation.coaching_tips,
                    "last_updated": time.time(),
                }
                from ws.broadcast import broadcast_all

                await broadcast_all(
                    ws_transcript=None,
                    ws_metrics=session.ws_metrics,
                    ws_alerts=session.ws_alerts,
                    metrics=metrics_dict,
                    new_alerts=new_alerts,
                )
        return  # buffer not ready yet

    flushed, time_offset, is_partial = flushed_data

    logger.info(
        f"Session {session_id[:8]}…: buffer flushed {len(flushed)}B → sending to Whisper (partial={is_partial})"  # noqa: E501
    )

    await _transcribe_and_enrich(
        session=session,
        session_id=session_id,
        flushed=flushed,
        time_offset=time_offset,
        transcriber=transcriber,
        diarizer=diarizer,
        is_partial=is_partial,
    )


async def _transcribe_and_enrich(
    session,
    session_id: str,
    flushed: bytes,
    time_offset: float,
    transcriber,
    diarizer,
    is_partial: bool = False,
) -> None:
    """Transcribe audio bytes, perform speaker diarization, enrichment, and broadcast updates."""  # noqa: E501
    # 4. Transcribe (GPU, async via thread pool)
    _settings = get_settings()
    _language = _settings.whisper_language or None  # None = auto-detect (multilingual)

    # Extract previous text for Whisper initial_prompt to prevent hallucinations
    prev_text = ""
    async with session.lock:
        if session.conversation.transcript_segments:
            prev_text = session.conversation.transcript_segments[-1].get("text", "")

    raw_segments = await transcriber.transcribe_async(
        flushed,
        time_offset=max(0.0, time_offset),
        language=_language,
        initial_prompt=prev_text[-200:] if prev_text else None,
        is_partial=is_partial,
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
            prev_speaker = session.conversation.transcript_segments[-1].get(
                "speaker", "Speaker 1"
            )

    if diarizer is None:
        diarized = raw_segments
        # Default all segments to "Speaker 1"
        for seg in diarized:
            seg.speaker = "Speaker 1"
    else:
        diarized = await diarizer.assign_speakers_async(
            raw_segments,
            flushed,
            max(0.0, time_offset),
            prev_speaker,
            session.speaker_profile,
        )

    # 6. NLP enrichment (sentiment per segment)
    nlp = get_nlp_engine()  # returns the module-level singleton; no model reload

    raw_dicts = [{"text": s.text, "start": s.start, "end": s.end} for s in diarized]
    loop = asyncio.get_running_loop()
    enriched = await loop.run_in_executor(None, nlp.enrich_transcript, raw_dicts)

    # Merge enrichment back onto diarized segments
    for i, seg in enumerate(diarized):
        if i < len(enriched):
            seg.__dict__.update(
                {
                    "sentiment": enriched[i].get("sentiment", 0.0),
                    "sentiment_label": enriched[i].get("sentiment_label", "Neutral"),
                    "sentiment_confidence": enriched[i].get(
                        "sentiment_confidence", 0.0
                    ),
                    "keywords": enriched[i].get("keywords", []),
                }
            )

    # 7. Update ConversationEngine and generate alerts
    from engine.conversation_engine import get_conversation_engine

    engine = get_conversation_engine()

    async with session.lock:
        # Append or Merge to transcript
        for seg in diarized:
            # Strip non-serializable TranscriptWord objects before saving to DB
            if hasattr(seg, "words"):
                seg.words = None

            merged = False
            if session.conversation.transcript_segments:
                # Check recent segments for overlap
                for i in range(
                    len(session.conversation.transcript_segments) - 1,
                    max(-1, len(session.conversation.transcript_segments) - 5),
                    -1,
                ):
                    last_seg = session.conversation.transcript_segments[i]
                    if last_seg.get("speaker") != seg.speaker:
                        # Intervening segment from another speaker found. Stop searching.
                        break
                    if (
                        last_seg.get("speaker") == seg.speaker
                        and last_seg.get("end", 0) >= seg.start - 0.5
                    ):
                        merged_text = _merge_overlapping_text(
                            last_seg.get("text", ""), seg.text
                        )
                        if last_seg.get("text", "") != merged_text:
                            last_seg["text"] = merged_text
                            last_seg["end"] = max(last_seg.get("end", 0), seg.end)
                            last_seg["sentiment"] = getattr(seg, "sentiment", 0.0)
                            last_seg["sentiment_label"] = getattr(
                                seg, "sentiment_label", "Neutral"
                            )
                            if "segment_id" not in last_seg:
                                last_seg["segment_id"] = str(uuid.uuid4())

                            session.dirty_transcript_segment_ids.add(
                                last_seg["segment_id"]
                            )

                        seg.__dict__["segment_id"] = last_seg["segment_id"]
                        seg.__dict__["text"] = merged_text
                        seg.__dict__["end"] = last_seg["end"]
                        merged = True
                        break

            if not merged:
                seg.__dict__["segment_id"] = str(uuid.uuid4())
                session.conversation.transcript_segments.append(seg.__dict__)

        # Authoritative audio timeline from pure byte accumulation
        session.conversation.audio_time_seconds = (
            session.audio_buffer._total_bytes_received / 32000.0
        )

        updated_metrics, new_alerts = engine.process_segments(
            session.conversation,
            session.mode,
            session_id,
            session.host_embedding,
        )
        session.conversation = updated_metrics

    # 8. Broadcast all updates
    for seg in diarized:
        seg_dict = {
            "session_id": session_id,
            "segment_id": getattr(seg, "segment_id", None),
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
        "roles": updated_metrics.roles,
        "coaching_tips": updated_metrics.coaching_tips,
        "last_updated": time.time(),
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
        flushed, time_offset, is_partial = remaining_data
        logger.info(
            f"Session {session_id[:8]}…: flushing {len(flushed)}B remaining audio"
        )
        await _transcribe_and_enrich(
            session=session,
            session_id=session_id,
            flushed=flushed,
            time_offset=time_offset,
            transcriber=transcriber,
            diarizer=diarizer,
            is_partial=is_partial,
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
        "sentiment_label": (
            enriched[0].get("sentiment_label", "Neutral") if enriched else "Neutral"
        ),
    }

    from engine.conversation_engine import get_conversation_engine

    engine = get_conversation_engine()

    async with session.lock:
        session.conversation.transcript_segments.append(seg_dict)

        # Authoritative audio timeline from pure byte accumulation
        session.conversation.audio_time_seconds = (
            session.audio_buffer._total_bytes_received / 32000.0
        )

        updated_metrics, new_alerts = engine.process_segments(
            session.conversation,
            session.mode,
            session_id,
            session.host_embedding,
        )
        session.conversation = updated_metrics

    # Broadcast segment to transcript websocket
    await broadcast_transcript(
        session.ws_transcript, {**seg_dict, "session_id": session_id}
    )

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
        "roles": updated_metrics.roles,
        "coaching_tips": updated_metrics.coaching_tips,
        "last_updated": time.time(),
    }

    await broadcast_all(
        ws_transcript=None,
        ws_metrics=session.ws_metrics,
        ws_alerts=session.ws_alerts,
        metrics=metrics_dict,
        new_alerts=new_alerts,
    )
