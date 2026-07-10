import numpy as np
import pytest
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ws.audio_handler import _merge_overlapping_text
from audio.speaker_profile import SpeakerProfile

def test_transcript_merge():
    # 1. Punctuation differences
    t1 = "Hello, world."
    t2 = "world How are you"
    assert _merge_overlapping_text(t1, t2) == "Hello, world. How are you"

    # 2. Casing differences
    t1 = "Hello World"
    t2 = "WORLD how are you"
    assert _merge_overlapping_text(t1, t2) == "Hello World how are you"

    # 3. Repeated words (false positive check)
    t1 = "Right right"
    t2 = "right"
    # overlap is 1 word, "right" -> "Right right"
    assert _merge_overlapping_text(t1, t2) == "Right right"

    # 4. Partial overlap
    t1 = "Let's discuss the"
    t2 = "discuss the new features."
    assert _merge_overlapping_text(t1, t2) == "Let's discuss the new features."

    # 5. No overlap
    t1 = "I am speaking."
    t2 = "And then I continued."
    assert _merge_overlapping_text(t1, t2) == "I am speaking. And then I continued."

def test_speaker_profile():
    profile = SpeakerProfile()
    
    # Same speaker (very high sim)
    emb1 = np.array([0.1, 0.2, 0.3, 0.4])
    emb2 = np.array([0.1, 0.21, 0.29, 0.41])  # Close to emb1
    
    spk1 = profile.match_or_create(emb1)
    spk2 = profile.match_or_create(emb2)
    assert spk1 == spk2, f"Should match same speaker, got {spk1} and {spk2}"
    
    # Different speaker (low sim)
    emb3 = np.array([-0.5, 0.8, -0.1, 0.1])
    spk3 = profile.match_or_create(emb3)
    assert spk3 != spk1, f"Should be different speakers, got {spk3} and {spk1}"
    
    # Borderline similarity (~0.4 - 0.5)
    v1 = np.array([1.0, 0.0])
    v2 = np.array([0.5, 0.866]) # sim = 0.5
    
    profile2 = SpeakerProfile()
    s1 = profile2.match_or_create(v1)
    s2 = profile2.match_or_create(v2)
    # Since threshold is 0.55, this 0.5 sim should NOT match, creating a new speaker.
    assert s1 != s2, f"Borderline (0.5) should not match at threshold 0.55"

    v3 = np.array([0.6, 0.8]) # sim = 0.6
    s3 = profile2.match_or_create(v3)
    # Since threshold is 0.55, 0.6 sim SHOULD match s1 or s2
    assert s3 in [s1, s2], "Should match existing speaker"

if __name__ == "__main__":
    test_transcript_merge()
    print("Transcript merge tests passed!")
    test_speaker_profile()
    print("Speaker profile tests passed!")
