"""
TalkSense AI — Post-Session Speaker Attribution Service

Runs after a session transitions to COMPLETED.  Reads the full-session
WAV file written by AudioBuffer, runs a single Pyannote diarization pass
on the complete audio, and retroactively updates all transcript_segment
speaker_id fields in PostgreSQL.

Pipeline:
    audio_file_path
        → Pyannote (full WAV, single pass)
        → Speaker turn timeline [(start, end, speaker_label), ...]
        → Two-stage speaker assignment per DB transcript segment:
              Stage 1 — winner-take-all temporal overlap
              Stage 2 — nearest-turn proximity (for gap segments)
        → Batch UPDATE transcript_segments.speaker_id
        → Update sessions.speaker_attribution_status

Design notes:
  - Pyannote is synchronous.  The public entry point wraps it in
    asyncio.get_event_loop().run_in_executor() so it does not block the
    FastAPI event loop.
  - The pipeline uses its own AsyncSessionLocal() DB connection — never
    the flusher's connection.
  - Status transitions are committed independently so a crash at any step
    leaves the session in an observable state ("processing" rather than
    "pending").
  - Exceptions are caught and logged; they are never propagated to the
    session manager, keeping session completion fast regardless of
    diarization success or failure.
"""

import asyncio
import logging
import os
import time

from utils.profiler import get_profiler, profile_stage, unregister_profiler

logger = logging.getLogger(__name__)


# ── Public entry point ────────────────────────────────────────────────────────


