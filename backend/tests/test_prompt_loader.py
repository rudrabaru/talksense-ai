import pytest
import os
import json
from services.prompt_loader import load_prompt_bundle


def test_valid_prompt_version():
    bundle = load_prompt_bundle("v1")
    assert "system_prompt" in bundle
    assert "user_prompt" in bundle
    assert "schema" in bundle
    assert isinstance(bundle["schema"], dict)


def test_missing_prompt_directory():
    with pytest.raises(FileNotFoundError, match="Prompt version directory not found"):
        load_prompt_bundle("v999_nonexistent")


def test_missing_files(tmp_path, monkeypatch):
    # Mock the directory resolution in prompt_loader
    # Instead of doing this, it's easier to create a fake version folder
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(current_dir)
    prompt_dir = os.path.join(backend_dir, "prompts", "post_session", "v_test_missing")

    os.makedirs(prompt_dir, exist_ok=True)
    try:
        with pytest.raises(FileNotFoundError, match="Missing required prompt file"):
            load_prompt_bundle("v_test_missing")
    finally:
        os.rmdir(prompt_dir)


def test_invalid_schema():
    current_dir = os.path.dirname(os.path.abspath(__file__))
    backend_dir = os.path.dirname(current_dir)
    prompt_dir = os.path.join(backend_dir, "prompts", "post_session", "v_test_invalid")

    os.makedirs(prompt_dir, exist_ok=True)
    try:
        with open(os.path.join(prompt_dir, "system.txt"), "w") as f:
            f.write("sys")
        with open(os.path.join(prompt_dir, "user.txt"), "w") as f:
            f.write("usr")
        with open(os.path.join(prompt_dir, "schema.json"), "w") as f:
            f.write("invalid { json")

        with pytest.raises(ValueError, match="Invalid JSON schema"):
            load_prompt_bundle("v_test_invalid")
    finally:
        for f in ["system.txt", "user.txt", "schema.json"]:
            path = os.path.join(prompt_dir, f)
            if os.path.exists(path):
                os.remove(path)
        os.rmdir(prompt_dir)
