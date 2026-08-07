import asyncio
import logging
from pydantic import ValidationError
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from sqlalchemy.ext.asyncio import AsyncSession
import time

from core.config import get_settings
from db.database import AsyncSessionLocal
from db import crud
from services.transcript_builder import build_transcript_string
from services.prompt_loader import load_prompt_bundle
from services.response_validator import validate_and_parse
from services.llm_engine import (
    LLMEngine, 
    ProviderTimeoutError, 
    RateLimitError, 
    ProviderUnavailableError
)

logger = logging.getLogger(__name__)

# Global concurrency guard
_LLM_SEMAPHORE = asyncio.Semaphore(20)

def _generate_fallback() -> dict:
    """Generate deterministic fallback JSON on total failure."""
    return {
        "executive_summary": "AI summary unavailable.",
        "decisions": [],
        "action_items": []
    }

# Retry strategy: up to 2 retries (3 attempts total) with exponential backoff.
# Only retry transient provider errors and JSON extraction/validation errors.
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((
        ProviderTimeoutError,
        RateLimitError,
        ProviderUnavailableError,
        ValidationError,
        ValueError  # Thrown by validator if JSON is missing or malformed
    )),
    reraise=True
)
async def _generate_and_validate_with_retries(
    engine: LLMEngine,
    system_prompt: str,
    user_prompt: str,
    schema: dict
) -> dict:
    
    # Concurrency control for API usage
    async with _LLM_SEMAPHORE:
        raw_response = await engine.generate_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            schema=schema
        )
        
        # Validation
        validated_dict = validate_and_parse(raw_response)
        return validated_dict


