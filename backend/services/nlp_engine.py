from transformers import pipeline

class NLPEngine:
    def __init__(self):
        self.sentiment_pipeline = pipeline(
            "sentiment-analysis",
            model="tabularisai/multilingual-sentiment-analysis"
        )

    def enrich_segment(self, segment: dict) -> dict:
        if len(segment["text"].split()) < 3:
            return {
                **segment,
                "sentiment": "Neutral",
                "sentiment_confidence": 0.0
            }

        result = self.sentiment_pipeline(segment["text"])[0]

        return {
            **segment,
            "sentiment": result["label"],        # positive / neutral / negative
            "sentiment_confidence": round(result["score"], 3)
        }

    def enrich_transcript(self, segments: list) -> list:
        return [self.enrich_segment(s) for s in segments]