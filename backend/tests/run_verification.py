import asyncio
import json
import os
import urllib.request

import websockets

API_URL = "http://localhost:8000/sessions"
WS_URL = "ws://localhost:8000/ws"


async def test_session(mode, fixture_path):
    print(
        f"\n{'='*50}\n--- Testing {mode.upper()} mode with {os.path.basename(fixture_path)} ---\n{'='*50}"
    )

    # 1. Create Session
    req = urllib.request.Request(f"{API_URL}?mode={mode}", method="POST")
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode())
            session_id = data["session_id"]
            print(f"Created session: {session_id}")
    except Exception as e:
        print(f"Failed to create session: {e}")
        return

    # Load fixture
    with open(fixture_path, "r") as f:
        convo = json.load(f)

    # 2. Connect to WS Channels
    audio_ws_url = f"{WS_URL}/audio/{session_id}"
    metrics_ws_url = f"{WS_URL}/metrics/{session_id}"
    alerts_ws_url = f"{WS_URL}/alerts/{session_id}"

    try:
        async with (
            websockets.connect(audio_ws_url) as audio_ws,
            websockets.connect(metrics_ws_url) as metrics_ws,
            websockets.connect(alerts_ws_url) as alerts_ws,
        ):

            print("Connected to WebSockets.")

            metrics_events = []
            alerts_events = []

            async def consume_metrics():
                try:
                    while True:
                        msg = await metrics_ws.recv()
                        metrics_events.append(json.loads(msg))
                except websockets.ConnectionClosed:
                    pass

            async def consume_alerts():
                try:
                    while True:
                        msg = await alerts_ws.recv()
                        alerts_events.append(json.loads(msg))
                except websockets.ConnectionClosed:
                    pass

            mtask = asyncio.create_task(consume_metrics())
            atask = asyncio.create_task(consume_alerts())

            # 3. Inject phrases sequentially
            for turn in convo:
                speaker = turn["speaker"]
                text = turn["text"]
                command = f"inject:{speaker}|{text}"
                await audio_ws.send(command)
                print(f"Injected: {speaker}: {text}")
                await asyncio.sleep(
                    2.5
                )  # wait for processing and engine flush (which is 1s interval)

            # 4. End Session
            await audio_ws.send("end")
            print("Sent 'end' command.")

            # wait a bit for final flushes
            await asyncio.sleep(4)

            # Evaluate Results
            if metrics_events:
                final_payload = metrics_events[-1]
                final_metrics = final_payload.get("payload", {})
                print("\n[Metrics Summary]")
                print(f" - Sentiment: {final_metrics.get('sentiment')}")
                print(f" - Health: {final_metrics.get('health_score')}")
                print(f" - Roles: {final_metrics.get('roles')}")
                print(f" - Objections: {final_metrics.get('objections')}")
                print(f" - Buying Signals: {final_metrics.get('buying_signals')}")
            else:
                print("No metrics received!")

            if alerts_events:
                print(f"\n[Alerts Triggered: {len(alerts_events)}]")
                for a in alerts_events:
                    alert_data = a.get("payload", {})
                    print(f" - {alert_data.get('type')}: {alert_data.get('message')}")
            else:
                print("\n[Alerts Triggered: 0]")

            mtask.cancel()
            atask.cancel()

    except Exception as e:
        print(f"WebSocket error: {e}")


async def main():
    base_dir = os.path.dirname(__file__)
    await test_session("sales", os.path.join(base_dir, "fixtures/sales_call.json"))
    await test_session("meeting", os.path.join(base_dir, "fixtures/meeting.json"))
    await test_session("interview", os.path.join(base_dir, "fixtures/interview.json"))


if __name__ == "__main__":
    asyncio.run(main())