async def run_post_session_pipeline(session_id: str) -> None:
    """
    Coordinates the entire Post-Session AI workflow.
    """
    print("TRACE: run_post_session_pipeline() starts")
    settings = get_settings()
    if not settings.enable_post_session_ai:
        logger.info(f"Post-Session AI is disabled via config. Skipping pipeline for {session_id[:8]}")
        return

    logger.info(f"Starting post-session pipeline for {session_id[:8]}")
    
    logger.info({
        "event": "pipeline_step",
        "step": "started",
        "session_id": session_id,
        "success": True
    })
    
    print("TRACE: AsyncSessionLocal created")
    # 1. Database scope
    async with AsyncSessionLocal() as db:
        try:
            print("TRACE: transcript fetch started")
            # 2. Fetch transcript segments
            # limit=100000 ensures we get the entire meeting
            db_segments = await crud.get_transcript_segments(db, session_id, limit=100000)
            if not db_segments:
                logger.info(f"No transcript segments found for {session_id[:8]}. Skipping post-session AI.")
                return
                
            from audio.offline_diarizer import run_offline_diarization
            from services.alignment import WordAligner, SpeakerCleanup
            from audio.buffer import _ensure_audio_dir
            import os

            audio_dir = _ensure_audio_dir()
            wav_path = os.path.join(audio_dir, f"session_{session_id}.wav")
            
            diart_intervals = []
            if os.path.exists(wav_path):
                logger.info({
                    "event": "pipeline_step",
                    "step": "offline_diarization",
                    "session_id": session_id,
                    "wav_path": wav_path
                })
                diart_start = time.monotonic()
                diart_intervals = await asyncio.to_thread(run_offline_diarization, wav_path)
                logger.info({
                    "event": "pipeline_step_complete",
                    "step": "offline_diarization",
                    "session_id": session_id,
                    "duration_ms": (time.monotonic() - diart_start) * 1000,
                    "success": True
                })
            else:
                logger.warning(f"Audio file {wav_path} not found. Proceeding without diarization.")
            
            logger.info("Aligning words with Pyannote intervals...")
            align_start = time.monotonic()
            aligned_words = WordAligner.align_words(db_segments, diart_intervals)
            processed_segments = SpeakerCleanup.process(aligned_words)
            logger.info({
                "event": "pipeline_step_complete",
                "step": "alignment",
                "session_id": session_id,
                "duration_ms": (time.monotonic() - align_start) * 1000,
                "success": True
            })
            
            # 3. Build transcript string from processed segments
            print("TRACE: building transcript string")
            transcript_string = ""
            for seg in processed_segments:
                transcript_string += f"{seg['speaker']} ({seg['start']:.1f}-{seg['end']:.1f}): {seg['text']}\n"

            if not transcript_string:
                logger.info(f"Transcript string built empty for {session_id[:8]}. Skipping.")
                return

            # 4. Load prompts
            print("TRACE: load_prompt_bundle() called")
            bundle = load_prompt_bundle(settings.post_session_prompt_version)
            system_prompt = bundle["system_prompt"]
            user_prompt_template = bundle["user_prompt"]
            schema = bundle["schema"]
            
            # Transcript Size Protection (Phase 66)
            MAX_TRANSCRIPT_CHARS = 100_000
            if len(transcript_string) > MAX_TRANSCRIPT_CHARS:
                logger.warning(f"Session {session_id[:8]} transcript exceeded {MAX_TRANSCRIPT_CHARS} chars. Truncating.")
                transcript_string = transcript_string[-MAX_TRANSCRIPT_CHARS:]
                transcript_string = "[...TRUNCATED...] " + transcript_string

            final_user_prompt = f"{user_prompt_template}\n\n{transcript_string}"

            # 5 & 6. Call LLM Engine and Validate (with retries)
            engine = LLMEngine()
            
            gemini_start_time = time.monotonic()
            
            try:
                print("TRACE: LLMEngine.generate_json() calling logic started")
                parsed_json = await asyncio.wait_for(
                    _generate_and_validate_with_retries(
                        engine,
                        system_prompt,
                        final_user_prompt,
                        schema
                    ),
                    timeout=30.0
                )
                print("TRACE: validate_and_parse() succeeds")
                validation_success = True
                fallback_used = False
                
            except Exception as e:
                logger.error(f"Post-Session AI pipeline failed completely after retries for {session_id[:8]}: {str(e)}")
                # 7. Fallback Generation
                parsed_json = _generate_fallback()
                validation_success = False
                fallback_used = True
            
            gemini_latency = (time.monotonic() - gemini_start_time) * 1000
            logger.info(f"[METRIC] Gemini Post-Session Latency: {gemini_latency:.2f}ms | Fallback: {fallback_used}")

            # 7.5 Transform Arrays back to Maps for internal usage
            raw_speaker_map = parsed_json.get("speaker_map", [])
            raw_roles = parsed_json.get("roles", [])
            
            if isinstance(raw_speaker_map, list):
                parsed_json["speaker_map"] = {item.get("segment_id"): item.get("speaker") for item in raw_speaker_map if "segment_id" in item}
            if isinstance(raw_roles, list):
                parsed_json["roles"] = {item.get("speaker"): item.get("role") for item in raw_roles if "speaker" in item}

            # 8. Calculate Speaking Ratio based on Pyannote processed segments
            speaker_word_counts = {}
            total_words = 0
            for seg in processed_segments:
                words_count = len(seg.get("words", []))
                if words_count == 0:
                    continue
                speaker = seg["speaker"]
                speaker_word_counts[speaker] = speaker_word_counts.get(speaker, 0) + words_count
                total_words += words_count
                
            speaking_ratio = {
                speaker: (count / total_words) if total_words > 0 else 0
                for speaker, count in speaker_word_counts.items()
            }
            parsed_json["speaking_ratio"] = speaking_ratio

            # 9. Persist JSON and Processed Transcript
            print("TRACE: crud.save_analysis_result() called")
            await crud.save_analysis_result(
                db, 
                session_id, 
                health_score=None, 
                summary=parsed_json.get("executive_summary", ""),
                report_json=parsed_json,
                processed_transcript=processed_segments
            )
            
            import uuid
            from db.models import Session
            db_session = await db.get(Session, uuid.UUID(session_id))
            if db_session:
                db_session.status = "completed"
                db_session.speaker_attribution_status = "completed"

            # Explicit commit for the pipeline
            print("TRACE: db.commit() called")
            await db.commit()

            print("TRACE: pipeline completed")
            # 9. Structured Telemetry
            logger.info(
                "Post-Session Pipeline Completed",
                extra={
                    "event": "post_session_pipeline_complete",
                    "session_id": session_id,
                    "provider": settings.post_session_provider,
                    "model": settings.post_session_model,
                    "validation_success": validation_success,
                    "fallback_used": fallback_used
                }
            )

        except Exception as e:
            # Global catch to ensure we don't crash any background task runner
            # and to guarantee rollback
            await db.rollback()
            logger.exception(f"Unexpected fatal error in post-session pipeline for {session_id[:8]}: {str(e)}")
            
            import uuid
            from db.models import Session
            try:
                async with AsyncSessionLocal() as failure_db:
                    db_session = await failure_db.get(Session, uuid.UUID(session_id))
                    if db_session:
                        # Graceful degradation: session is complete, but AI failed
                        db_session.status = "completed"
                        db_session.speaker_attribution_status = "failed"
                        await failure_db.commit()
            except Exception as nested_e:
                logger.error(f"Failed to update session status to failed: {nested_e}")