async def run_post_session_diarization(
    session_id: str,
    audio_file_path: str,
) -> None:
    """
    Orchestrate the full post-session diarization pipeline.

    This coroutine is designed to be launched as a fire-and-forget
    asyncio.create_task() from SessionManager.end().  Any uncaught
    exception is logged but never re-raised.

    Sequence:
      1. Set speaker_attribution_status = "pending" in DB.
      2. Validate that the WAV file exists and has meaningful content.
      3. Set status = "processing".
      4. Run Pyannote in a thread executor (non-blocking).
      5. Load all transcript segments from DB.
      6. Map each segment to the best-overlapping speaker turn.
      7. Batch-update speaker_id in DB.
      8. Set status = "completed".
      9. Log before/after summary.

    On any failure: set status = "failed" and log the exception.

    Args:
        session_id:      UUID string of the completed session.
        audio_file_path: Absolute path to the finalised WAV file.
    """
    t_start = time.monotonic()
    logger.info(
        "post_session_diarizer — session %s: started (audio=%s)",
        session_id[:8],
        audio_file_path,
    )

    try:
        # ── Step 1: mark pending ──────────────────────────────────────────────
        await _set_attribution_status(session_id, "pending")

        # ── Step 2: validate audio file ───────────────────────────────────────
        if not os.path.isfile(audio_file_path):
            logger.warning(
                "post_session_diarizer — session %s: WAV not found at %s, aborting",
                session_id[:8],
                audio_file_path,
            )
            await _set_attribution_status(session_id, "failed")
            return

        file_size = os.path.getsize(audio_file_path)
        # A WAV header alone is 44 bytes; require at least 0.5s of audio
        # (0.5 * 16000 * 2 = 16000 bytes + 44 header = 16044 bytes minimum)
        if file_size < 16_044:
            logger.warning(
                "post_session_diarizer — session %s: WAV too small (%d bytes), aborting",  # noqa: E501
                session_id[:8],
                file_size,
            )
            await _set_attribution_status(session_id, "failed")
            return

        wav_duration = max(0.0, (file_size - 44) / (16000 * 2))

        try:
            from db import crud
            from db.database import AsyncSessionLocal

            async with AsyncSessionLocal() as db:
                segments = await crud.get_all_transcript_segments(db, session_id)
                latest_segment_end = max((s.end_time for s in segments), default=0.0)

                gap = latest_segment_end - wav_duration
                if gap > 1.0:
                    logger.warning(
                        "wav duration %.2fs but latest transcript %.2fs (gap=%.2fs)",
                        wav_duration,
                        latest_segment_end,
                        gap,
                    )
        except Exception as e:
            logger.warning("Failed to validate audio duration gap: %s", e)

        # ── Step 3: mark processing ───────────────────────────────────────────
        await _set_attribution_status(session_id, "processing")

        # ── Step 4: run Pyannote in thread executor ───────────────────────────
        loop = asyncio.get_running_loop()
        with profile_stage(session_id, "Speaker Diarization"):
            turns = await loop.run_in_executor(
                None,
                _run_pyannote_sync,
                audio_file_path,
                session_id,
            )

        if turns is None:
            # _run_pyannote_sync already logged the error
            await _set_attribution_status(session_id, "failed")
            return

        # ── Step 5 & 6 & 7: fetch segments, map speakers, update DB ──────────
        with profile_stage(session_id, "Speaker Attribution"):
            update_result = await _apply_speaker_updates(session_id, turns)

        # ── Step 8: mark completed ────────────────────────────────────────────
        await _set_attribution_status(session_id, "completed")

        # ── Step 9: persist quality diagnostics into session_metrics ─────────
        unique_speakers = len({s for _, _, s in turns})
        diagnostics = {
            "speakers_detected": unique_speakers,
            "speaker_turns": len(turns),
            "segments_updated": update_result["segments_updated"],
            "total_segments": update_result["total_segments"],
            "coverage_percent": round(
                update_result["segments_updated"]
                / max(update_result["total_segments"], 1)
                * 100,
                1,
            ),
            "overlap_matched": update_result.get("overlap_count", 0),
            "proximity_matched": update_result.get("proximity_count", 0),
        }
        await _persist_attribution_diagnostics(session_id, diagnostics)

        elapsed = time.monotonic() - t_start
        logger.info(
            "post_session_diarizer — session %s: completed in %.1fs — "
            "%d speaker(s), %d turn(s), %d/%d segment(s) updated "
            "(coverage=%.1f%%, overlap=%d, proximity=%d)",
            session_id[:8],
            elapsed,
            unique_speakers,
            len(turns),
            update_result["segments_updated"],
            update_result["total_segments"],
            diagnostics["coverage_percent"],
            diagnostics["overlap_matched"],
            diagnostics["proximity_matched"],
        )

        # ── Step 10: Role Classification (Offline-First mode-aware mapping) ─────────────
        from ws.session_manager import get_session_manager
        
        manager = get_session_manager()
        session_obj = manager.get(session_id)
        
        primary_roles = {}
        if session_obj and session_obj.conversation:
            primary_roles = session_obj.conversation.roles

        # If somehow missing (e.g. failed session before roles inferred), fallback to DB
        if not primary_roles:
            from db import crud
            from db.database import AsyncSessionLocal
            async with AsyncSessionLocal() as db:
                metrics = await crud.get_latest_session_metrics(db, session_id)
                role_metric = next((m for m in metrics if m.metric_name == "speaker_roles"), None)
                if role_metric and role_metric.metric_value:
                    primary_roles = role_metric.metric_value

        with profile_stage(session_id, "Database writes"):
            from db import crud
            from db.database import AsyncSessionLocal
            
            async with AsyncSessionLocal() as db:
                metrics_to_save = []
                
                # Standardized offline-first roles
                if primary_roles:
                    metrics_to_save.append(
                        {"metric_name": "speaker_roles", "metric_value": primary_roles}
                    )
                    
                # Save role classification result
                if metrics_to_save:
                    await crud.save_session_metrics_batch(
                        db, session_id, metrics_to_save
                    )
                    await db.commit()

        logger.info(
            "post_session_diarizer — session %s: roles classified (offline):\n%s",
            session_id[:8],
            (
                "\n".join([f"{spk} -> {role}" for spk, role in primary_roles.items()])
                if primary_roles
                else "none"
            ),
        )

        # ── Step 11: Objection Handling Analysis ───────────────────────────────
        from services.objection_handler import analyze_objection_handling

        async with AsyncSessionLocal() as db:
            await analyze_objection_handling(db, session_id)
            with profile_stage(session_id, "Database writes"):
                await db.commit()

        # ── Step 12: Talk Ratio Timeline ───────────────────────────────────────
        from services.talk_ratio_analyzer import analyze_talk_ratio

        async with AsyncSessionLocal() as db:
            # Fetch all updated segments
            segments = await crud.get_all_transcript_segments(db, session_id)
            if segments:
                talk_ratio_data = analyze_talk_ratio(segments)
                # Persist two metrics
                with profile_stage(session_id, "Database writes"):
                    await crud.save_session_metrics_batch(
                        db,
                        session_id,
                        [
                            {
                                "metric_name": "talk_ratio_summary",
                                "metric_value": {
                                    "summary": talk_ratio_data["summary"],
                                    "overall_participation": talk_ratio_data[
                                        "overall_participation"
                                    ],
                                },
                            },
                            {
                                "metric_name": "talk_timeline",
                                "metric_value": {
                                    "timeline": talk_ratio_data["timeline"]
                                },
                            },
                        ],
                    )
                    await db.commit()
                logger.info(
                    "post_session_diarizer — session %s: Talk ratio timeline generated.",  # noqa: E501
                    session_id[:8],
                )

        # ── Step 12.5: Context Analysis & Upsert AnalysisResult ─────────────────
        from services.context_analyzer import analyze_meeting, analyze_sales

        async with AsyncSessionLocal() as db:
            db_segments = await crud.get_all_transcript_segments(db, session_id)
            session_row = await crud.get_session(db, session_id)

            if db_segments and session_row:
                enriched_segments = []
                for s in db_segments:
                    enriched_segments.append(
                        {
                            "start": s.start_time,
                            "end": s.end_time,
                            "speaker": s.speaker_id or "Speaker 1",
                            "text": s.text or "",
                            "sentiment": s.sentiment or 0.0,
                            "sentiment_label": s.sentiment_label or "Neutral",
                            "sentiment_confidence": 1.0,
                        }
                    )

                final_transcript = {
                    "session_id": session_id,
                    "text": " ".join([s["text"] for s in enriched_segments]),
                    "segments": enriched_segments,
                }

                # Run the appropriate mode analysis inside loop executor
                if session_row.mode == "sales":
                    insights = await loop.run_in_executor(
                        None, analyze_sales, enriched_segments, session_id
                    )
                else:
                    insights = await loop.run_in_executor(
                        None, analyze_meeting, final_transcript
                    )

                # Save AnalysisResult
                q_score = (
                    insights.get("quality", {}).get("score", 5)
                    if isinstance(insights.get("quality"), dict)
                    else 5
                )
                health_score = int(q_score * 10)

                with profile_stage(session_id, "Database writes"):
                    import uuid as _uuid

                    from sqlalchemy.dialects.postgresql import insert as pg_insert

                    from db.models import AnalysisResult as DBAnalysisResult

                    stmt = (
                        pg_insert(DBAnalysisResult)
                        .values(
                            session_id=_uuid.UUID(session_id),
                            health_score=health_score,
                            summary=insights.get("summary", ""),
                            report_json=insights,
                        )
                        .on_conflict_do_update(
                            index_elements=["session_id"],
                            set_={
                                "health_score": health_score,
                                "summary": insights.get("summary", ""),
                                "report_json": insights,
                            },
                        )
                    )
                    await db.execute(stmt)

                    metrics_to_save = [
                        {"metric_name": "health_score", "metric_value": health_score},
                        {
                            "metric_name": "sentiment_score",
                            "metric_value": insights.get("sentiment_score", 0.0),
                        },
                        {
                            "metric_name": "objections",
                            "metric_value": insights.get("objections", []),
                        },
                        {
                            "metric_name": "buying_signals",
                            "metric_value": (
                                insights.get("buying_signals", [])
                                if "buying_signals" in insights
                                else []
                            ),
                        },
                    ]
                    await crud.save_session_metrics_batch(
                        db, session_id, metrics_to_save
                    )
                    await db.commit()

        # ── Step 13: Client Memory Profile ─────────────────────────────────────
        try:
            from services.client_memory import update_client_memory

            with profile_stage(session_id, "Client Memory update"):
                async with AsyncSessionLocal() as db:
                    session_row = await crud.get_session(db, session_id)
                    if session_row and session_row.client_id:
                        logger.info(
                            "post_session_diarizer — session %s: Updating client memory for client %s...",  # noqa: E501
                            session_id[:8],
                            session_row.client_id,
                        )
                        await update_client_memory(db, session_row.client_id)
                        with profile_stage(session_id, "Database writes"):
                            await db.commit()
                        logger.info(
                            "post_session_diarizer — session %s: Client memory updated.",  # noqa: E501
                            session_id[:8],
                        )
                    else:
                        logger.info(
                            "post_session_diarizer — session %s: No client linked, skipping memory update.",  # noqa: E501
                            session_id[:8],
                        )
        except Exception as e:
            logger.error(
                "Failed to update client memory for session %s: %s",
                session_id[:8],
                e,
                exc_info=True,
            )

        # ── Step 14: Simulate Dashboard data preparation ────────────────────────
        try:
            with profile_stage(session_id, "Dashboard data preparation"):
                async with AsyncSessionLocal() as db:
                    # Run the exact dashboard query DB fallback logic
                    db_session = await crud.get_session(db, session_id)
                    if db_session:
                        await crud.get_transcript_segments(db, session_id, limit=50)
                        await crud.get_latest_session_metrics(db, session_id)
                        await crud.get_alerts(db, session_id, limit=50)

                        # Reconstruct metrics dictionary & speaking ratios
                        db_segments = await crud.get_all_transcript_segments(
                            db, session_id
                        )
                        if db_segments:
                            participation = {}
                            for seg in db_segments:
                                speaker = seg.speaker_id or "Speaker 1"
                                text = seg.text or ""
                                word_count = len(text.split())
                                participation[speaker] = (
                                    participation.get(speaker, 0) + word_count
                                )
                            total_words = sum(participation.values()) or 1
                            # Compute speaking ratio to simulate load
                            {
                                sp: round((wc / total_words) * 100, 1)
                                for sp, wc in participation.items()
                            }
        except Exception as e:
            logger.error(
                "Failed to simulate dashboard data preparation for session %s: %s",
                session_id[:8],
                e,
            )

        # ── Profile logging & cleanup ──────────────────────────────────────────
        profiler = get_profiler(session_id)
        if profiler:
            profiler.log_results()
            try:
                total_time = (time.perf_counter() - profiler.start_time) * 1000
                async with AsyncSessionLocal() as db:
                    await crud.save_session_metrics_batch(
                        db,
                        session_id,
                        [
                            {
                                "metric_name": "performance_profile",
                                "metric_value": {
                                    "timings": profiler.timings,
                                    "total_time_ms": total_time,
                                },
                            }
                        ],
                    )
                    await db.commit()
            except Exception as pe:
                logger.error("Failed to save performance profile to DB: %s", pe)
            unregister_profiler(session_id)

    except Exception:  # noqa: BLE001
        logger.exception(
            "post_session_diarizer — session %s: unhandled error",
            session_id[:8],
        )
        try:
            await _set_attribution_status(session_id, "failed")
        except Exception:  # noqa: BLE001
            pass  # best-effort: status may already be inconsistent


