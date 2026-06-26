from services.clause_parser import split_into_clauses
from services.conversation_state_resolver import resolve_conversation_state

text1 = "I'll handle the API..."
text2 = "Wait, no, I am going to handle the UI."

segments = [
    {"speaker": "A", "text": text1},
    {"speaker": "A", "text": text2}
]

for s in segments:
    s["clauses"] = split_into_clauses(s["text"])

resolve_conversation_state(segments)

for s in segments:
    print(f"--- Segment ---")
    for c in s["clauses"]:
        print(f"  {c}")
