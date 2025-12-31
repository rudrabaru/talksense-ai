import sys
import os
import json
import argparse

# Add backend to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(project_root, "backend"))

from services.embeddings.embed_conversation import embedder, EMBEDDING_LOG_FILE
from services.pattern_miner import miner

def run_analysis(session_id=None):
    print("Starts Advanced Conversation Analysis (Offline)...")
    
    # 1. Load Segments
    # In a real app, this would read from a Database.
    # Here we read from logs/enriched_segments.jsonl
    log_file = os.path.join(project_root, "backend", "logs", "enriched_segments.jsonl")
    
    if not os.path.exists(log_file):
        print("No enriched segment logs found.")
        return

    # Find segments for the target session (or all if not specified)
    # For simplicity, if session_id is None, we process the LAST session found.
    
    sessions_map = {}
    
    with open(log_file, "r", encoding="utf-8") as f:
        for line in f:
            try:
                data = json.loads(line)
                sess = data.get("session_id")
                if not sess: continue
                if sess not in sessions_map:
                    sessions_map[sess] = []
                sessions_map[sess].append(data)
            except:
                pass

    if not sessions_map:
        print("No session data found in logs.")
        return

    if session_id:
        if session_id not in sessions_map:
            print(f"Session ID {session_id} not found.")
            return
        target_sessions = [session_id]
    else:
        # Process ONLY the last session for demo purposes
        last_session = list(sessions_map.keys())[-1]
        print(f"No Session ID provided. Defaulting to last session: {last_session}")
        target_sessions = [last_session]

    # 2. Process
    for sess in target_sessions:
        print(f"\nProcessing Session: {sess}")
        segments = sessions_map[sess]
        
        # A) Embeddings
        print("  - Generating Embeddings...")
        emb_result = embedder.process_session(sess, segments)
        embedder.save_embeddings(emb_result)
        
        # B) Pattern Mining
        print("  - Mining Patterns...")
        mining_result = miner.analyze_session(
            sess, 
            segments, 
            emb_result["conversation_embedding"],
            emb_result.get("topic_shifts", [])
        )
        
        print("\n  [ANALYSIS RESULT]")
        print(f"  Risk Score: {mining_result['risk_score']}")
        print(f"  Similarity to Failed Deals: {mining_result['similarity_to_failed_deal']}")
        print(f"  Patterns Detected: {mining_result['patterns_detected']}")
        
        # (Optional) We could save this to 'insights.jsonl'
        
    print("\nAnalysis Complete.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--session_id", help="Specific Session ID to analyze")
    args = parser.parse_args()
    
    run_analysis(args.session_id)
