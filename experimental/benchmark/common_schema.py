from typing import List, Dict, Any

class Segment:
    """Unified segment representation for evaluation."""
    def __init__(self, start: float, end: float, speaker: str, text: str = ""):
        self.start = start
        self.end = end
        self.speaker = speaker
        self.text = text

    def duration(self) -> float:
        return max(0.0, self.end - self.start)

    def overlap(self, other: "Segment") -> float:
        return max(0.0, min(self.end, other.end) - max(self.start, other.start))

    def __repr__(self) -> str:
        return f"Segment({self.start:.2f}-{self.end:.2f}, {self.speaker!r})"

def create_neutral_output(
    pipeline_name: str,
    sample_id: str,
    segments: List[Segment],
    latency_seconds: float,
    load_seconds: float = 0.0,
    inference_seconds: float = 0.0,
    peak_ram_mb: float = 0.0,
    metadata: Dict[str, Any] = None
) -> Dict[str, Any]:
    """Generates the common JSON schema for both pipelines."""
    speakers = sorted(list(set(s.speaker for s in segments)))
    return {
        "pipeline": pipeline_name,
        "sample_id": sample_id,
        "speakers": speakers,
        "segments": [
            {"start": round(s.start, 3), "end": round(s.end, 3), "speaker": s.speaker}
            for s in segments
        ],
        "runtime": {
            "latency_seconds": round(latency_seconds, 3),
            "load_seconds": round(load_seconds, 3),
            "inference_seconds": round(inference_seconds, 3),
            "peak_ram_mb": round(peak_ram_mb, 2)
        },
        "metadata": metadata or {}
    }