# ── Synchronous Pyannote execution (runs in thread executor) ──────────────────


def _run_pyannote_sync(
    audio_file_path: str,
    session_id: str,
) -> list[tuple[float, float, str]] | None:
    """
    Run Pyannote speaker diarization on the full WAV file.

    This is a blocking function — it MUST be called via run_in_executor().

    Returns:
        List of (start_sec, end_sec, speaker_label) tuples,
        or None if diarization failed.
    """
    try:
        import warnings
        import os

        hf_token = os.environ.get("HF_TOKEN")
        if not hf_token:
            logger.warning(
                "post_session_diarizer — session %s: HF_TOKEN not set, "
                "cannot run post-session diarization",
                session_id[:8],
            )
            return None

        t0 = time.monotonic()
        logger.info(
            "post_session_diarizer — session %s: running Pyannote on %s …",
            session_id[:8],
            audio_file_path,
        )

        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message=".*torchcodec is not installed correctly.*",
                category=UserWarning,
            )
            import wave

            import numpy as np
            import torch

            logger.info(
                "post_session_diarizer — session %s: pre-loading WAV file using wave module",  # noqa: E501
                session_id[:8],
            )
            with wave.open(audio_file_path, "rb") as w:
                params = w.getparams()
                nchannels, sampwidth, framerate, nframes = params[:4]
                raw_bytes = w.readframes(nframes)

            audio_int16 = np.frombuffer(raw_bytes, dtype=np.int16)
            if nchannels > 1:
                audio_int16 = (
                    audio_int16.reshape(-1, nchannels).mean(axis=1).astype(np.int16)
                )

            audio_float32 = audio_int16.astype(np.float32) / 32768.0
            audio_tensor = torch.from_numpy(audio_float32).unsqueeze(0)

            waveform = {"waveform": audio_tensor, "sample_rate": framerate}
            logger.info(
                "post_session_diarizer — session %s: waveform pre-loaded (channels=%d, sample_rate=%d, duration=%.2fs)",  # noqa: E501
                session_id[:8],
                nchannels,
                framerate,
                len(audio_int16) / framerate,
            )

            from pyannote.audio import Pipeline
            
            logger.info("post_session_diarizer — session %s: Loading offline pipeline", session_id[:8])
            pipeline = Pipeline.from_pretrained(
                "pyannote/speaker-diarization-3.1",
                token=hf_token,
            )
            device = "cuda" if torch.cuda.is_available() else "cpu"
            pipeline.to(torch.device(device))
            
            # OPTIMIZATION: Set batch size to 32 for maximum throughput.
            # Stride remains 0.1 (default) to preserve SCDR accuracy.
            pipeline.segmentation_batch_size = 32

            with torch.inference_mode():
                diarization = pipeline(
                    waveform,
                    num_speakers=2,
                )

        # Unwrap DiarizeOutput wrapper if present (pyannote-audio 4.x) using duck-typing
        # to bypass class-identity mismatches under Uvicorn reload environments.
        annotation = getattr(diarization, "speaker_diarization", diarization)

        turns: list[tuple[float, float, str]] = []
        for turn, _, speaker in annotation.itertracks(yield_label=True):
            # Map "SPEAKER_00" → "Speaker 1", "SPEAKER_01" → "Speaker 2", etc.
            mapped = speaker
            if speaker.startswith("SPEAKER_"):
                try:
                    num = int(speaker.split("_")[-1])
                    mapped = f"Speaker {num + 1}"
                except (ValueError, IndexError):
                    pass
            turns.append((turn.start, turn.end, mapped))

        elapsed = time.monotonic() - t0
        unique_speakers = len({s for _, _, s in turns})
        logger.info(
            "post_session_diarizer — session %s: Pyannote finished in %.1fs — "
            "detected %d speaker(s), %d turn(s)",
            session_id[:8],
            elapsed,
            unique_speakers,
            len(turns),
        )
        return turns

    except Exception as exc:
        logger.error(
            "post_session_diarizer — session %s: Pyannote error — %s",
            session_id[:8],
            exc,
            exc_info=True,
        )
        return None


