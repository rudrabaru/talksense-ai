import os
import sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from ws.audio_handler import _merge_overlapping_text


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


if __name__ == "__main__":
    test_transcript_merge()
    print("Transcript merge tests passed!")
