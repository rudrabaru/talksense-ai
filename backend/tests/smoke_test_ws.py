import asyncio
import logging
import sys

import requests
import websockets

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)

BASE_URL = "http://127.0.0.1:8000"
WS_URL = "ws://127.0.0.1:8000"

HTTP_TIMEOUT = 10
WS_TIMEOUT = 10


def assert_status(response, expected=200, endpoint=""):
    if response.status_code != expected:
        raise RuntimeError(
            f"{endpoint} returned {response.status_code}\n{response.text}"
        )


async def test_websocket_integration():
    logging.info("=" * 70)
    logging.info("TalkSense AI Integration Smoke Test")
    logging.info("=" * 70)

    session_id = None

    try:
        ###############################################################
        # Health Check
        ###############################################################

        logging.info("Checking backend health...")

        health = requests.get(
            f"{BASE_URL}/health",
            timeout=HTTP_TIMEOUT,
        )

        assert_status(health, endpoint="/health")

        logging.info("✓ Backend is healthy")

        ###############################################################
        # Create Session
        ###############################################################

        logging.info("Creating meeting session...")

        session = requests.post(
            f"{BASE_URL}/sessions",
            json={"mode": "sales"},
            timeout=HTTP_TIMEOUT,
        )

        assert_status(session, endpoint="/sessions")

        session_data = session.json()

        if "session_id" not in session_data:
            raise RuntimeError("Missing session_id")

        if "ws" not in session_data:
            raise RuntimeError("Missing websocket information")

        if "audio" not in session_data["ws"]:
            raise RuntimeError("Missing audio websocket path")

        session_id = session_data["session_id"]
        ws_uri = WS_URL + session_data["ws"]["audio"]

        logging.info(f"✓ Session created ({session_id})")

        ###############################################################
        # WebSocket
        ###############################################################

        logging.info("Connecting to WebSocket...")

        async with websockets.connect(
            ws_uri,
            open_timeout=WS_TIMEOUT,
            close_timeout=WS_TIMEOUT,
        ) as ws:

            logging.info("✓ WebSocket connected")

            payload = (
                "inject:Customer|"
                "The pricing is far too high for our budget right now."
            )

            logging.info("Injecting mock transcript...")

            await asyncio.wait_for(
                ws.send(payload),
                timeout=WS_TIMEOUT,
            )

            ###########################################################
            # Optional acknowledgement
            ###########################################################

            try:
                response = await asyncio.wait_for(
                    ws.recv(),
                    timeout=2,
                )

                logging.info(f"Received server response: {response}")

            except asyncio.TimeoutError:
                logging.info("No immediate WebSocket response " "(this is acceptable).")

            ###########################################################

            await asyncio.sleep(2)

            logging.info("Ending session...")

            await asyncio.wait_for(
                ws.send("end"),
                timeout=WS_TIMEOUT,
            )

        logging.info("✓ WebSocket test completed")

        ###############################################################
        # Dashboard Validation
        ###############################################################

        logging.info("Checking dashboard metrics...")

        dashboard = requests.get(
            f"{BASE_URL}/dashboard/{session_id}",
            timeout=HTTP_TIMEOUT,
        )

        assert_status(
            dashboard,
            endpoint="/dashboard",
        )

        dashboard_data = dashboard.json()

        objections = dashboard_data.get("objections", [])

        if not objections:
            raise RuntimeError("ConversationEngine produced zero objections.")

        logging.info(f"✓ Objection detected: {objections[0]}")

        ###############################################################
        # Optional transcript validation
        ###############################################################

        transcripts = (
            dashboard_data.get("transcripts") or dashboard_data.get("segments") or []
        )

        if transcripts:
            logging.info(f"✓ Transcript count: {len(transcripts)}")
        else:
            logging.info("Transcript list not exposed by dashboard API.")

        ###############################################################
        # Optional objection validation
        ###############################################################

        objection = objections[0]

        if isinstance(objection, dict):

            objection_type = objection.get("type")

            logging.info(f"Objection type: {objection_type}")

            expected = {
                "budget",
                "pricing",
                "cost",
            }

            if objection_type and objection_type.lower() not in expected:
                logging.warning("Unexpected objection category " f"'{objection_type}'")

        ###############################################################

        logging.info("=" * 70)
        logging.info("Integration Smoke Test PASSED")
        logging.info("=" * 70)

    except Exception:
        logging.exception("Smoke test failed")
        sys.exit(1)

    finally:
        ###############################################################
        # Cleanup
        ###############################################################

        if session_id:

            logging.info("Cleaning up session...")

            try:

                delete = requests.delete(
                    f"{BASE_URL}/sessions/{session_id}",
                    timeout=HTTP_TIMEOUT,
                )

                if delete.status_code == 200:
                    logging.info("✓ Session deleted")
                else:
                    logging.warning(f"Cleanup returned {delete.status_code}")

            except Exception as exc:
                logging.warning(f"Cleanup failed: {exc}")


if __name__ == "__main__":
    asyncio.run(test_websocket_integration())
