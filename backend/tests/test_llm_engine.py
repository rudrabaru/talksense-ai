import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.genai import errors

from core.config import get_settings
from services.llm_engine import (
    AuthenticationError,
    GeminiProvider,
    LLMEngine,
    ProviderTimeoutError,
    ProviderUnavailableError,
    RateLimitError,
)


@pytest.fixture
def mock_settings():
    settings = get_settings()
    settings.gemini_api_key = "test_key"
    settings.post_session_provider = "gemini"
    settings.post_session_model = "gemini-1.5-flash"
    settings.post_session_timeout = 1
    return settings


@pytest.mark.asyncio
async def test_gemini_success(mock_settings, monkeypatch):
    class MockResponse:
        text = '{"success": true}'

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(return_value=MockResponse())

    with patch("services.llm_engine.genai.Client", return_value=mock_client):
        provider = GeminiProvider()
        result = await provider.generate_json("sys", "user", {"schema": "test"})
        assert result == '{"success": true}'


@pytest.mark.asyncio
async def test_gemini_timeout(mock_settings):
    async def slow_generation(*args, **kwargs):
        await asyncio.sleep(2)
        return "too late"

    mock_client = MagicMock()
    mock_client.aio.models.generate_content = slow_generation

    with patch("services.llm_engine.genai.Client", return_value=mock_client):
        provider = GeminiProvider()
        with pytest.raises(ProviderTimeoutError, match="Provider did not respond"):
            await provider.generate_json("sys", "user", {})


@pytest.mark.asyncio
async def test_gemini_authentication_error(mock_settings):
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=errors.APIError(403, {"message": "403 Forbidden"}, None)
    )

    with patch("services.llm_engine.genai.Client", return_value=mock_client):
        provider = GeminiProvider()
        with pytest.raises(AuthenticationError, match="Invalid API key"):
            await provider.generate_json("sys", "user", {})


@pytest.mark.asyncio
async def test_gemini_rate_limit(mock_settings):
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=errors.APIError(429, {"message": "429 Too Many Requests"}, None)
    )

    with patch("services.llm_engine.genai.Client", return_value=mock_client):
        provider = GeminiProvider()
        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            await provider.generate_json("sys", "user", {})


@pytest.mark.asyncio
async def test_gemini_service_unavailable(mock_settings):
    mock_client = MagicMock()
    mock_client.aio.models.generate_content = AsyncMock(
        side_effect=errors.APIError(503, {"message": "503 Backend Error"}, None)
    )

    with patch("services.llm_engine.genai.Client", return_value=mock_client):
        provider = GeminiProvider()
        with pytest.raises(ProviderUnavailableError, match="Provider unavailable"):
            await provider.generate_json("sys", "user", {})


def test_llm_engine_provider_selection(mock_settings):
    engine = LLMEngine()
    assert isinstance(engine.provider, GeminiProvider)


def test_llm_engine_unsupported_provider():
    settings = get_settings()
    settings.post_session_provider = "openai"
    with pytest.raises(ValueError, match="Unsupported POST_SESSION_PROVIDER: openai"):
        LLMEngine()


def test_gemini_provider_missing_key():
    settings = get_settings()
    settings.gemini_api_key = ""
    with pytest.raises(AuthenticationError, match="GEMINI_API_KEY is not configured"):
        GeminiProvider()


@pytest.mark.asyncio
async def test_llm_engine_facade(mock_settings):
    engine = LLMEngine()

    # Mock the provider's generate_json method directly
    engine.provider.generate_json = AsyncMock(return_value='{"facade": "success"}')

    res = await engine.generate_json("sys", "usr", {})
    assert res == '{"facade": "success"}'
    engine.provider.generate_json.assert_called_once_with("sys", "usr", {})
