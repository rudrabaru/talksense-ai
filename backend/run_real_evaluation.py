import asyncio
import json
import os
import subprocess

from audio.diarizer import get_diarizer
from audio.transcriber import get_transcriber
from core.config import get_settings
from engine.conversation_engine import ConversationState, get_conversation_engine
from evaluate_speaker_accuracy import Segment as EvalSegment
from evaluate_speaker_accuracy import (
    compute_accuracy,
    compute_precision_recall_f1,
    compute_scdr,
    load_ground_truth,
    match_segments,
    resolve_label_mapping,
)
from services.nlp_engine import get_nlp_engine

SAMPLE_RATE = 16000
CHUNK_DURATION = 5.0  # seconds
CHUNK_SIZE = int(SAMPLE_RATE * 2 * CHUNK_DURATION)  # 2 bytes per sample


async def run_pipeline():
    print("Loading settings...")
    settings = get_settings()

    print(f"Loading Whisper model ({settings.whisper_model})...")
    transcriber = get_transcriber()
    transcriber.load(
        settings.whisper_model, settings.whisper_compute_type, settings.whisper_device
    )

    print("Loading Pyannote Diarizer...")
    diarizer = get_diarizer()
    diarizer.load(settings.hf_token, settings.pyannote_device)

    print("Loading NLP Engine...")
    nlp = get_nlp_engine()

    audio_path = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__), "..", "sample_audio", "meeting_short.mp3"
        )
    )
    print(f"Decoding audio: {audio_path}")

    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        audio_path,
        "-f",
        "s16le",
        "-ac",
        "1",
        "-ar",
        str(SAMPLE_RATE),
        "-",
    ]

    process = subprocess.Popen(
        ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )

    audio_data = process.stdout.read()
    process.wait()

    print(f"Decoded {len(audio_data)} bytes of PCM audio.")

    all_diarized_segments = []

    # Process in chunks to simulate real-time WebSocket stream
    offset_bytes = 0
    time_offset = 0.0
    prev_speaker = "Speaker 1"

    conversation = ConversationState()
    engine = get_conversation_engine()

    print("Running audio pipeline...")
    while offset_bytes < len(audio_data):
        chunk = audio_data[offset_bytes : offset_bytes + CHUNK_SIZE]

        # Whisper transcription
        raw_segments = transcriber.transcribe(chunk, time_offset=time_offset)

        if raw_segments:
            # Diarization
            diarized = diarizer.assign_speakers(
                raw_segments, chunk, time_offset, prev_speaker
            )
            if diarized:
                prev_speaker = diarized[-1].speaker

            # NLP Enrichment
            raw_dicts = [
                {"text": s.text, "start": s.start, "end": s.end} for s in diarized
            ]
            enriched = await asyncio.get_running_loop().run_in_executor(
                None, nlp.enrich_transcript, raw_dicts
            )

            for i, seg in enumerate(diarized):
                if i < len(enriched):
                    seg.__dict__.update(
                        {
                            "sentiment": enriched[i].get("sentiment", 0.0),
                            "sentiment_label": enriched[i].get(
                                "sentiment_label", "Neutral"
                            ),
                        }
                    )
                all_diarized_segments.append(seg)
                conversation.transcript_segments.append(seg.__dict__)

            # Run ConversationEngine metrics
            conversation, _ = engine.process_segments(
                diarized, conversation, mode="meeting"
            )

        offset_bytes += len(chunk)
        time_offset += (len(chunk) / 2) / SAMPLE_RATE

    print(f"Pipeline finished. Found {len(all_diarized_segments)} segments.")
    for s in all_diarized_segments:
        print(f"  [{s.start:.2f} - {s.end:.2f}] {s.speaker}: {s.text}")

    print("\nEvaluating against ground truth...")
    gt_path = os.path.join(
        os.path.dirname(__file__), "ground_truth", "meeting_short_gt.json"
    )
    annotated_segs, metadata = load_ground_truth(gt_path)

    # Convert DiarizedSegment to EvalSegment
    predicted_segs = [
        EvalSegment(start=s.start, end=s.end, speaker=s.speaker, text=s.text)
        for s in all_diarized_segments
    ]

    pairs = match_segments(predicted_segs, annotated_segs, min_overlap_ratio=0.10)
    label_map = resolve_label_mapping(pairs)
    accuracy, correct, total_matched = compute_accuracy(pairs, label_map)
    per_speaker = compute_precision_recall_f1(pairs, label_map)
    scdr, scdr_detected, scdr_total = compute_scdr(
        predicted_segs, annotated_segs, label_map
    )
    macro_f1 = (
        sum(v["f1"] for v in per_speaker.values()) / len(per_speaker)
        if per_speaker
        else 0.0
    )

    print("\n--- ATTRIBUTION ACCURACY ---")
    print(f"Segments Matched: {len(pairs)} / {len(annotated_segs)}")
    print(f"Accuracy: {accuracy:.1f}% ({correct}/{total_matched})")
    print(f"Macro F1: {macro_f1:.3f}")
    print(f"SCDR:     {scdr:.1f}% ({scdr_detected}/{scdr_total})")

    print("\n--- NLP METRICS ---")
    print(f"Health Score: {conversation.health_score}")
    print(f"Sentiment: {conversation.sentiment} ({conversation.sentiment_score:.2f})")
    print(f"Speaking Ratio: {conversation.speaking_ratio}")
    print(f"Objections Detected: {len(conversation.objections)}")
    print(f"Buying Signals Detected: {len(conversation.buying_signals)}")
    print(f"Roles: {conversation.participation}")

    # Write full JSON output to consume later
    output = {
        "attribution": {"accuracy": accuracy, "macro_f1": macro_f1, "scdr": scdr},
        "nlp": {
            "health_score": conversation.health_score,
            "sentiment": conversation.sentiment,
            "sentiment_score": conversation.sentiment_score,
            "speaking_ratio": conversation.speaking_ratio,
            "objections": conversation.objections,
            "buying_signals": conversation.buying_signals,
            "participation": conversation.participation,
        },
    }

    with open("real_evaluation_results.json", "w") as f:
        json.dump(output, f, indent=2)


if __name__ == "__main__":
    asyncio.run(run_pipeline())
