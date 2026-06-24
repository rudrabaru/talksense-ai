"""
TalkSense AI — Diarization Post-Processing Configuration

Centralized configuration for all post-processing heuristics applied
after Pyannote speaker assignment to improve SCDR.

All magic numbers live here. No hardcoded values elsewhere.
"""

# Strategy A: Sandwich Correction
# If pattern is A → B → A and B segment is short, relabel B to A
SANDWICH_ENABLED = True
SANDWICH_MAX_DURATION_S = 3.0    # Max duration of middle segment to correct
SANDWICH_MAX_WORDS = 5           # Max word count of middle segment to correct

# Strategy B: Short Segment Confidence Repair  
# If segment is very short and both neighbors are the same speaker, relabel
SHORT_REPAIR_ENABLED = True
SHORT_REPAIR_MAX_DURATION_S = 2.0  # Shorter threshold than sandwich
SHORT_REPAIR_MAX_WORDS = 3         # Fewer words threshold

# Strategy C: Turn Merge
# Merge consecutive segments of same speaker with small gap
TURN_MERGE_ENABLED = False          # Disabled by default (doesn't help SCDR)
TURN_MERGE_MAX_GAP_S = 0.5         # Max gap between segments to merge

# Strategy D: Transition Smoothing
# Prevent spurious transitions from very short segments
TRANSITION_SMOOTH_ENABLED = True
TRANSITION_SMOOTH_MIN_DURATION_S = 1.0  # Segments shorter than this get smoothed


def apply_postprocessing(predicted_segments):
    """
    Apply all enabled post-processing strategies to predicted speaker segments.
    
    Args:
        predicted_segments: list of objects with .start, .end, .speaker, .text
        
    Returns:
        list of corrected segment objects (same type)
    """
    if not predicted_segments or len(predicted_segments) < 3:
        return predicted_segments
    
    segments = list(predicted_segments)  # Don't mutate original
    
    # Strategy A: Sandwich Correction (A → B → A, relabel B → A)
    if SANDWICH_ENABLED:
        segments = _apply_sandwich(segments)
    
    # Strategy B: Short Segment Confidence Repair
    if SHORT_REPAIR_ENABLED:
        segments = _apply_short_repair(segments)
    
    # Strategy D: Transition Smoothing
    if TRANSITION_SMOOTH_ENABLED:
        segments = _apply_transition_smoothing(segments)
    
    return segments


def _apply_sandwich(segments):
    """Strategy A: Fix A→B→A patterns where B is short."""
    if len(segments) < 3:
        return segments
    
    corrections = 0
    for i in range(1, len(segments) - 1):
        prev_spk = segments[i - 1].speaker
        curr_spk = segments[i].speaker
        next_spk = segments[i + 1].speaker
        
        if prev_spk == next_spk and curr_spk != prev_spk:
            duration = segments[i].end - segments[i].start
            word_count = len(segments[i].text.strip().split()) if hasattr(segments[i], 'text') and segments[i].text else 999
            
            if duration <= SANDWICH_MAX_DURATION_S and word_count <= SANDWICH_MAX_WORDS:
                segments[i] = _clone_with_speaker(segments[i], prev_spk)
                corrections += 1
    
    return segments


def _apply_short_repair(segments):
    """Strategy B: Repair very short segments when neighbors agree."""
    if len(segments) < 3:
        return segments
    
    for i in range(1, len(segments) - 1):
        prev_spk = segments[i - 1].speaker
        curr_spk = segments[i].speaker
        next_spk = segments[i + 1].speaker
        
        if prev_spk == next_spk and curr_spk != prev_spk:
            duration = segments[i].end - segments[i].start
            word_count = len(segments[i].text.strip().split()) if hasattr(segments[i], 'text') and segments[i].text else 999
            
            if duration <= SHORT_REPAIR_MAX_DURATION_S and word_count <= SHORT_REPAIR_MAX_WORDS:
                segments[i] = _clone_with_speaker(segments[i], prev_spk)
    
    return segments


def _apply_transition_smoothing(segments):
    """Strategy D: Smooth transitions by absorbing very short lone segments."""
    if len(segments) < 3:
        return segments
    
    for i in range(1, len(segments) - 1):
        curr_spk = segments[i].speaker
        duration = segments[i].end - segments[i].start
        
        if duration < TRANSITION_SMOOTH_MIN_DURATION_S:
            prev_spk = segments[i - 1].speaker
            next_spk = segments[i + 1].speaker
            
            # If this short segment is different from both neighbors but neighbors
            # agree, it's likely noise
            if prev_spk == next_spk and curr_spk != prev_spk:
                segments[i] = _clone_with_speaker(segments[i], prev_spk)
    
    return segments


def _clone_with_speaker(segment, new_speaker):
    """Create a copy of segment with a different speaker label."""
    # Works with namedtuple-like objects that have _replace, or simple objects
    if hasattr(segment, '_replace'):
        return segment._replace(speaker=new_speaker)
    elif hasattr(segment, '__dict__'):
        import copy
        new_seg = copy.copy(segment)
        new_seg.speaker = new_speaker
        return new_seg
    else:
        # Fallback: create a new namedtuple-style object
        from collections import namedtuple
        Seg = namedtuple('Segment', ['start', 'end', 'speaker', 'text'])
        return Seg(start=segment.start, end=segment.end, speaker=new_speaker, 
                   text=getattr(segment, 'text', ''))
