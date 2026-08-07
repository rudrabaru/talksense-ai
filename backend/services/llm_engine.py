import asyncio
import logging
from abc import ABC, abstractmethod

from google import genai  # type: ignore
from google.genai import errors  # type: ignore
from google.genai.types import GenerateContentConfig  # type: ignore

from core.config import get_settings

logger = logging.getLogger(__name__)

# ── Exception Hierarchy ───────────────────────────────────────────────────────


class LLMProviderError(Exception):
    """Base class for all LLM provider errors."""

    pass


class AuthenticationError(LLMProviderError):
    """Raised when the API key is invalid or missing."""

    pass


class ProviderTimeoutError(LLMProviderError):
    """Raised when the provider does not respond within the configured timeout."""

    pass


class RateLimitError(LLMProviderError):
    """Raised when the provider's rate limits are exceeded (HTTP 429)."""

    pass


class ProviderUnavailableError(LLMProviderError):
    """Raised when the provider is down or returns a 5xx error."""

    pass


# ── Provider Abstraction ──────────────────────────────────────────────────────


class BaseLLMProvider(ABC):
    @abstractmethod
    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
    ) -> str:
        pass


# ── Gemini Provider ───────────────────────────────────────────────────────────


class GeminiProvider(BaseLLMProvider):
    def __init__(self):
        settings = get_settings()
        self.api_key = settings.gemini_api_key
        self.model_name = settings.post_session_model
        self.timeout = settings.post_session_timeout

        if not self.api_key:
            raise AuthenticationError("GEMINI_API_KEY is not configured.")

        self.client = genai.Client(api_key=self.api_key)

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
    ) -> str:

        config = GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schema,
            system_instruction=system_prompt,
        )

        logger.info(
            f"Invoking Gemini Provider (Model: {self.model_name})",
            extra={
                "event": "llm_invoke",
                "provider": "gemini",
                "model": self.model_name,
            },
        )

        try:

            # google.genai async client
            response = await asyncio.wait_for(
                self.client.aio.models.generate_content(
                    model=self.model_name, contents=user_prompt, config=config
                ),
                timeout=self.timeout,
            )

            # Simple logging of success
            logger.info(
                "Gemini invocation successful",
                extra={
                    "event": "llm_success",
                    "provider": "gemini",
                    "model": self.model_name,
                },
            )

            return str(response.text or "")

        except asyncio.TimeoutError as e:
            logger.error("Gemini Provider timed out")
            raise ProviderTimeoutError(
                f"Provider did not respond within {self.timeout} seconds"
            ) from e
        except errors.APIError as e:
            # Handle rate limits, auth errors, and general API errors
            logger.error(f"Gemini API Error: {str(e)}")
            if "429" in str(e):
                raise RateLimitError("Rate limit exceeded") from e
            elif "403" in str(e) or "401" in str(e):
                raise AuthenticationError("Invalid API key or permissions") from e
            else:
                raise ProviderUnavailableError(f"Provider unavailable: {str(e)}") from e
        except Exception as e:
            logger.error(f"Unexpected error calling Gemini: {str(e)}")
            raise ProviderUnavailableError(f"Provider unavailable: {str(e)}") from e


# ── LLM Engine Facade ─────────────────────────────────────────────────────────


class LLMEngine:
    """
    Facade for interacting with LLM providers.
    Selects the correct provider based on configuration.
    """

    def __init__(self):
        settings = get_settings()
        self.provider_name = settings.post_session_provider.lower()

        if self.provider_name == "gemini":
            self.provider: BaseLLMProvider = GeminiProvider()
        else:
            raise ValueError(f"Unsupported POST_SESSION_PROVIDER: {self.provider_name}")

    async def generate_json(
        self,
        system_prompt: str,
        user_prompt: str,
        schema: dict,
    ) -> str:
        """
        Delegates JSON generation to the configured provider.
        """
        return await self.provider.generate_json(system_prompt, user_prompt, schema)
