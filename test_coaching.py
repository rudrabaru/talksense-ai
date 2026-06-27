import time
import json
import sys
import os

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), "backend"))

from ws.session_manager import ConversationState
from engine.conversation_engine import ConversationEngine

engine = ConversationEngine()
state = ConversationState()

# Simulate states
state.duration_seconds = 180
state.filler_count = 15  # 15 / 3 = 5 fillers/min -> triggers filler density
state.interruptions = 4  # triggers interruptions
state.speaking_ratio = {"Speaker A": 80, "Speaker B": 20}  # triggers speaking balance
state.objection_timeline = [
    {"category": "Pricing", "keyword": "expensive", "timestamp": 150}
]  # 180 - 150 = 30 < 120 -> triggers objection

t0 = time.perf_counter()
for _ in range(1000):
    engine._generate_coaching_recommendations(state, mode="sales")
t1 = time.perf_counter()

cpu_overhead = ((t1 - t0) / 1000) * 1000  # in ms

payload = json.dumps(state.coaching_tips)
payload_size = len(payload.encode("utf-8"))

print("--- Coaching Validation ---")
print(f"Tips generated: {len(state.coaching_tips)}")
for t in state.coaching_tips:
    print(f" - {t['id']}: {t['title']} ({t['severity']})")

print(f"\nCPU Overhead per tick: {cpu_overhead:.4f} ms")
print(f"Payload size: {payload_size} bytes")

# Test disappear
state.interruptions = 0
state.filler_count = 5  # 5 / 3 = 1.6
state.speaking_ratio = {"Speaker A": 55, "Speaker B": 45}
state.duration_seconds = 300  # 300 - 150 = 150 > 120 -> objection stale
engine._generate_coaching_recommendations(state, mode="sales")
print(f"\nTips after state normalized: {len(state.coaching_tips)}")
