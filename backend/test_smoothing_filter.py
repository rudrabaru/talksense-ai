from services.word_speaker_aligner import align_words_to_speakers


def run_test(name, words, segments, expected_outcome):
    print(f"\n--- {name} ---")

    # 1. Raw word-level alignment (No smoothing)
    # Monkeypatch os.environ
    import os

    os.environ["DISABLE_5_WORD_SMOOTHING"] = "1"
    raw_aligned = align_words_to_speakers(words, segments)

    # 2. Smoothed word-level alignment
    os.environ["DISABLE_5_WORD_SMOOTHING"] = "0"
    smoothed_aligned = align_words_to_speakers(words, segments)

    print("WORDS:")
    print(" ".join(w["word"] for w in words))

    print("\nRAW ALIGNMENT (No Smoothing):")
    raw_spk = [w["speaker"] for w in raw_aligned]
    print(raw_spk)

    print("\nSMOOTHED ALIGNMENT (5-Word Window):")
    smoothed_spk = [w["speaker"] for w in smoothed_aligned]
    print(smoothed_spk)

    if raw_spk != smoothed_spk:
        print("\n[!] SMOOTHING CHANGED THE RESULT")
        print(f"Expected: {expected_outcome}")
    else:
        print("\n[=] No change from smoothing")


# Test 1: Rapid Pyannote Jitter (The bug we tried to fix)
# A single word gets misattributed to B in the middle of an A sentence.
words_1 = [
    {"word": "I", "start": 1.0, "end": 1.2},
    {"word": "think", "start": 1.2, "end": 1.4},
    {"word": "that", "start": 1.4, "end": 1.6},  # Jitter here
    {"word": "is", "start": 1.6, "end": 1.8},
    {"word": "great.", "start": 1.8, "end": 2.0},
]
segs_1 = [
    (1.0, 1.4, "Speaker 1"),
    (1.4, 1.6, "Speaker 2"),  # Pyannote hallucinated a blip
    (1.6, 2.0, "Speaker 1"),
]
run_test(
    "Test 1: Pyannote Jitter Filter (A -> B -> A)",
    words_1,
    segs_1,
    "Smoothing SHOULD fix this (all Speaker 1)",
)

# Test 2: Legitimate short response ("yes", "okay", "exactly")
# Speaker 1 talks, Speaker 2 says "exactly", Speaker 1 continues.
words_2 = [
    {"word": "So", "start": 1.0, "end": 1.2},
    {"word": "we", "start": 1.2, "end": 1.4},
    {"word": "agree.", "start": 1.4, "end": 1.8},
    {"word": "Exactly.", "start": 2.0, "end": 2.5},  # Speaker 2
    {"word": "Moving", "start": 2.6, "end": 2.8},
    {"word": "on", "start": 2.8, "end": 3.0},
    {"word": "then.", "start": 3.0, "end": 3.5},
]
segs_2 = [
    (1.0, 1.8, "Speaker 1"),
    (2.0, 2.5, "Speaker 2"),  # Legitimate 1-word turn
    (2.6, 3.5, "Speaker 1"),
]
run_test(
    "Test 2: Legitimate 1-Word Turn (Backchannel)",
    words_2,
    segs_2,
    "Smoothing might ERASE the 'Exactly' (Danger!)",
)

# Test 3: Short 2-word interruption
words_3 = [
    {"word": "I", "start": 1.0, "end": 1.2},
    {"word": "was", "start": 1.2, "end": 1.4},
    {"word": "saying-", "start": 1.4, "end": 1.8},
    {"word": "No", "start": 1.8, "end": 2.0},  # Speaker 2
    {"word": "wait!", "start": 2.0, "end": 2.4},  # Speaker 2
    {"word": "Let", "start": 2.4, "end": 2.6},
    {"word": "me", "start": 2.6, "end": 2.8},
    {"word": "finish.", "start": 2.8, "end": 3.2},
]
segs_3 = [
    (1.0, 1.8, "Speaker 1"),
    (1.8, 2.4, "Speaker 2"),  # Legitimate 2-word turn
    (2.4, 3.2, "Speaker 1"),
]
run_test(
    "Test 3: Legitimate 2-Word Interruption",
    words_3,
    segs_3,
    "Smoothing might ERASE the interruption (Danger!)",
)
