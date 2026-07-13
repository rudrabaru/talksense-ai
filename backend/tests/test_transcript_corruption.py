import pytest
import numpy as np
from unittest.mock import AsyncMock, patch, MagicMock

from audio.transcriber import WhisperTranscriber, TranscriptSegment, TranscriptWord
from audio.diarizer import SpeakerDiarizer, DiarizedSegment
from audio.speaker_profile import SpeakerProfile
from audio.buffer import SAMPLE_RATE, OVERLAP_MS

@pytest.mark.asyncio
async def test_transcriber_filters_punctuation():
    """Verify that punctuation-only transcript segments are dropped."""
    transcriber = WhisperTranscriber()
    transcriber._loaded = True
    transcriber._model = MagicMock()
    
    # Mock whisper model returning a punctuation segment
    mock_segment = MagicMock()
    mock_segment.text = " . . . . _ _ "
    mock_segment.start = 0.0
    mock_segment.end = 1.0
    mock_segment.avg_logprob = -0.1
    mock_segment.words = []
    
    mock_info = MagicMock()
    mock_info.language = "en"
    
    transcriber._model.transcribe.return_value = ([mock_segment], mock_info)
    
    # Dummy PCM
    pcm_bytes = b'\x00' * 32000
    
    segments = transcriber.transcribe(pcm_bytes)
    assert len(segments) == 0, "Punctuation-only segments must be dropped"

@pytest.mark.asyncio
async def test_transcriber_tail_dropping():
    """Verify that is_partial correctly drops words in the overlap tail."""
    transcriber = WhisperTranscriber()
    transcriber._loaded = True
    transcriber._model = MagicMock()
    
    chunk_duration_sec = 2.0
    pcm_bytes = b'\x00' * int(chunk_duration_sec * SAMPLE_RATE * 2)
    time_offset = 0.0
    tail_start = chunk_duration_sec - (OVERLAP_MS / 1000.0) # 1.0s
    
    mock_segment = MagicMock()
    mock_segment.text = "Hello world from the tail."
    mock_segment.start = 0.0
    mock_segment.end = 1.5
    mock_segment.avg_logprob = -0.1
    
    w1 = MagicMock(word="Hello", start=0.1, end=0.5, probability=0.9)
    w2 = MagicMock(word=" world", start=0.5, end=0.9, probability=0.9)
    w3 = MagicMock(word=" from", start=1.1, end=1.3, probability=0.9) # In tail!
    w4 = MagicMock(word=" the tail.", start=1.3, end=1.5, probability=0.9) # In tail!
    
    mock_segment.words = [w1, w2, w3, w4]
    mock_info = MagicMock(language="en")
    
    transcriber._model.transcribe.return_value = ([mock_segment], mock_info)
    
    # Run with is_partial=True
    segments = transcriber.transcribe(pcm_bytes, time_offset, is_partial=True)
    
    assert len(segments) == 1
    assert segments[0].text == "Hello world"
    assert len(segments[0].words) == 2
    assert segments[0].end == 0.9
    
    # Run with is_partial=False
    segments_full = transcriber.transcribe(pcm_bytes, time_offset, is_partial=False)
    assert len(segments_full) == 1
    assert segments_full[0].text == "Hello world from the tail."
    assert len(segments_full[0].words) == 4

@pytest.mark.asyncio
async def test_diarizer_silence_overlap_gate():
    """Verify that Pyannote is only called on windows containing Whisper words."""
    diarizer = SpeakerDiarizer()
    diarizer._loaded = True
    diarizer._model = MagicMock()
    
    # Return a dummy embedding for any call
    mock_emb = np.zeros(256, dtype=np.float32)
    mock_tensor = MagicMock()
    mock_tensor.cpu.return_value.numpy.return_value = [mock_emb]
    diarizer._model.return_value = mock_tensor
    
    # Mock device
    import torch
    mock_param = MagicMock()
    mock_param.device = torch.device('cpu')
    diarizer._model.parameters.return_value = iter([mock_param])
    
    profile = SpeakerProfile()
    
    # Chunk is 2.0s long
    chunk_duration_sec = 2.0
    pcm_bytes = b'\x00' * int(chunk_duration_sec * SAMPLE_RATE * 2)
    
    # One whisper segment from 1.2 to 1.8 seconds
    # So windows before 1.2 shouldn't generate embeddings
    w1 = TranscriptWord(word="test", start=1.2, end=1.8, probability=0.9)
    seg = TranscriptSegment(start=1.2, end=1.8, text="test", words=[w1])
    
    diarizer._diarize_with_embeddings([seg], pcm_bytes, 0.0, "Speaker 1", profile)
    
    # Pyannote should only run for windows overlapping [1.2, 1.8]
    # Windows: [0.0, 1.0], [0.5, 1.5], [1.0, 2.0]
    # Overlaps: 
    # [0.0, 1.0] -> No
    # [0.5, 1.5] -> Yes (1.2 to 1.5 overlaps)
    # [1.0, 2.0] -> Yes
    # [1.5, 2.0] -> Yes (Length is 0.5s, valid window)
    # Total calls: 3
    assert diarizer._model.call_count == 3
