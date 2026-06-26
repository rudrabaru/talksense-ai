import asyncio
import json
import os
import subprocess
import time

import httpx
import websockets

BACKEND_HTTP = "http://localhost:8000"
BACKEND_WS = "ws://localhost:8000"
AUDIO_FILE = "sample_audio/meeting_short.mp3"


async def test_e2e():
    print("Creating session...")
    async with httpx.AsyncClient() as client:
        resp = await client.post(f"{BACKEND_HTTP}/sessions", json={"mode": "meeting"})
        session_id = resp.json()["session_id"]
        print(f"Session: {session_id}")

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
    assert process.stdout is not None

    ws_audio_url = f"{BACKEND_WS}/ws/audio/{session_id}"
    t_start = time.time()
    try:
        async with websockets.connect(ws_audio_url) as ws:
            while time.time() - t_start < 25.0:  # Stream 25s
                chunk = process.stdout.read(8000)
                if not chunk:
                    break
                await ws.send(chunk)
                await asyncio.sleep(0.25)
            await ws.send("end")
            await asyncio.sleep(2)
    finally:
        process.terminate()

    print("Monitoring status...")
    from sqlalchemy import text

    from db.database import AsyncSessionLocal

    for _ in range(30):
        async with AsyncSessionLocal() as db:
            res = await db.execute(
                text(
                    "SELECT status, speaker_attribution_status FROM sessions WHERE id = :sid"  # noqa: E501
                ),
                {"sid": session_id},
            )
            row = res.fetchone()
            if row is not None and row.speaker_attribution_status in [
                "completed",
                "failed",
            ]:  # noqa: E501
                break
        await asyncio.sleep(2)

    print("Fetching dashboard snapshot...")
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{BACKEND_HTTP}/dashboard/{session_id}")
        data = resp.json()
        print(
            json.dumps(
                {
                    "talk_ratio_summary": data.get("talk_ratio_summary"),
                    "talk_timeline": data.get("talk_timeline"),
                },
                indent=2,
            )
        )

        with open("talk_ratio_output.json", "w") as f:
            json.dump(
                {
                    "talk_ratio_summary": data.get("talk_ratio_summary"),
                    "talk_timeline": data.get("talk_timeline"),
                },
                f,
                indent=2,
            )


if __name__ == "__main__":
    asyncio.run(test_e2e())
