from services.word_speaker_aligner import align_words_to_speakers


def test_align_perfect_overlap():
    words = [
        {"word": "hello", "start": 0.0, "end": 0.5, "probability": 0.9},
        {"word": "world", "start": 0.5, "end": 1.0, "probability": 0.9},
    ]
    speaker_segments = [(0.0, 1.0, "Speaker A")]

    aligned = align_words_to_speakers(words, speaker_segments)

    assert len(aligned) == 2
    assert aligned[0]["speaker"] == "Speaker A"
    assert aligned[1]["speaker"] == "Speaker A"


def test_align_speaker_switch_mid_sentence():
    words = [
        {"word": "hello", "start": 0.0, "end": 0.5},
        {"word": "yes", "start": 0.6, "end": 1.0},
        {"word": "world", "start": 1.1, "end": 1.5},
    ]
    # Speaker A speaks 0-0.6, Speaker B interrupts 0.6-1.0, Speaker A continues 1.0-1.5
    speaker_segments = [
        (0.0, 0.6, "Speaker A"),
        (0.6, 1.0, "Speaker B"),
        (1.0, 1.5, "Speaker A"),
    ]

    aligned = align_words_to_speakers(words, speaker_segments)

    assert aligned[0]["speaker"] == "Speaker A"
    assert aligned[1]["speaker"] == "Speaker B"
    assert aligned[2]["speaker"] == "Speaker A"


def test_align_out_of_bounds_nearest_fallback():
    words = [
        {"word": "hello", "start": 0.0, "end": 0.5},
        {"word": "world", "start": 2.0, "end": 2.5},
    ]
    # Segment misses the first word completely, and is far from the second word
    speaker_segments = [(1.0, 1.5, "Speaker B")]

    aligned = align_words_to_speakers(words, speaker_segments)

    # "hello" nearest to 1.0 -> Speaker B
    # "world" nearest to 1.5 -> Speaker B
    assert aligned[0]["speaker"] == "Speaker B"
    assert aligned[1]["speaker"] == "Speaker B"


def test_align_empty_inputs():
    assert align_words_to_speakers([], [(0, 1, "Speaker A")]) == []

    words = [{"word": "hello", "start": 0, "end": 1}]
    aligned = align_words_to_speakers(words, [])
    assert aligned[0]["speaker"] == "Speaker 1"  # default fallback
