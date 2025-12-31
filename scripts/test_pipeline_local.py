import sys
import os
import json

# Add backend to sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "../backend"))

from services.speech_to_text import transcribe_audio
from services.nlp_engine import enrich_transcript
from services.context_analyzer import analyze_meeting

def test_pipeline():
    audio_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "../sample_audio/BuisinessMeeting.mp3"))
    
    if not os.path.exists(audio_path):
        print(f"File not found: {audio_path}")
        return

    print(f"--- 1. Transcribing {audio_path} ---")
    # Note: This might take time on CPU
    transcript = transcribe_audio(audio_path)
    print("Transcription complete. Text length:", len(transcript["text"]))

    print("\n--- 2. Enriching with NLP ---")
    enriched = enrich_transcript(transcript)
    print("Enrichment complete.")
    print("First segment sentiment:", enriched["segments"][0].get("sentiment"))
    
    print("\n--- 3. Context Analysis (Meeting Mode) ---")
    insights = analyze_meeting(enriched)
    
    print("\n--- RESULTS ---")
    print(json.dumps(insights, indent=2))

if __name__ == "__main__":
    test_pipeline()