# ── DB helpers ────────────────────────────────────────────────────────────────


async def _set_attribution_status(session_id: str, status: str) -> None:
    """Update speaker_attribution_status on the session row and commit."""
    try:
        from db import crud
        from db.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            await crud.update_session_speaker_attribution_status(db, session_id, status)
            await db.commit()

        # Synchronise memory state
        from ws.session_manager import get_session_manager

        manager = get_session_manager()
        session = manager.get(session_id)
        if session:
            session.speaker_attribution_status = status

        logger.info(
            "speaker attribution status=%s session=%s",
            status,
            session_id,
        )
        logger.debug(
            "post_session_diarizer — session %s: attribution status → %s",
            session_id[:8],
            status,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "post_session_diarizer — session %s: failed to set status=%s",
            session_id[:8],
            status,
        )


async def _apply_speaker_updates(
    session_id: str,
    turns: list[tuple[float, float, str]],
) -> dict:
    """
    Fetch all transcript segments for the session, compute the best speaker
    for each using a two-stage algorithm, then batch-update speaker_id.

    Stage 1 — winner-take-all overlap: the Pyannote turn with the greatest
    temporal overlap with the segment wins.

    Stage 2 — nearest-turn proximity: when no overlap exists (segment falls
    in a gap between Pyannote turns), assign the turn whose nearest boundary
    is temporally closest to the segment.  This handles timestamp drift
    between Whisper and Pyannote and short gap intervals.

    Returns a dict with:
        segments_updated  int  — number of rows whose speaker_id changed
        total_segments    int  — total number of transcript segments in DB
        overlap_count     int  — segments resolved by overlap
        proximity_count   int  — segments resolved by proximity fallback
    """
    if not turns:
        logger.info(
            "post_session_diarizer — session %s: no speaker turns detected, "
            "speaker_id fields unchanged",
            session_id[:8],
        )
        return {
            "segments_updated": 0,
            "total_segments": 0,
            "overlap_count": 0,
            "proximity_count": 0,
        }

    from db import crud
    from db.database import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        segments = await crud.get_all_transcript_segments(db, session_id)
        total = len(segments)

        if not segments:
            logger.info(
                "post_session_diarizer — session %s: no transcript segments in DB",
                session_id[:8],
            )
            return {
                "segments_updated": 0,
                "total_segments": 0,
                "overlap_count": 0,
                "proximity_count": 0,
            }

        speaker_updates: list[dict] = []
        overlap_count = 0
        proximity_count = 0

        logger.debug(
            "post_session_diarizer — session %s: matching %d segment(s) against "
            "%d Pyannote turn(s)",
            session_id[:8],
            total,
            len(turns),
        )

        for seg in segments:
            new_speaker, reason, quality = _find_best_speaker(
                seg.start_time, seg.end_time, turns
            )

            if reason.startswith("overlap"):
                overlap_count += 1
                logger.debug(
                    "  MATCHED  seg=%-4s [%6.2f-%6.2f] → %-12s | %s",
                    seg.id,
                    seg.start_time,
                    seg.end_time,
                    new_speaker,
                    reason,
                )
            elif reason.startswith("nearest"):
                proximity_count += 1
                logger.debug(
                    "  PROXIM   seg=%-4s [%6.2f-%6.2f] → %-12s | %s",
                    seg.id,
                    seg.start_time,
                    seg.end_time,
                    new_speaker,
                    reason,
                )
            else:
                logger.debug(
                    "  UNMATCH  seg=%-4s [%6.2f-%6.2f] → %-12s | %s",
                    seg.id,
                    seg.start_time,
                    seg.end_time,
                    new_speaker,
                    reason,
                )

            if new_speaker != seg.speaker_id:
                speaker_updates.append(
                    {
                        "segment_id": seg.id,
                        "speaker": new_speaker,
                    }
                )

        logger.info(
            "post_session_diarizer — session %s: assignment summary — "
            "overlap=%d, proximity=%d, unmatched=%d (total=%d)",
            session_id[:8],
            overlap_count,
            proximity_count,
            total - overlap_count - proximity_count,
            total,
        )

        if not speaker_updates:
            logger.info(
                "post_session_diarizer — session %s: all %d segment(s) already have "
                "correct speaker labels — no updates needed",
                session_id[:8],
                total,
            )
            return {
                "segments_updated": 0,
                "total_segments": total,
                "overlap_count": overlap_count,
                "proximity_count": proximity_count,
            }

        with profile_stage(session_id, "Database writes"):
            count = await crud.update_segment_speakers(db, session_id, speaker_updates)
            await db.commit()

    logger.info(
        "post_session_diarizer — session %s: updated %d / %d segment speaker labels",
        session_id[:8],
        count,
        total,
    )
    return {
        "segments_updated": count,
        "total_segments": total,
        "overlap_count": overlap_count,
        "proximity_count": proximity_count,
    }


