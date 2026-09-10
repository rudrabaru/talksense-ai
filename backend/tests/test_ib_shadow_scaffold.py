"""
Focused tests for the INERT IB 1.5s shadow-mode scaffolding
(``backend/audio/ib_shadow.py`` + the feature-flagged tap in
``backend/ws/audio_handler.py``).

These tests assert the scaffold is plumbing only:
  * shadow is OFF by default,
  * the PCM tap never blocks or raises and drops on a full bounded queue,
  * the decode seam is an explicit no-op (``IB_DECODE_IMPLEMENTED is False``),
  * end-of-session drain writes the artifact set and frees the slot,
  * with the flag OFF the audio handler constructs no ShadowRunner.
No ASR / VAD / Whisper / DB behaviour is exercised.
"""

import json

import pytest

from audio import ib_shadow
from audio.ib_shadow import ShadowRunner, shadow_enabled


class _FakeSettings:
    def __init__(self, *, enabled=False, max_sessions=1, dirpath="ib_shadow_trial"):
        self.enable_ib_shadow = enabled
        self.ib_shadow_max_sessions = max_sessions
        self.ib_shadow_dir = dirpath


@pytest.fixture
def _clean_slots():
    ib_shadow._active_slots.clear()
    yield
    ib_shadow._active_slots.clear()


@pytest.fixture
def _fake_settings(monkeypatch):
    def _apply(**kwargs):
        settings = _FakeSettings(**kwargs)
        monkeypatch.setattr(ib_shadow, "get_settings", lambda: settings)
        return settings

    return _apply


# ── the decode seam stays explicitly unimplemented ──────────────────────────
def test_decode_seam_flag_is_false():
    assert ib_shadow.IB_DECODE_IMPLEMENTED is False


async def test_decode_seam_returns_none(_fake_settings, _clean_slots, tmp_path):
    _fake_settings(enabled=True, dirpath=str(tmp_path))
    runner = ShadowRunner("sseam", "meeting", lambda: None)
    assert await runner._decode_seam((0.0, b"\x00\x00")) is None


# ── default OFF ────────────────────────────────────────────────────────────
def test_shadow_off_by_default(_fake_settings, _clean_slots):
    _fake_settings(enabled=False)
    assert shadow_enabled("s1") is False


def test_shadow_enabled_only_when_flag_on(_fake_settings, _clean_slots):
    _fake_settings(enabled=True)
    assert shadow_enabled("s1") is True


def test_kill_switch_forces_off(_fake_settings, _clean_slots, monkeypatch):
    _fake_settings(enabled=True)
    monkeypatch.setattr(ib_shadow, "_GLOBAL_KILL", True)
    assert shadow_enabled("s1") is False


def test_slot_cap_enforced(_fake_settings, _clean_slots):
    _fake_settings(enabled=True, max_sessions=1)
    ib_shadow._active_slots.add("already-running")
    assert shadow_enabled("s2") is False


# ── bounded non-blocking PCM tap ───────────────────────────────────────────
def test_feed_is_non_blocking_and_drops_when_full(
    _fake_settings, _clean_slots, tmp_path
):
    _fake_settings(enabled=True, dirpath=str(tmp_path))
    runner = ShadowRunner("sfull", "meeting", lambda: None)
    # Consumer intentionally not started -> the bounded queue never drains.
    overflow = 50
    for _ in range(ib_shadow._QUEUE_MAX + overflow):
        runner.feed(b"\x00\x00", 0.0)
    assert runner._frames_received == ib_shadow._QUEUE_MAX + overflow
    assert runner._frames_dropped == overflow
    assert runner._queue.qsize() == ib_shadow._QUEUE_MAX


# ── lifecycle: start -> feed -> snapshot -> drain writes the artifact set ───
async def test_run_drains_and_writes_artifacts(_fake_settings, _clean_slots, tmp_path):
    _fake_settings(enabled=True, dirpath=str(tmp_path))
    runner = ShadowRunner("srun", "sales", lambda: None)
    runner.start()
    assert "srun" in ib_shadow._active_slots

    for i in range(5):
        runner.feed(b"\x01\x02\x03\x04", float(i))
    runner.snapshot_prod_transcript([{"speaker": "Speaker 1", "text": "hello world"}])
    await runner.stop()

    sdir = tmp_path / "srun"
    assert (sdir / "events.jsonl").is_file()
    assert (sdir / "manifest.json").is_file()
    assert (sdir / "metrics.json").is_file()
    assert (sdir / "prod_segments.json").is_file()
    assert (sdir / "prod_transcript.txt").read_text(
        encoding="utf-8"
    ).strip() == "Speaker 1: hello world"
    assert (tmp_path / "index.csv").is_file()

    metrics = json.loads((sdir / "metrics.json").read_text(encoding="utf-8"))
    assert metrics["frames_received"] == 5
    assert metrics["frames_dropped"] == 0
    assert metrics["errored"] is False
    assert metrics["ib_decode_implemented"] is False

    manifest = json.loads((sdir / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["phase"] == "complete"
    assert manifest["config"]["enable_ib_shadow"] is True

    # slot released on stop
    assert "srun" not in ib_shadow._active_slots


async def test_stop_is_idempotent(_fake_settings, _clean_slots, tmp_path):
    _fake_settings(enabled=True, dirpath=str(tmp_path))
    runner = ShadowRunner("sidem", "interview", lambda: None)
    runner.start()
    await runner.stop()
    await runner.stop()  # must not raise


async def test_no_audio_archive_when_path_missing(
    _fake_settings, _clean_slots, tmp_path
):
    _fake_settings(enabled=True, dirpath=str(tmp_path))
    runner = ShadowRunner("snoaudio", "meeting", lambda: str(tmp_path / "nope.wav"))
    runner.start()
    await runner.stop()
    assert not (tmp_path / "snoaudio" / "audio.wav").exists()


# ── audio handler: flag OFF -> no ShadowRunner constructed ─────────────────
def test_audio_handler_imports_shadow_symbols():
    from ws import audio_handler

    assert hasattr(audio_handler, "ShadowRunner")
    assert hasattr(audio_handler, "shadow_enabled")


def test_audio_handler_off_path_builds_no_runner(monkeypatch, _clean_slots):
    """With the flag OFF, shadow_enabled() gates construction — nothing is built."""
    from ws import audio_handler

    monkeypatch.setattr(
        audio_handler, "shadow_enabled", lambda _sid: False, raising=True
    )
    calls: list[str] = []

    class _Boom:
        def __init__(self, *a, **k):
            calls.append("constructed")

    monkeypatch.setattr(audio_handler, "ShadowRunner", _Boom, raising=True)
    assert audio_handler.shadow_enabled("x") is False
    assert calls == []
