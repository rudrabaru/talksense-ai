import json
import os
import math
from typing import List, Dict, Any

# CONFIG
EMBEDDING_LOG_FILE = "conversation_embeddings.jsonl"
WINDOW_SIZE = 6 # sliding window size

class ConversationEmbedder:
    def __init__(self):
        self.model = None
        self._load_model()

    def _load_model(self):
        try:
            from sentence_transformers import SentenceTransformer
            # Using 'all-MiniLM-L6-v2' as requested (fast, stable)
            self.model = SentenceTransformer('all-MiniLM-L6-v2')
            print("Loaded SentenceTransformer model.")
        except ImportError:
            print("sentence-transformers not found. Using MOCK mode.")
            self.model = None

    def embed_text(self, text: str) -> List[float]:
        if not text:
            return [0.0] * 384 # MiniLM dim is 384
            
        if self.model:
            return self.model.encode(text).tolist()
        else:
            # MOCK EMBEDDING: deterministic based on length/content hash
            # Just to simulate vectors for verification
            val = hash(text) % 100 / 100.0
            return [val] * 5 + [0.0] * 379

    def cosine_similarity(self, vec_a: List[float], vec_b: List[float]) -> float:
        dot_product = sum(a*b for a, b in zip(vec_a, vec_b))
        norm_a = math.sqrt(sum(a*a for a in vec_a))
        norm_b = math.sqrt(sum(b*b for b in vec_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot_product / (norm_a * norm_b)

    def process_session(self, session_id: str, segments: List[Dict[str, Any]]):
        """
        Generates granular embeddings for a session.
        """
        # A) Full Conversation Embedding
        full_text = " ".join([s.get("text", "") for s in segments])
        full_embedding = self.embed_text(full_text)
        
        # B) Speaker-wise Embeddings
        speaker_texts = {}
        for s in segments:
            spk = s.get("speaker_id", "spk_0")
            text = s.get("text", "")
            speaker_texts[spk] = speaker_texts.get(spk, "") + " " + text
            
        speaker_embeddings = {spk: self.embed_text(txt) for spk, txt in speaker_texts.items()}
        
        # C) Sliding Window Embeddings + Topic Shift
        window_embeddings = []
        topic_shifts = []
        
        num_windows = len(segments) - WINDOW_SIZE + 1
        if num_windows < 1:
            # If conversation too short, just embed the whole thing as one window
            vec = self.embed_text(full_text)
            window_embeddings.append({"start": 0, "end": len(segments), "vector": vec})
        else:
            prev_vec = None
            for i in range(num_windows):
                window_seg = segments[i : i + WINDOW_SIZE]
                window_text = " ".join([s.get("text", "") for s in window_seg])
                vec = self.embed_text(window_text)
                
                window_embeddings.append({
                    "start": i, 
                    "end": i + WINDOW_SIZE, 
                    "vector": vec
                })
                
                # Topic Shift Detection
                if prev_vec is not None:
                    sim = self.cosine_similarity(prev_vec, vec)
                    if sim < 0.75:
                        topic_shifts.append({
                            "window_index": i, 
                            "similarity": round(sim, 3),
                            "note": "Significant semantic shift detected"
                        })
                prev_vec = vec

        return {
            "session_id": session_id,
            "conversation_embedding": full_embedding,
            "speaker_embeddings": speaker_embeddings,
            "window_embeddings": window_embeddings,
            "topic_shifts": topic_shifts
        }

    def save_embeddings(self, data: Dict[str, Any]):
        log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "backend", "logs")
        os.makedirs(log_dir, exist_ok=True)
        path = os.path.join(log_dir, EMBEDDING_LOG_FILE)
        
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(data) + "\n")
        print(f"Saved embeddings for session {data['session_id']}")

# Singleton
embedder = ConversationEmbedder()