async def _persist_attribution_diagnostics(
    session_id: str,
    diagnostics: dict,
) -> None:
    """
    Persist speaker attribution quality diagnostics into the session_metrics
    JSONB table as a single row with metric_name="speaker_attribution".

    Stored fields:
        speakers_detected   int   — distinct speaker labels assigned
        speaker_turns       int   — total diarization turn intervals
        segments_updated    int   — transcript segments re-labelled
        total_segments      int   — total transcript segments in DB
        coverage_percent    float — segments_updated / total_segments * 100

    No schema changes required — uses the existing session_metrics table.
    """
    try:
        from db import crud
        from db.database import AsyncSessionLocal

        async with AsyncSessionLocal() as db:
            with profile_stage(session_id, "Database writes"):
                await crud.save_session_metrics_batch(
                    db,
                    session_id,
                    [
                        {
                            "metric_name": "speaker_attribution",
                            "metric_value": diagnostics,
                        }
                    ],
                )
                await db.commit()

        logger.info(
            "post_session_diarizer — session %s: attribution diagnostics persisted "
            "(speakers=%d, coverage=%.1f%%, updated=%d/%d)",
            session_id[:8],
            diagnostics.get("speakers_detected", 0),
            diagnostics.get("coverage_percent", 0.0),
            diagnostics.get("segments_updated", 0),
            diagnostics.get("total_segments", 0),
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "post_session_diarizer — session %s: failed to persist attribution diagnostics",  # noqa: E501
            session_id[:8],
        )


