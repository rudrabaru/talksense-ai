import sys
import os
import json
import csv

# Add backend to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(project_root, "backend"))

from services.prediction.feature_builder import feature_builder
from services.embeddings.embed_conversation import embedder # To calculate sim if needed, or read from logs
# Actually, pattern miner calculates sim. 
# For this export script, to match the plan "Input: session summary, patterns, embeddings",
# we ideally read the *output* of the offline analysis.
# But we haven't persistently logged the "pattern miner output" to a file in Phase 3!
# We logged embeddings. Pattern miner was just a service or used in the runner.
# Correction: The 'run_advanced_analysis.py' printed results but didn't save them structurally.
# For training data export, we need that data. 
# STRATEGY: Rerun Feature Extraction here using the Services. 
# Read: session_summaries.jsonl + enriched_segments.jsonl + outcomes.jsonl

from services.pattern_miner import miner

def export_dataset():
    print("Exporting Prediction Dataset...")
    
    # Files
    session_log = os.path.join(project_root, "backend", "logs", "session_summaries.jsonl")
    enriched_log = os.path.join(project_root, "backend", "logs", "enriched_segments.jsonl")
    emb_log = os.path.join(project_root, "backend", "logs", "conversation_embeddings.jsonl")
    outcomes_file = os.path.join(project_root, "data", "outcomes.jsonl")
    output_csv = os.path.join(project_root, "data", "prediction_dataset.csv")

    if not os.path.exists(session_log):
        print("No session logs found.")
        return

    # 1. Load Outcomes
    outcomes = {}
    if os.path.exists(outcomes_file):
        with open(outcomes_file, "r") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    outcomes[d["session_id"]] = d["deal_outcome"]
                except: pass
    
    # 2. Load Embeddings (for optimization, or re-compute)
    # We will re-compute logic via PatternMiner to get consistent features
    
    # 3. Load Segments by Session
    segments_map = {}
    if os.path.exists(enriched_log):
        with open(enriched_log, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    d = json.loads(line)
                    sid = d.get("session_id")
                    if sid:
                        if sid not in segments_map: segments_map[sid] = []
                        segments_map[sid].append(d)
                except: pass

    # 4. Load Conversation Embeddings (if available, else we mock/skip sim)
    embeddings_map = {}
    if os.path.exists(emb_log):
         with open(emb_log, "r", encoding="utf-8") as f:
            for line in f:
                try:
                     d = json.loads(line)
                     embeddings_map[d["session_id"]] = d["conversation_embedding"]
                except: pass

    # 5. Process Sessions
    dataset = []
    
    with open(session_log, "r") as f:
        for line in f:
            try:
                summ = json.loads(line)
                sid = summ["session_id"]
                
                # Check outcome ground truth
                label = outcomes.get(sid)
                if not label:
                    continue # Skip sessions without label for training
                
                # Re-run Miner to get Features
                segs = segments_map.get(sid, [])
                emb = embeddings_map.get(sid)
                
                # Mine Patterns
                # (PatternMiner handles empty emb gracefully for similarity=0)
                # We assume no topic shifts recorded here for simplicity or re-calc if needed.
                # Let's pass empty topic_shifts list or simplistic len logic
                
                # Note: pattern_miner expects list of window embeddings for topic shift? 
                # Actually miner.analyze_session takes topic_shifts list outputted by embedder.
                # We don't have that persisted.
                # Simplified: pass empty list for now.
                mining_result = miner.analyze_session(sid, segs, emb, [])
                
                features = feature_builder.build_features(
                    session_summary=summ,
                    patterns=mining_result["patterns_detected"],
                    risk_score=mining_result["risk_score"],
                    similarity_to_failed=mining_result["similarity_to_failed_deal"]
                )
                
                # Add Label
                features["target_label"] = 1 if label == "won" else 0
                features["session_id"] = sid
                
                dataset.append(features)
                
            except Exception as e:
                print(f"Skipping session due to error: {e}")

    # 6. Write CSV
    if not dataset:
        print("No matched data found to export.")
        return

    headers = list(dataset[0].keys())
    # Ensure ID and Label are at ends or specific? Doesn't matter for pandas usually.
    
    with open(output_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(dataset)
        
    print(f"Exported {len(dataset)} rows to {output_csv}")

if __name__ == "__main__":
    export_dataset()
