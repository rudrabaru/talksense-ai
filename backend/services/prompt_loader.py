import os
import json
import logging

logger = logging.getLogger(__name__)


def load_prompt_bundle(version: str) -> dict:
    """
    Loads the system prompt, user prompt, and JSON schema from the
    specified prompt version directory.

    Returns a dict with:
    - system_prompt (str)
    - user_prompt (str)
    - schema (dict)
    """
    # Resolve absolute path based on this file's location
    # This file is in backend/services/prompt_loader.py
    # Prompts are in backend/prompts/post_session/<version>/
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(current_dir)
    prompt_dir = os.path.join(backend_dir, "prompts", "post_session", version)

    if not os.path.exists(prompt_dir) or not os.path.isdir(prompt_dir):
        raise FileNotFoundError(f"Prompt version directory not found: {prompt_dir}")

    system_path = os.path.join(prompt_dir, "system.txt")
    user_path = os.path.join(prompt_dir, "user.txt")
    schema_path = os.path.join(prompt_dir, "schema.json")

    # Validate required files
    for path in [system_path, user_path, schema_path]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing required prompt file: {path}")

    try:
        with open(system_path, "r", encoding="utf-8") as f:
            system_prompt = f.read().strip()

        with open(user_path, "r", encoding="utf-8") as f:
            user_prompt = f.read().strip()

        with open(schema_path, "r", encoding="utf-8") as f:
            schema = json.load(f)

    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON schema in {schema_path}: {str(e)}")

    logger.info(f"Successfully loaded post-session prompt bundle version: {version}")

    return {
        "system_prompt": system_prompt,
        "user_prompt": user_prompt,
        "schema": schema,
    }
