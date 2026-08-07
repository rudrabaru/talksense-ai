import pytest
import asyncio
from unittest.mock import AsyncMock, patch, MagicMock

from ws.session_manager import get_session_manager, SessionStatus
from core.config import get_settings


@pytest.fixture
def mock_settings():
    settings = get_settings()
    settings.enable_post_session_ai = False
    return settings


@pytest.fixture
def session_manager():
    sm = get_session_manager()
    sm._sessions.clear()
    return sm


@pytest.fixture
def mock_db_crud(monkeypatch):
    monkeypatch.setattr(
        "db.database.AsyncSessionLocal",
        MagicMock(return_value=AsyncMock()),
        raising=False,
    )
    monkeypatch.setattr(
        "ws.session_manager._flush_session_final", AsyncMock(), raising=False
    )
    monkeypatch.setattr(
        "ws.session_manager._register_flush_worker", MagicMock(), raising=False
    )

    mock_crud = MagicMock()
    for attr in dir(mock_crud):
        if not attr.startswith("_"):
            setattr(mock_crud, attr, AsyncMock())

    # specifically
    mock_crud.update_session_status = AsyncMock()
    mock_crud.update_session_audio_path = AsyncMock()
    mock_crud.get_session = AsyncMock()
    mock_crud.save_session_metrics_batch = AsyncMock()
    mock_crud.save_transcript_segments = AsyncMock()
    mock_crud.save_alerts_batch = AsyncMock()

    monkeypatch.setattr("db.crud", mock_crud, raising=False)

    import sys

    if "db.crud" not in sys.modules:
        sys.modules["db.crud"] = mock_crud


@pytest.fixture
def mock_pipeline(monkeypatch):
    mock_run = AsyncMock()
    monkeypatch.setattr(
        "services.post_session_pipeline.run_post_session_pipeline",
        mock_run,
        raising=False,
    )

    # We must also mock the internal import in end()
    # It imports run_post_session_pipeline from services.post_session_pipeline
    return mock_run


@pytest.mark.asyncio
async def test_post_session_ai_disabled(
    mock_settings, session_manager, mock_db_crud, mock_pipeline, monkeypatch
):
    mock_settings.enable_post_session_ai = False

    # Mocking FLUSH_SEMAPHORE as None means we skip final flush for DB testing,
    # but we still hit the DB persistence block in step 4.
    monkeypatch.setattr("ws.session_manager._FLUSH_SEMAPHORE", asyncio.Semaphore(1))

    session = session_manager.create("meeting")

    await session_manager.end(session.session_id, SessionStatus.COMPLETED)

    # Verify pipeline was NOT scheduled
    assert mock_pipeline.call_count == 0


@pytest.mark.asyncio
async def test_post_session_ai_enabled(
    mock_settings, session_manager, mock_db_crud, mock_pipeline, monkeypatch
):
    mock_settings.enable_post_session_ai = True
    monkeypatch.setattr("ws.session_manager._FLUSH_SEMAPHORE", asyncio.Semaphore(1))

    # Mock the run_post_session_diarization to avoid actual diarization logic
    monkeypatch.setattr(
        "ws.session_manager._run_post_session_diarization", AsyncMock(), raising=False
    )

    session = session_manager.create("meeting")

    with patch("ws.session_manager._register_flush_worker") as mock_register:
        await session_manager.end(session.session_id, SessionStatus.COMPLETED)

        # Verify pipeline WAS scheduled
        pipeline_scheduled = False
        for call in mock_register.call_args_list:
            task = call.args[0]
            if task.get_name().startswith("post-pipeline-"):
                pipeline_scheduled = True
                break

        assert (
            pipeline_scheduled
        ), "Pipeline was not scheduled when feature flag is enabled"
        assert mock_pipeline.call_count == 1


@pytest.mark.asyncio
async def test_post_session_ai_not_scheduled_on_failure(
    mock_settings, session_manager, mock_db_crud, mock_pipeline, monkeypatch
):
    mock_settings.enable_post_session_ai = True
    monkeypatch.setattr("ws.session_manager._FLUSH_SEMAPHORE", asyncio.Semaphore(1))

    session = session_manager.create("meeting")

    await session_manager.end(session.session_id, SessionStatus.FAILED)

    # Verify pipeline was NOT scheduled because status != COMPLETED
    assert mock_pipeline.call_count == 0


@pytest.mark.asyncio
async def test_post_session_ai_exception_does_not_break_cleanup(
    mock_settings, session_manager, mock_db_crud, mock_pipeline, monkeypatch
):
    mock_settings.enable_post_session_ai = True
    monkeypatch.setattr("ws.session_manager._FLUSH_SEMAPHORE", asyncio.Semaphore(1))
    monkeypatch.setattr(
        "ws.session_manager._run_post_session_diarization", AsyncMock(), raising=False
    )

    session = session_manager.create("meeting")

    # We mock run_post_session_pipeline to throw an error immediately
    mock_pipeline.side_effect = Exception("Simulated pipeline failure")

    try:
        await session_manager.end(session.session_id, SessionStatus.COMPLETED)
    except Exception as e:
        pytest.fail(f"end() raised exception: {e}")

    # The session should still be processed and removed
    assert session_manager.get(session.session_id) is None
