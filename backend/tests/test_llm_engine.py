import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from google.api_core.exceptions import (
    PermissionDenied,
    ResourceExhausted,
    ServiceUnavailable,
)

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
    provider = GeminiProvider()

    class MockResponse:
        text = '{"success": true}'

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(return_value=MockResponse())

    with patch("google.generativeai.GenerativeModel", return_value=mock_model):
        result = await provider.generate_json("sys", "user", {"schema": "test"})
        assert result == '{"success": true}'


@pytest.mark.asyncio
async def test_gemini_timeout(mock_settings):
    provider = GeminiProvider()

    async def slow_generation(*args, **kwargs):
        await asyncio.sleep(2)
        return "too late"

    mock_model = MagicMock()
    mock_model.generate_content_async = slow_generation

    with patch("google.generativeai.GenerativeModel", return_value=mock_model):
        with pytest.raises(ProviderTimeoutError, match="Provider did not respond"):
            await provider.generate_json("sys", "user", {})


@pytest.mark.asyncio
async def test_gemini_authentication_error(mock_settings):
    provider = GeminiProvider()

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(
        side_effect=PermissionDenied("Bad key")
    )

    with patch("google.generativeai.GenerativeModel", return_value=mock_model):
        with pytest.raises(AuthenticationError, match="Invalid API key"):
            await provider.generate_json("sys", "user", {})


@pytest.mark.asyncio
async def test_gemini_rate_limit(mock_settings):
    provider = GeminiProvider()

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(
        side_effect=ResourceExhausted("Quota exceeded")
    )

    with patch("google.generativeai.GenerativeModel", return_value=mock_model):
        with pytest.raises(RateLimitError, match="Rate limit exceeded"):
            await provider.generate_json("sys", "user", {})


@pytest.mark.asyncio
async def test_gemini_service_unavailable(mock_settings):
    provider = GeminiProvider()

    mock_model = MagicMock()
    mock_model.generate_content_async = AsyncMock(
        side_effect=ServiceUnavailable("503 Backend Error")
    )

    with patch("google.generativeai.GenerativeModel", return_value=mock_model):
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
