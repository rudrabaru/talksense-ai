import asyncio
import os
import subprocess
import sys
import time

import httpx
import websockets

sys.stdout.reconfigure(encoding="utf-8")
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

BACKEND_HTTP = "http://localhost:8000"
BACKEND_WS = "ws://localhost:8000"
AUDIO_FILE = "sample_audio/meeting_short.mp3"


async def run_ui_verification():
    print("=" * 70)
    print("TalkSense AI: UI Verification Speaker Attribution Runner")
    print("=" * 70)

    # 1. Create a session
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BACKEND_HTTP}/sessions", json={"mode": "meeting"})
        resp.raise_for_status()
        session_data = resp.json()
        session_id = session_data["session_id"]
        print(f"SESSION_ID_READY:{session_id}")
        sys.stdout.flush()

    # 2. Wait 8 seconds to allow the browser subagent to navigate to the page
    print("Waiting 8 seconds for browser to connect...")
    await asyncio.sleep(8)

    # 3. Stream audio file
    audio_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", AUDIO_FILE)
    )
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        audio_path,
        "-f",
        "s16le",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-",
    ]
    process = subprocess.Popen(
        ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )

    ws_audio_url = f"{BACKEND_WS}/ws/audio/{session_id}"
    chunk_size = 8000  # 250ms of PCM
    chunk_interval = 0.250
    stream_duration = 30.0  # Stream 30 seconds to cover multiple speaker segments

    print(f"Connecting to Audio WS and streaming for {stream_duration}s...")
    t_start = time.time()
    try:
        async with websockets.connect(ws_audio_url) as ws:
            while time.time() - t_start < stream_duration:
                t_loop = time.time()
                chunk = process.stdout.read(chunk_size)
                if not chunk:
                    break
                await ws.send(chunk)

                elapsed = time.time() - t_loop
                sleep_time = max(0.0, chunk_interval - elapsed)
                await asyncio.sleep(sleep_time)

            print("Streaming finished. Sending 'end' command...")
            await ws.send("end")
            await asyncio.sleep(2)
    except Exception as e:
        print(f"WebSocket Error: {e}")
    finally:
        process.terminate()

    # Wait another 15 seconds to allow the browser to auto-refresh and display
    # "Completed"
    print("Waiting 15 seconds for post-processing and frontend auto-refresh...")
    await asyncio.sleep(15)
    print("Runner completed.")


if __name__ == "__main__":
    asyncio.run(run_ui_verification())
