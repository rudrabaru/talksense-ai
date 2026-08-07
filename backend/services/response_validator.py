import json
import re
import logging
from typing import Any
from pydantic import BaseModel, ConfigDict, Field, field_validator, ValidationError

logger = logging.getLogger(__name__)


class ActionItem(BaseModel):
    model_config = ConfigDict(extra="forbid")
    task: str
    assignee: str


class SpeakerMapEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    segment_id: str
    speaker: str


class RoleEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")
    speaker: str
    role: str


class PostSessionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    executive_summary: str
    speaker_map: list[SpeakerMapEntry] = Field(default_factory=list)
    roles: list[RoleEntry] = Field(default_factory=list)
    decisions: list[str] = Field(default_factory=list)
    action_items: list[ActionItem] = Field(default_factory=list)

    @field_validator("executive_summary")
    @classmethod
    def validate_summary_not_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("executive_summary cannot be empty")
        return v


def _extract_json(raw_text: str) -> str:
    """
    Extracts the first valid JSON block from a raw text string,
    accounting for potential markdown code blocks or surrounding text.

    Args:
        raw_text: The raw output from the LLM.

    Returns:
        The extracted JSON string.

    Raises:
        ValueError: If no JSON block can be found.
    """
    # 1. Attempt to find markdown JSON block: ```json ... ``` or ``` ... ```
    md_pattern = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)
    match = md_pattern.search(raw_text)
    if match:
        return match.group(1)

    # 2. Fallback to finding the first { and the last }
    start_idx = raw_text.find("{")
    end_idx = raw_text.rfind("}")

    if start_idx != -1 and end_idx != -1 and end_idx > start_idx:
        return raw_text[start_idx : end_idx + 1]

    raise ValueError("No valid JSON block detected in the response.")


def validate_and_parse(raw_text: str) -> dict[str, Any]:
    """
    Parses and validates the raw text output from the LLM into a strongly-typed dictionary.

    Pipeline:
    1. Extracts JSON string from raw text.
    2. Parses JSON string into a Python dict.
    3. Validates against PostSessionResponse Pydantic model.
    4. Applies business rules (e.g. no empty summary, default lists).
    5. Returns the validated dictionary dump.

    Args:
        raw_text: The raw string response from the LLM provider.

    Returns:
        A dictionary perfectly matching the PostSessionResponse schema.

    Raises:
        ValueError: If no JSON is found, or JSON is malformed.
        pydantic.ValidationError: If the schema or business rules are violated.
    """
    # 1. Extract JSON text
    json_str = _extract_json(raw_text)

    # 2. Parse JSON
    try:
        parsed_dict = json.loads(json_str)
    except json.JSONDecodeError as e:
        logger.error(
            f"Failed to parse extracted JSON: {str(e)}\nExtracted JSON: {json_str}"
        )
        raise ValueError(f"Malformed JSON: {str(e)}") from e

    # 3 & 4. Validate with Pydantic
    try:
        validated_model = PostSessionResponse.model_validate(parsed_dict)
    except ValidationError as e:
        logger.error(f"Pydantic validation failed: {str(e)}")
        raise e

    # 5. Return dict
    return validated_model.model_dump()
