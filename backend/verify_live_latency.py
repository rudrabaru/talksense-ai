import asyncio
import json
import subprocess
import sys
import time

# Ensure UTF-8 output on Windows console
from typing import Any

import httpx
import websockets

sys_stdout: Any = sys.stdout
sys_stdout.reconfigure(encoding="utf-8")
session_start_time = 0.0


async def run_latency_test():
    global session_start_time
    url = "http://localhost:8000/sessions"
    print("--- 1. Creating session ---")
    async with httpx.AsyncClient() as client:
        resp = await client.post(url, json={"mode": "meeting"})
        resp.raise_for_status()
        session_start_time = time.time()
        session_data = resp.json()
        session_id = session_data["session_id"]
        print(f"Created session: {session_id}")

    ws_audio_url = f"ws://localhost:8000/ws/audio/{session_id}"
    ws_transcript_url = f"ws://localhost:8000/ws/transcript/{session_id}"

    latencies = []

    async def receive_transcripts():
        print("Connecting to transcript WebSocket...")
        async with websockets.connect(ws_transcript_url) as ws:
            print("Transcript WebSocket connected.")
            while True:
                try:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if data.get("type") == "transcript":
                        payload = data["payload"]
                        text = payload["text"]
                        end_sec = payload["end"]
                        speaker = payload["speaker"]
                        sentiment = payload["sentiment_label"]

                        recv_time = time.time()
                        # The audio corresponding to the segment ended at
                        # session_start_time + end_sec
                        audio_end_time = session_start_time + end_sec
                        latency = recv_time - audio_end_time
                        latencies.append(latency)
                        print(
                            f"[Transcript Received] Speaker: {speaker} | Sentiment: {sentiment} | Text: '{text}'"  # noqa: E501
                        )
                        print(
                            f"  -> Segment End: {end_sec:.2f}s | Latency: {latency:.3f}s"  # noqa: E501
                        )
                except websockets.exceptions.ConnectionClosed:
                    print("Transcript WebSocket closed.")
                    break

    # Start the transcript receiver in background
    receiver_task = asyncio.create_task(receive_transcripts())
    await asyncio.sleep(1)  # wait for connection

    print("\n--- 2. Starting audio streaming ---")
    ffmpeg_cmd = [
        "ffmpeg",
        "-y",
        "-i",
        "../sample_audio/meeting_short.mp3",
        "-f",
        "s16le",
        "-ac",
        "1",
        "-ar",
        "16000",
        "-",
    ]

    # We will read from stdout
    process = subprocess.Popen(
        ffmpeg_cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL
    )

    async with websockets.connect(ws_audio_url) as ws:
        print("Audio WebSocket connected. Streaming...")

        # We will stream for 20 seconds
        stream_duration = 20.0
        chunk_size = 8000  # 250ms of 16kHz 16-bit mono PCM
        chunk_interval = 0.250  # 250ms

        start_stream_time = time.time()

        assert process.stdout is not None
        while time.time() - start_stream_time < stream_duration:
            loop_start = time.time()

            chunk = process.stdout.read(chunk_size)
            if not chunk:
                break

            await ws.send(chunk)

            # sleep to simulate real-time playback
            elapsed = time.time() - loop_start
            sleep_time = max(0.0, chunk_interval - elapsed)
            await asyncio.sleep(sleep_time)

        print("Finished streaming audio chunks.")

        # Send end command to finish session
        print("Sending 'end' control command to close session...")
        await ws.send("end")

        # Wait a bit for final transcriptions to arrive
        await asyncio.sleep(3)

    # Clean up
    process.terminate()
    receiver_task.cancel()
    try:
        await receiver_task
    except asyncio.CancelledError:
        pass

    if latencies:
        avg_lat = sum(latencies) / len(latencies)
        max_lat = max(latencies)
        min_lat = min(latencies)
        print("\n--- LATENCY REPORT ---")
        print(f"Number of Segments Transcribed: {len(latencies)}")
        print(f"Minimum Latency: {min_lat:.3f}s")
        print(f"Average Latency: {avg_lat:.3f}s")
        print(f"Maximum Latency: {max_lat:.3f}s")
    else:
        print("\nERROR: No transcripts received during the test.")


if __name__ == "__main__":
    asyncio.run(run_latency_test())