def _find_best_speaker(
    seg_start: float,
    seg_end: float,
    turns: list[tuple[float, float, str]],
    fallback: str = "Speaker 1",
) -> tuple[str, str, float]:
    """
    Assign a speaker label to the transcript segment [seg_start, seg_end].

    Two-stage algorithm:

    Stage 1 — Winner-take-all overlap
        Iterate all Pyannote turns.  Compute the temporal overlap between the
        segment and each turn.  The turn with the greatest positive overlap
        wins.  Overlap = min(seg_end, turn_end) − max(seg_start, turn_start).

    Stage 2 — Nearest-turn proximity (gap fallback)
        If no turn overlaps the segment at all (segment falls in a Pyannote
        gap interval), assign the turn whose nearest boundary is temporally
        closest to the segment.  Distance is measured as the gap between the
        segment and the nearest turn edge:
            • if segment is AFTER the turn  → gap = seg_start − turn_end
            • if segment is BEFORE the turn → gap = turn_start − seg_end
        The turn with the smallest gap wins.  This gracefully handles:
            – Short silences between turns (Pyannote unlabelled intervals)
            – Timestamp drift between Whisper and Pyannote
            – Very short segments (<0.5 s) that Pyannote groups differently

    Returns:
        (speaker_label, reason_string, quality_metric)
        reason_string is one of:
            "overlap(Xs,Y%)"   — resolved by Stage 1
            "nearest(gap=Xs)" — resolved by Stage 2
            "no_turns"         — turns list was empty (should never reach here)
    """
    if not turns:
        return fallback, "no_turns", 0.0

    # ── Stage 1: winner-take-all overlap ────────────────────────────────────
    best_speaker: str | None = None
    best_overlap: float = 0.0

    for turn_start, turn_end, speaker in turns:
        overlap = min(seg_end, turn_end) - max(seg_start, turn_start)
        if overlap > best_overlap:
            best_overlap = overlap
            best_speaker = speaker

    if best_speaker is not None:
        seg_dur = max(seg_end - seg_start, 1e-6)
        overlap_pct = round(best_overlap / seg_dur * 100, 1)
        return (
            best_speaker,
            f"overlap({best_overlap:.2f}s,{overlap_pct}%)",
            best_overlap,
        )

    # ── Stage 2: nearest-turn proximity fallback ─────────────────────────────
    # No turn overlaps this segment — find the nearest turn by boundary gap.
    nearest_speaker: str | None = None
    nearest_gap: float = float("inf")

    for turn_start, turn_end, speaker in turns:
        if seg_start >= turn_end:
            # segment is fully after this turn
            gap = seg_start - turn_end
        elif seg_end <= turn_start:
            # segment is fully before this turn
            gap = turn_start - seg_end
        else:
            # Positive overlap — should have been caught in Stage 1.
            # Guard against float rounding: treat as zero gap.
            gap = 0.0

        if gap < nearest_gap:
            nearest_gap = gap
            nearest_speaker = speaker

    if nearest_speaker is not None:
        return nearest_speaker, f"nearest(gap={nearest_gap:.2f}s)", nearest_gap

    return fallback, "no_turns", 0.0
