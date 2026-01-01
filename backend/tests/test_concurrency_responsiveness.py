import time
import threading
import subprocess
import sys
import os
import httpx
import asyncio

# Configuration
BASE_URL = "http://127.0.0.1:8000"
TEST_FILE = "uploads/BuisinessMeeting.mp3"  # Use an existing file
SERVER_PROCESS = None

def start_server():
    """Starts the FastAPI server in a subprocess."""
    global SERVER_PROCESS
    print("[Test] Starting Uvicorn server...")
    SERVER_PROCESS = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--port", "8000"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    # Wait for server to boot
    for _ in range(20):
        try:
            resp = httpx.get(f"{BASE_URL}/health", timeout=1.0)
            if resp.status_code == 200:
                print("[Test] Server is up!")
                return
        except Exception:
            time.sleep(1)
    raise RuntimeError("Server failed to start")

def perform_heavy_request():
    """Simulates a heavy analysis request."""
    print("[Test] Sending heavy /analyze request...")
    if not os.path.exists(TEST_FILE):
        print(f"[Skipping] Test file {TEST_FILE} not found. Cannot perform heavy load test accurately without it.")
        return

    try:
        with open(TEST_FILE, "rb") as f:
            files = {"file": (os.path.basename(TEST_FILE), f, "audio/mpeg")}
            # Increase timeout to allowing full processing (Whisper takes time)
            resp = httpx.post(f"{BASE_URL}/analyze", files=files, data={"mode": "meeting"}, timeout=120.0)
            print(f"[Test] Analysis finished with status {resp.status_code}")
    except httpx.TimeoutException:
        print("[Test] Analysis timed out (expected if strictly checking responsiveness only)")
    except Exception as e:
        print(f"[Test] Analysis failed: {e}")

def check_responsiveness():
    """Checks /health endpoint latency during heavy load."""
    print("[Test] Monitor starting: checking /health responsiveness...")
    latencies = []
    start_time = time.time()
    
    # Monitor for 10 seconds or until thread logic dictates
    for i in range(10):
        try:
            req_start = time.time()
            resp = httpx.get(f"{BASE_URL}/health", timeout=2.0)
            duration = time.time() - req_start
            print(f"[Monitor] /health responded in {duration:.4f}s")
            latencies.append(duration)
            
            if duration > 2.5:
                print("[FAIL] /health took too long!")
                return False
        except Exception as e:
            print(f" [FAIL] /health check failed: {e}")
            return False
            
        time.sleep(0.5)
        
    avg_latency = sum(latencies) / len(latencies)
    print(f"[Test] Average latency: {avg_latency:.4f}s")
    return True

def main():
    try:
        start_server()
        
        # Start heavy request in a separate thread
        analysis_thread = threading.Thread(target=perform_heavy_request)
        analysis_thread.start()
        
        # Give it a second to actually start processing and block if it was going to block
        time.sleep(2)
        
        # Check responsiveness
        passed = check_responsiveness()
        
        if passed:
            print("\n [PASSED]: Server remained responsive during heavy analysis.")
            sys.exit(0)
        else:
            print("\n [FAILED]: Server became unresponsive.")
            sys.exit(1)
            
    finally:
        if SERVER_PROCESS:
            SERVER_PROCESS.terminate()
            print("[Test] Server stopped.")

if __name__ == "__main__":
    main()
