import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.config import get_settings
from services.llm_engine import AuthenticationError, ProviderTimeoutError
from services.post_session_pipeline import _LLM_SEMAPHORE, run_post_session_pipeline


@pytest.fixture
def mock_settings():
    settings = get_settings()
    settings.enable_post_session_ai = True
    settings.post_session_provider = "gemini"
    settings.post_session_model = "gemini-1.5-flash"
    settings.post_session_prompt_version = "v1"
    return settings


@pytest.fixture
def mock_db():
    db_mock = AsyncMock()
    # Mock context manager
    db_mock.__aenter__.return_value = db_mock
    db_mock.__aexit__.return_value = False
    return db_mock


@pytest.fixture
def mock_crud_get_transcript(monkeypatch):
    class MockSegment:
        def __init__(self):
            self.start_time = 0.0
            self.end_time = 1.0
            self.text = "Hello"
            self.speaker_id = "Speaker 1"

    mock = AsyncMock(return_value=[MockSegment()])
    monkeypatch.setattr("db.crud.get_transcript_segments", mock)
    return mock


@pytest.fixture
def mock_crud_save_analysis(monkeypatch):
    mock = AsyncMock()
    monkeypatch.setattr("db.crud.save_analysis_result", mock)
    return mock


@pytest.fixture
def mock_prompt_loader(monkeypatch):
    mock = MagicMock(
        return_value={"system_prompt": "sys", "user_prompt": "user", "schema": {}}
    )
    monkeypatch.setattr("services.post_session_pipeline.load_prompt_bundle", mock)
    return mock


@pytest.mark.asyncio
async def test_successful_execution(
    mock_settings,
    mock_db,
    mock_crud_get_transcript,
    mock_crud_save_analysis,
    mock_prompt_loader,
    monkeypatch,
):
    monkeypatch.setattr(
        "services.post_session_pipeline.AsyncSessionLocal",
        MagicMock(return_value=mock_db),
    )

    mock_engine_cls = MagicMock()
    mock_engine_inst = MagicMock()
    mock_engine_inst.generate_json = AsyncMock(
        return_value='{"executive_summary": "success"}'
    )
    mock_engine_cls.return_value = mock_engine_inst
    monkeypatch.setattr("services.post_session_pipeline.LLMEngine", mock_engine_cls)

    import uuid

    valid_uuid = str(uuid.uuid4())
    await run_post_session_pipeline(valid_uuid)

    # Assert DB flow
    mock_crud_get_transcript.assert_called_once()
    mock_crud_save_analysis.assert_called_once()

    args, kwargs = mock_crud_save_analysis.call_args
    assert kwargs["summary"] == "success"
    assert kwargs["report_json"]["executive_summary"] == "success"
    mock_db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_timeout_recovery_retry(
    mock_settings,
    mock_db,
    mock_crud_get_transcript,
    mock_crud_save_analysis,
    mock_prompt_loader,
    monkeypatch,
):
    monkeypatch.setattr(
        "services.post_session_pipeline.AsyncSessionLocal",
        MagicMock(return_value=mock_db),
    )

    mock_engine_cls = MagicMock()
    mock_engine_inst = MagicMock()

    # Fail first time, succeed second time
    mock_engine_inst.generate_json = AsyncMock(
        side_effect=[
            ProviderTimeoutError("timeout"),
            '{"executive_summary": "recovered"}',
        ]
    )
    mock_engine_cls.return_value = mock_engine_inst
    monkeypatch.setattr("services.post_session_pipeline.LLMEngine", mock_engine_cls)

    # Fast forward tenacity waits for testing

    monkeypatch.setattr("tenacity.nap.time.sleep", MagicMock())
    monkeypatch.setattr(asyncio, "sleep", AsyncMock())

    import uuid

    valid_uuid = str(uuid.uuid4())
    await run_post_session_pipeline(valid_uuid)

    assert mock_engine_inst.generate_json.call_count == 2
    args, kwargs = mock_crud_save_analysis.call_args
    assert kwargs["summary"] == "recovered"


@pytest.mark.asyncio
async def test_authentication_failure_no_retry(
    mock_settings,
    mock_db,
    mock_crud_get_transcript,
    mock_crud_save_analysis,
    mock_prompt_loader,
    monkeypatch,
):
    monkeypatch.setattr(
        "services.post_session_pipeline.AsyncSessionLocal",
        MagicMock(return_value=mock_db),
    )

    mock_engine_cls = MagicMock()
    mock_engine_inst = MagicMock()

    # AuthenticationError should not be retried based on retry_if_exception_type
    mock_engine_inst.generate_json = AsyncMock(
        side_effect=AuthenticationError("bad key")
    )
    mock_engine_cls.return_value = mock_engine_inst
    monkeypatch.setattr("services.post_session_pipeline.LLMEngine", mock_engine_cls)

    import uuid

    valid_uuid = str(uuid.uuid4())
    await run_post_session_pipeline(valid_uuid)

    # Called exactly once, no retries
    assert mock_engine_inst.generate_json.call_count == 1

    # Should save fallback
    args, kwargs = mock_crud_save_analysis.call_args
    assert kwargs["summary"] == "AI summary unavailable."


@pytest.mark.asyncio
async def test_db_rollback_on_fatal_error(
    mock_settings, mock_db, mock_crud_get_transcript, monkeypatch
):
    monkeypatch.setattr(
        "services.post_session_pipeline.AsyncSessionLocal",
        MagicMock(return_value=mock_db),
    )

    # Force the transcript fetch to throw an unexpected error
    mock_crud_get_transcript.side_effect = Exception("DB disconnected")

    import uuid

    valid_uuid = str(uuid.uuid4())
    await run_post_session_pipeline(valid_uuid)

    # Rollback must be called
    mock_db.rollback.assert_called_once()


@pytest.mark.asyncio
async def test_semaphore_limit(
    mock_settings,
    mock_db,
    mock_crud_get_transcript,
    mock_crud_save_analysis,
    mock_prompt_loader,
    monkeypatch,
):
    monkeypatch.setattr(
        "services.post_session_pipeline.AsyncSessionLocal",
        MagicMock(return_value=mock_db),
    )

    mock_engine_cls = MagicMock()
    mock_engine_inst = MagicMock()
    mock_engine_inst.generate_json = AsyncMock(
        return_value='{"executive_summary": "success"}'
    )
    mock_engine_cls.return_value = mock_engine_inst
    monkeypatch.setattr("services.post_session_pipeline.LLMEngine", mock_engine_cls)

    assert _LLM_SEMAPHORE._value == 20
    import uuid

    valid_uuid = str(uuid.uuid4())
    await run_post_session_pipeline(valid_uuid)
    # Should be released
    assert _LLM_SEMAPHORE._value == 20
