from typing import Dict, Optional

import numpy as np


class SpeakerProfile:
    """
    Maintains persistent speaker embeddings for a session to prevent cross-chunk amnesia.
    Uses Cosine Similarity to match incoming segment embeddings to known speakers.
    """

    def __init__(self, similarity_threshold: float = 0.35):
        self.similarity_threshold = similarity_threshold
        # Map canonical speaker ID (e.g. "Speaker 1") to their centroid embedding
        self.centroids: Dict[str, np.ndarray] = {}
        # Keep track of how many embeddings were aggregated into the centroid
        self.counts: Dict[str, int] = {}
        self._next_speaker_id = 1

    def match_or_create(self, embedding: np.ndarray) -> str:
        """
        Compare the new embedding with existing centroids using Cosine Similarity.
        If max similarity > threshold, assign to that speaker and update centroid.
        Else, create a new speaker.
        """
        if embedding is None or len(embedding) == 0:
            return "Speaker 1"

        best_speaker: Optional[str] = None
        best_sim = -1.0

        # L2 normalize input embedding
        emb_norm = embedding / (np.linalg.norm(embedding) + 1e-8)

        for spk, centroid in self.centroids.items():
            # centroids are kept normalized, but we normalize again just in case
            cent_norm = centroid / (np.linalg.norm(centroid) + 1e-8)
            sim = np.dot(emb_norm, cent_norm)
            if sim > best_sim:
                best_sim = float(sim)
                best_speaker = spk

        print(
            f"DEBUG: match_or_create best_sim={best_sim:.3f} for speaker={best_speaker}, threshold={self.similarity_threshold}"
        )

        if best_speaker is not None and best_sim >= self.similarity_threshold:
            # Update centroid (moving average)
            count = self.counts[best_speaker]
            new_centroid = (self.centroids[best_speaker] * count + emb_norm) / (
                count + 1
            )
            self.centroids[best_speaker] = new_centroid / (
                np.linalg.norm(new_centroid) + 1e-8
            )
            self.counts[best_speaker] += 1
            return best_speaker
        else:
            # Create new speaker
            new_spk = f"Speaker {self._next_speaker_id}"
            self._next_speaker_id += 1
            self.centroids[new_spk] = emb_norm
            self.counts[new_spk] = 1
            return new_spk
