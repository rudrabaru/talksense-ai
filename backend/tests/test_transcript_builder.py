import pytest
from services.transcript_builder import build_transcript_string, _estimate_tokens

def test_empty_transcript():
    assert build_transcript_string([]) == ""

def test_single_segment():
    segments = [{"start_time": 15.5, "text": "Hello world"}]
    expected = "[00:15] System: Hello world"
    assert build_transcript_string(segments) == expected

def test_multiple_segments_ordering():
    segments = [
        {"start_time": 20.0, "text": "Second"},
        {"start_time": 5.0, "text": "First"},
    ]
    expected = "[00:05] System: First\n[00:20] System: Second"
    assert build_transcript_string(segments) == expected

def test_timestamp_formatting():
    segments = [{"start_time": 65.1, "text": "Over a minute"}]
    expected = "[01:05] System: Over a minute"
    assert build_transcript_string(segments) == expected

def test_token_truncation():
    # 1 token = 4 chars roughly. max_tokens = 100 means max_chars = 400
    long_text = "A" * 500
    segments = [{"start_time": 0.0, "text": long_text}]
    
    # Should trigger truncation
    result = build_transcript_string(segments, max_tokens=100)
    
    assert "[TRANSCRIPT TRUNCATED DUE TO LENGTH]" in result
    # It should preserve the start and end portions
    assert result.startswith("[00:00] System: " + ("A" * 64)) # roughly 20% of 400 chars is 80 chars, minus the prefix length
    # And end with A's
    assert result.endswith("A")
