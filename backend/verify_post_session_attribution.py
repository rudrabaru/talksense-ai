import asyncio
import time
import httpx
import websockets
import json
import subprocess
import os
import sys
import wave

# Ensure UTF-8 output on Windows console to prevent UnicodeEncodeError
sys.stdout.reconfigure(encoding='utf-8')

# Add backend directory to Python path for DB access
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BACKEND_HTTP = "http://localhost:8000"
BACKEND_WS = "ws://localhost:8000"
AUDIO_FILE = "sample_audio/meeting_short.mp3"  # Relative to talksense-ai root

async def run_verification():
    print("=" * 70)
    print("TalkSense AI: End-to-End Post-Session Speaker Attribution Verification")
    print("=" * 70)

    # 1. Create a session
    print("\n[Step 1] Creating a new meeting session...")
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BACKEND_HTTP}/sessions", json={"mode": "meeting"})
        resp.raise_for_status()
        session_data = resp.json()
        session_id = session_data["session_id"]
        print(f"    Created Session ID: {session_id}")

    # 2. Start streaming raw audio (ffmpeg decoding mp3 -> 16kHz s16le PCM)
    audio_path = os.path.join("..", AUDIO_FILE)
    if not os.path.exists(audio_path):
        # try absolute or direct path
        audio_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", AUDIO_FILE))
    
    print(f"\n[Step 2] Streaming audio file: {audio_path}")
    if not os.path.exists(audio_path):
        print(f"    ❌ ERROR: Audio file not found at {audio_path}")
        return

    # Decode audio using ffmpeg to standard mono 16kHz signed 16-bit PCM
    ffmpeg_cmd = [
        "ffmpeg", "-y", "-i", audio_path,
        "-f", "s16le", "-ac", "1", "-ar", "16000", "-"
    ]
    try:
        process = subprocess.Popen(ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"    ❌ ERROR starting ffmpeg: {e}")
        return

    ws_audio_url = f"{BACKEND_WS}/ws/audio/{session_id}"
    ws_transcript_url = f"{BACKEND_WS}/ws/transcript/{session_id}"

    # Setup listener for live transcripts to prove live streaming is occurring
    live_segments = []
    async def listen_transcripts():
        try:
            async with websockets.connect(ws_transcript_url) as ws:
                while True:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if data.get("type") == "transcript":
                        payload = data["payload"]
                        text = payload["text"]
                        speaker = payload["speaker"]
                        print(f"      [Live Transcript] {speaker}: {text}")
                        live_segments.append(payload)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"      [Transcript WS] Error: {e}")

    transcript_listener = asyncio.create_task(listen_transcripts())
    await asyncio.sleep(1) # Let listener connect

    # Connect and stream audio chunks
    chunk_size = 8000  # 250ms of PCM
    chunk_interval = 0.250
    stream_duration = 30.0  # Stream 30 seconds of audio to get multiple speaker segments
    
    print(f"    Connecting to Audio WS: {ws_audio_url}")
    t_start = time.time()
    try:
        async with websockets.connect(ws_audio_url) as ws:
            print("    Connected. Streaming binary chunks...")
            
            while time.time() - t_start < stream_duration:
                t_loop = time.time()
                chunk = process.stdout.read(chunk_size)
                if not chunk:
                    print("    End of audio stream reached.")
                    break
                
                await ws.send(chunk)
                
                # Sleep to maintain real-time simulation
                elapsed = time.time() - t_loop
                sleep_time = max(0.0, chunk_interval - elapsed)
                await asyncio.sleep(sleep_time)

            print("    Streaming finished. Sending 'end' command...")
            await ws.send("end")
            await asyncio.sleep(2)
    except Exception as e:
        print(f"    ❌ WebSocket connection failed: {e}")
    finally:
        process.terminate()
        transcript_listener.cancel()

    print(f"\n    Finished streaming. Total live segments received: {len(live_segments)}")

    # 3. Monitor Status Lifecycle & DB
    print("\n[Step 3] Monitoring Speaker Attribution Status Lifecycle in DB...")
    
    from db.database import AsyncSessionLocal, engine
    from sqlalchemy import text
    
    status_log = []
    
    # Poll database for status changes
    for step in range(30):
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                text("SELECT status, speaker_attribution_status, audio_file_path FROM sessions WHERE id = :sid"),
                {"sid": session_id}
            )
            row = result.fetchone()
            if row:
                status_log.append((time.time(), row.status, row.speaker_attribution_status, row.audio_file_path))
                print(f"    Time +{step}s | Session Status: {row.status:12s} | Attribution Status: {str(row.speaker_attribution_status)}")
                if row.speaker_attribution_status in ["completed", "failed"]:
                    break
        await asyncio.sleep(1)

    # 4. Check WAV File Creation (Test 1)
    print("\n[Step 4] Validating WAV File Creation (Test 1)...")
    final_wav_path = None
    for item in status_log:
        if item[3]:
            final_wav_path = item[3]
    
    if final_wav_path and os.path.exists(final_wav_path):
        size = os.path.getsize(final_wav_path)
        print(f"    WAV File Path: {final_wav_path}")
        print(f"    WAV File Size: {size} bytes")
        
        # Verify WAV file is valid using standard wave module
        try:
            with wave.open(final_wav_path, "rb") as w:
                nchannels, sampwidth, framerate, nframes = w.getparams()[:4]
                duration = nframes / framerate
                print(f"    WAV Properties: Channels={nchannels}, SampleWidth={sampwidth} bytes, FrameRate={framerate}Hz")
                print(f"    WAV Duration: {duration:.2f} seconds")
                if size > 44 and duration > 0:
                    print("    ✅ TEST 1 PASSED: Valid WAV file created.")
                else:
                    print("    ❌ TEST 1 FAILED: Invalid WAV file size or duration.")
        except Exception as e:
            print(f"    ❌ TEST 1 FAILED: Failed to open WAV file: {e}")
    else:
        print(f"    ❌ TEST 1 FAILED: WAV file not found at path {final_wav_path}")

    # 5. Status Lifecycle Verification (Test 2)
    print("\n[Step 5] Validating Status Lifecycle Transitions (Test 2)...")
    transitions = [item[2] for item in status_log if item[2] is not None]
    unique_transitions = []
    for t in transitions:
        if not unique_transitions or unique_transitions[-1] != t:
            unique_transitions.append(t)
            
    print(f"    Observed transition sequence: {unique_transitions}")
    if "completed" in unique_transitions:
        print("    ✅ TEST 2 PASSED: Attribution status transitioned to 'completed'.")
    else:
        print("    ❌ TEST 2 FAILED: Attribution status did not transition to 'completed'.")

    # 6. Speaker Update Validation (Test 4)
    print("\n[Step 6] Validating Speaker Attribution Updates in DB (Test 4)...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text("SELECT speaker_id, text, start_time, end_time FROM transcript_segments WHERE session_id = :sid ORDER BY start_time"),
            {"sid": session_id}
        )
        segments = result.fetchall()
        
        distinct_speakers = set()
        print(f"    Found {len(segments)} segments in DB:")
        for idx, s in enumerate(segments):
            distinct_speakers.add(s.speaker_id)
            print(f"      Segment {idx+1:02d} | Time: {s.start_time:.2f}s - {s.end_time:.2f}s | Speaker: {s.speaker_id:12s} | '{s.text[:40]}...'")
            
        print(f"    Distinct speakers found after post-session diarization: {distinct_speakers}")
        if len(distinct_speakers) >= 2:
            print(f"    ✅ TEST 4 PASSED: DB updated with {len(distinct_speakers)} distinct speakers.")
        else:
            print("    ❌ TEST 4 FAILED: DB has less than 2 distinct speakers.")

    # 7. Dashboard REST Response Validation (Test 5)
    print("\n[Step 7] Validating REST Dashboard Payload (Test 5)...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND_HTTP}/dashboard/{session_id}")
        if resp.status_code == 200:
            dash = resp.json()
            segs = dash.get("transcript_segments", [])
            dash_speakers = {s.get("speaker") for s in segs if s.get("speaker")}
            print(f"    Dashboard segments count: {len(segs)}")
            print(f"    Dashboard distinct speakers: {dash_speakers}")
            if len(dash_speakers) >= 2:
                print("    ✅ TEST 5 PASSED: Dashboard returns corrected speakers.")
            else:
                print("    ❌ TEST 5 FAILED: Dashboard does not return multiple speakers.")
        else:
            print(f"    ❌ TEST 5 FAILED: GET /dashboard status code {resp.status_code}")

    # 8. Attribution Diagnostics Persisted (Test 6)
    print("\n[Step 8] Validating Attribution Diagnostics in session_metrics (Test 6)...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            text(
                "SELECT metric_value FROM session_metrics "
                "WHERE session_id = :sid AND metric_name = 'speaker_attribution' "
                "ORDER BY timestamp DESC LIMIT 1"
            ),
            {"sid": session_id}
        )
        row = result.fetchone()
        if row is None:
            print("    ❌ TEST 6 FAILED: No 'speaker_attribution' metric row found in session_metrics.")
        else:
            diag = row.metric_value if isinstance(row.metric_value, dict) else {}
            required_keys = {"speakers_detected", "speaker_turns", "segments_updated", "total_segments", "coverage_percent"}
            missing = required_keys - set(diag.keys())
            if missing:
                print(f"    ❌ TEST 6 FAILED: Diagnostics row missing keys: {missing}")
                print(f"    Actual value: {diag}")
            else:
                print(f"    Diagnostics row found:")
                print(f"      speakers_detected : {diag['speakers_detected']}")
                print(f"      speaker_turns     : {diag['speaker_turns']}")
                print(f"      segments_updated  : {diag['segments_updated']}")
                print(f"      total_segments    : {diag['total_segments']}")
                print(f"      coverage_percent  : {diag['coverage_percent']}%")
                # Validate coverage calculation
                expected_coverage = round(
                    diag["segments_updated"] / max(diag["total_segments"], 1) * 100, 1
                )
                if diag["coverage_percent"] == expected_coverage:
                    print(f"    ✅ TEST 6 PASSED: Attribution diagnostics persisted correctly (coverage={diag['coverage_percent']}%).")
                else:
                    print(f"    ❌ TEST 6 FAILED: coverage_percent mismatch (expected {expected_coverage}, got {diag['coverage_percent']}).")

    # 9. Dashboard speaker_attribution nested object (Test 7)
    print("\n[Step 9] Validating dashboard speaker_attribution nested payload (Test 7)...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND_HTTP}/dashboard/{session_id}")
        if resp.status_code == 200:
            dash = resp.json()
            sa = dash.get("speaker_attribution")
            if sa is None:
                print("    ❌ TEST 7 FAILED: 'speaker_attribution' key missing from dashboard response.")
            else:
                print(f"    speaker_attribution payload:")
                for k, v in sa.items():
                    print(f"      {k:<20} : {v}")
                required = {"status", "speakers_detected", "coverage"}
                missing = required - set(sa.keys())
                if missing:
                    print(f"    ❌ TEST 7 FAILED: Missing keys in speaker_attribution: {missing}")
                elif sa.get("status") != "completed":
                    print(f"    ❌ TEST 7 FAILED: Expected status='completed', got {sa.get('status')!r}")
                elif sa.get("coverage") is None:
                    print("    ❌ TEST 7 FAILED: 'coverage' is None — diagnostics not populated.")
                else:
                    print(f"    ✅ TEST 7 PASSED: Dashboard speaker_attribution has all fields (coverage={sa['coverage']}%).")
        else:
            print(f"    ❌ TEST 7 FAILED: GET /dashboard status code {resp.status_code}")

    await engine.dispose()
    print("\nVerification process complete.")

if __name__ == "__main__":
    asyncio.run(run_verification())

