import os

import pytest
from httpx import AsyncClient, ASGITransport

from db import crud
from db.database import engine, AsyncSessionLocal
from db.models import Base
from main import app


@pytest.mark.asyncio
async def test_audio_playback_valid_session():
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        # Create a session
        res = await ac.post("/sessions", json={"mode": "meeting"})
        assert res.status_code == 200
        session_id = res.json()["session_id"]

        # End it
        await ac.delete(f"/sessions/{session_id}")

        # Create a dummy audio file
        test_dir = os.path.abspath("session_audio")
        os.makedirs(test_dir, exist_ok=True)
        dummy_path = os.path.join(test_dir, f"test_{session_id}.wav")
        with open(dummy_path, "wb") as f:
            f.write(
                b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00\x80\xbb\x00\x00\x00\xee\x02\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
            )

        # Update db manually
        from db.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            db_sess = await crud.get_session(session, session_id)
            assert db_sess is not None
            db_sess.audio_file_path = dummy_path
            await session.commit()

        # 1. completed session with valid audio + 5. correct media type
        res_audio = await ac.get(f"/sessions/{session_id}/audio")
        assert res_audio.status_code == 200
        assert res_audio.headers["content-type"] == "audio/wav"

        # 7. range behavior
        res_range = await ac.get(
            f"/sessions/{session_id}/audio", headers={"Range": "bytes=0-10"}
        )
        assert res_range.status_code == 206
        assert "content-range" in res_range.headers

        # Clean up
        if os.path.exists(dummy_path):
            os.remove(dummy_path)


@pytest.mark.asyncio
async def test_audio_playback_unknown_session():
    # 2. unknown session
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.get("/sessions/00000000-0000-0000-0000-000000000000/audio")
        assert res.status_code == 404


@pytest.mark.asyncio
async def test_audio_playback_no_audio():
    # 3. session without audio
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.post("/sessions", json={"mode": "meeting"})
        session_id = res.json()["session_id"]

        res_audio = await ac.get(f"/sessions/{session_id}/audio")
        assert res_audio.status_code == 404
        assert "No audio recording exists" in res_audio.json()["error"]


@pytest.mark.asyncio
async def test_audio_playback_missing_file():
    # 4. missing physical file
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.post("/sessions", json={"mode": "meeting"})
        session_id = res.json()["session_id"]

        from db.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            db_sess = await crud.get_session(session, session_id)
            assert db_sess is not None
            db_sess.audio_file_path = os.path.abspath("session_audio/doesnotexist.wav")
            await session.commit()

        res_audio = await ac.get(f"/sessions/{session_id}/audio")
        assert res_audio.status_code == 404
        assert "is missing from storage" in res_audio.json()["error"]


@pytest.mark.asyncio
async def test_audio_playback_path_safety():
    # 6. path safety
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        res = await ac.post("/sessions", json={"mode": "meeting"})
        session_id = res.json()["session_id"]

        from db.database import AsyncSessionLocal

        async with AsyncSessionLocal() as session:
            db_sess = await crud.get_session(session, session_id)
            assert db_sess is not None
            db_sess.audio_file_path = os.path.abspath("../secret_file.txt")
            await session.commit()

        # Create dummy file outside session_audio
        dummy = os.path.abspath("../secret_file.txt")
        with open(dummy, "w") as f:
            f.write("secret")

        res_audio = await ac.get(f"/sessions/{session_id}/audio")
        assert res_audio.status_code == 403
        assert "Invalid audio path" in res_audio.json()["error"]

        os.remove(dummy)
