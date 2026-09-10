"""
TalkSense AI — IB 1.5s Shadow-Mode Scaffolding (INERT)

Feature-flagged, default OFF. Pure plumbing for a future "independent-buffer" (IB)
shadow ASR trial:

  * a bounded, non-blocking PCM tap off the live receive loop
  * a per-session queue + single consumer task with a safe end-of-session drain
  * file-based telemetry / production-transcript snapshot / audio archival under
    ``<ib_shadow_dir>/<session_id>/``

This module deliberately contains NO ASR / VAD / Whisper / decoding /
buffering-for-decode logic. :meth:`ShadowRunner._decode_seam` is the single,
explicitly unimplemented integration point. Wiring it to the validated
``ib_stabilizer.py`` (SHA-256
``5568cb85bb57131c1ae346ab3b4bcb4c54aab9057c4553a90e4f088063f0600e``) and its
dependency modules (``stab_generalize`` / ``stab_nrng`` / ``stab_common``) is a
separate, approved task gated on dependency-provenance sign-off — those files are
NOT vendored or referenced here.

With ``enable_ib_shadow`` OFF (the default) nothing in this module runs: the audio
handler never constructs a :class:`ShadowRunner`.
"""

from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import logging
import subprocess
import time
from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, TextIO

from core.config import get_settings

logger = logging.getLogger(__name__)

# Flips to True ONLY when the validated IB stabilizer is actually wired into
# ``ShadowRunner._decode_seam`` by a future, separately-approved change.
IB_DECODE_IMPLEMENTED = False

_QUEUE_MAX = 256  # frames; bounded backpressure for the PCM tap
_DRAIN_TIMEOUT_S = 2.0  # bound on the end-of-session consumer drain
_CONSUMER_POLL_S = 0.2  # queue.get timeout so stop() drains promptly

# Process-wide slot accounting + runtime kill switch (no restart needed).
_active_slots: set[str] = set()
_GLOBAL_KILL = False


def shadow_enabled(session_id: str) -> bool:
    """True only if the flag is on, the kill switch is off, and a slot is free."""
    try:
        settings = get_settings()
    except Exception:  # pragma: no cover - defensive
        return False
    if not getattr(settings, "enable_ib_shadow", False):
        return False
    if _GLOBAL_KILL:
        return False
    max_sessions = int(getattr(settings, "ib_shadow_max_sessions", 1) or 1)
    return len(_active_slots) < max_sessions


class ShadowRunner:
    """Per-session inert shadow pipeline. Constructed only when shadow_enabled()."""

    def __init__(
        self,
        session_id: str,
        mode: str,
        wav_path_getter: Callable[[], str | None],
    ) -> None:
        self.session_id = session_id
        self.mode = mode
        self._wav_path_getter = wav_path_getter

        settings = get_settings()
        self._root = Path(str(getattr(settings, "ib_shadow_dir", "ib_shadow_trial")))
        self._dir = self._root / session_id

        self._queue: asyncio.Queue[tuple[float, bytes]] = asyncio.Queue(
            maxsize=_QUEUE_MAX
        )
        self._stopping = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._events_fh: TextIO | None = None

        # counters / state
        self._frames_received = 0
        self._frames_dropped = 0
        self._bytes_received = 0
        self._queue_high_water = 0
        self._errored = False
        self._started_monotonic: float | None = None
        self._wall_start: str | None = None
        self._git_head: str | None = None
        self._stopped = False
        self._decode_seam_logged = False

    # ── lifecycle ────────────────────────────────────────────────────────────
    def start(self) -> None:
        """Register a slot, open telemetry, spawn the consumer. Never raises."""
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            self._events_fh = open(self._dir / "events.jsonl", "a", encoding="utf-8")
            self._git_head = _git_head()
            self._started_monotonic = time.monotonic()
            self._wall_start = _now_iso()
            _active_slots.add(self.session_id)
            self._write_manifest(phase="start")
            self._log_event("consumer_start")
            self._task = asyncio.create_task(
                self._consumer(), name=f"ib-shadow-{self.session_id[:8]}"
            )
        except Exception:  # pragma: no cover - defensive
            logger.warning(
                "IB shadow %s: start failed; shadow inert",
                self.session_id[:8],
                exc_info=True,
            )
            _active_slots.discard(self.session_id)

    def feed(self, pcm_bytes: bytes, recv_monotonic: float) -> None:
        """Non-blocking PCM tap. Enqueues the raw bytes ref; drops on a full queue.

        Called from the WS receive-loop hot path — must never block or raise.
        """
        self._frames_received += 1
        self._bytes_received += len(pcm_bytes)
        try:
            self._queue.put_nowait((recv_monotonic, pcm_bytes))
        except asyncio.QueueFull:
            self._frames_dropped += 1
            return
        depth = self._queue.qsize()
        if depth > self._queue_high_water:
            self._queue_high_water = depth

    async def stop(self, timeout: float = _DRAIN_TIMEOUT_S) -> None:
        """Signal, drain (bounded), write rollups, archive audio, free the slot.

        Idempotent and non-fatal: any failure here is logged, never raised.
        """
        if self._stopped:
            return
        self._stopped = True
        self._stopping.set()

        if self._task is not None:
            try:
                await asyncio.wait_for(asyncio.shield(self._task), timeout=timeout)
            except (asyncio.TimeoutError, asyncio.CancelledError):
                self._task.cancel()
                try:
                    await self._task
                except asyncio.CancelledError:
                    pass
                except Exception:  # pragma: no cover - defensive
                    logger.warning(
                        "IB shadow %s: consumer cancel raised",
                        self.session_id[:8],
                        exc_info=True,
                    )

        try:
            self._log_event(
                "consumer_stop",
                frames_received=self._frames_received,
                frames_dropped=self._frames_dropped,
                errored=self._errored,
            )
            wav_sha, wav_bytes = self._archive_audio()
            self._write_metrics(wav_sha, wav_bytes)
            self._write_manifest(phase="complete", wav_sha=wav_sha, wav_bytes=wav_bytes)
            self._append_index(wav_sha, wav_bytes)
        except Exception:  # pragma: no cover - defensive
            logger.warning(
                "IB shadow %s: stop rollup failed",
                self.session_id[:8],
                exc_info=True,
            )
        finally:
            _active_slots.discard(self.session_id)
            if self._events_fh is not None:
                try:
                    self._events_fh.close()
                except Exception:  # pragma: no cover - defensive
                    pass
                self._events_fh = None

    # ── consumer + the explicitly unimplemented seam ────────────────────────
    async def _consumer(self) -> None:
        try:
            while True:
                try:
                    frame = await asyncio.wait_for(
                        self._queue.get(), timeout=_CONSUMER_POLL_S
                    )
                except asyncio.TimeoutError:
                    if self._stopping.is_set() and self._queue.empty():
                        return
                    continue
                recv_monotonic, pcm = frame
                self._log_event(
                    "chunk_received",
                    bytes=len(pcm),
                    queue_depth=self._queue.qsize(),
                    frames_dropped=self._frames_dropped,
                    lag_s=round(time.monotonic() - recv_monotonic, 4),
                )
                await self._decode_seam(frame)
        except Exception:  # shadow must never crash production
            self._errored = True
            logger.warning(
                "IB shadow %s: consumer aborted; shadow disabled",
                self.session_id[:8],
                exc_info=True,
            )

    async def _decode_seam(self, frame: tuple[float, bytes]) -> None:
        """EXPLICIT UNIMPLEMENTED SEAM — intentionally a no-op.

        This is the single integration point for the validated IB stabilizer. It
        stays a no-op until a separate, approved task wires ``ib_stabilizer.py``
        (SHA-256 ``5568cb85bb57131c1ae346ab3b4bcb4c54aab9057c4553a90e4f088063f0600e``)
        under the existing GPU semaphore and Whisper singleton. The three
        dependency modules (``stab_generalize`` / ``stab_nrng`` / ``stab_common``)
        have no published reference SHA and are NOT vendored.

        Do NOT add ASR / VAD / decoding here without that approval.
        """
        if not self._decode_seam_logged:
            self._decode_seam_logged = True
            logger.info(
                "IB shadow %s: decode seam is a no-op (IB_DECODE_IMPLEMENTED=%s)",
                self.session_id[:8],
                IB_DECODE_IMPLEMENTED,
            )
        return None

    # ── production-output snapshot ─────────────────────────────────────────
    def snapshot_prod_transcript(self, segments: list[dict[str, Any]]) -> None:
        """Write a read-only copy of the production transcript at session end."""
        try:
            self._dir.mkdir(parents=True, exist_ok=True)
            (self._dir / "prod_segments.json").write_text(
                json.dumps(segments, indent=1, default=str), encoding="utf-8"
            )
            lines = [
                f"{seg.get('speaker', '?')}: {seg.get('text', '')}".rstrip()
                for seg in segments
            ]
            body = "\n".join(lines)
            if body:
                body += "\n"
            (self._dir / "prod_transcript.txt").write_text(body, encoding="utf-8")
        except Exception:  # pragma: no cover - defensive
            logger.warning(
                "IB shadow %s: prod transcript snapshot failed",
                self.session_id[:8],
                exc_info=True,
            )

    # ── helpers ───────────────────────────────────────────────────────────
    def _log_event(self, kind: str, **fields: Any) -> None:
        if self._events_fh is None:
            return
        row = {
            "t_wall": _now_iso(),
            "t_monotonic": round(time.monotonic(), 4),
            "session_id": self.session_id,
            "kind": kind,
            **fields,
        }
        try:
            self._events_fh.write(json.dumps(row, default=str) + "\n")
            self._events_fh.flush()
        except Exception:  # pragma: no cover - defensive
            pass

    def _archive_audio(self) -> tuple[str | None, int | None]:
        try:
            raw = self._wav_path_getter()
        except Exception:  # pragma: no cover - defensive
            raw = None
        if not raw:
            return None, None
        src = Path(raw)
        if not src.is_file():
            return None, None
        try:
            data = src.read_bytes()
            (self._dir / "audio.wav").write_bytes(data)
            return hashlib.sha256(data).hexdigest(), len(data)
        except Exception:  # pragma: no cover - defensive
            logger.warning(
                "IB shadow %s: audio archive failed",
                self.session_id[:8],
                exc_info=True,
            )
            return None, None

    def _config_snapshot(self) -> dict[str, Any]:
        settings = get_settings()
        return {
            "enable_ib_shadow": bool(getattr(settings, "enable_ib_shadow", False)),
            "ib_shadow_max_sessions": int(
                getattr(settings, "ib_shadow_max_sessions", 1)
            ),
            "ib_shadow_dir": str(getattr(settings, "ib_shadow_dir", "ib_shadow_trial")),
        }

    def _write_manifest(
        self,
        phase: str,
        wav_sha: str | None = None,
        wav_bytes: int | None = None,
    ) -> None:
        payload: dict[str, Any] = {
            "session_id": self.session_id,
            "mode": self.mode,
            "phase": phase,
            "git_head": self._git_head,
            "wall_start": self._wall_start,
            "ib_decode_implemented": IB_DECODE_IMPLEMENTED,
            "config": self._config_snapshot(),
        }
        if phase == "complete":
            payload["wall_end"] = _now_iso()
            payload["frames_received"] = self._frames_received
            payload["frames_dropped"] = self._frames_dropped
            payload["bytes_received"] = self._bytes_received
            payload["queue_high_water"] = self._queue_high_water
            payload["errored"] = self._errored
            payload["wav_sha256"] = wav_sha
            payload["wav_bytes"] = wav_bytes
        try:
            (self._dir / "manifest.json").write_text(
                json.dumps(payload, indent=1), encoding="utf-8"
            )
        except Exception:  # pragma: no cover - defensive
            pass

    def _write_metrics(self, wav_sha: str | None, wav_bytes: int | None) -> None:
        wall = (
            round(time.monotonic() - self._started_monotonic, 3)
            if self._started_monotonic is not None
            else None
        )
        payload = {
            "session_id": self.session_id,
            "mode": self.mode,
            "frames_received": self._frames_received,
            "frames_dropped": self._frames_dropped,
            "bytes_received": self._bytes_received,
            "queue_high_water": self._queue_high_water,
            "queue_max": _QUEUE_MAX,
            "errored": self._errored,
            "consumer_wall_s": wall,
            "ib_decode_implemented": IB_DECODE_IMPLEMENTED,
            "wav_sha256": wav_sha,
            "wav_bytes": wav_bytes,
        }
        try:
            (self._dir / "metrics.json").write_text(
                json.dumps(payload, indent=1), encoding="utf-8"
            )
        except Exception:  # pragma: no cover - defensive
            pass

    def _append_index(self, wav_sha: str | None, wav_bytes: int | None) -> None:
        header = [
            "session_id",
            "mode",
            "wall_end",
            "frames_received",
            "frames_dropped",
            "bytes_received",
            "queue_high_water",
            "errored",
            "ib_decode_implemented",
            "wav_sha256",
            "wav_bytes",
        ]
        row = [
            self.session_id,
            self.mode,
            _now_iso(),
            self._frames_received,
            self._frames_dropped,
            self._bytes_received,
            self._queue_high_water,
            self._errored,
            IB_DECODE_IMPLEMENTED,
            wav_sha or "",
            "" if wav_bytes is None else wav_bytes,
        ]
        try:
            self._root.mkdir(parents=True, exist_ok=True)
            index = self._root / "index.csv"
            is_new = not index.is_file()
            with open(index, "a", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                if is_new:
                    writer.writerow(header)
                writer.writerow(row)
        except Exception:  # pragma: no cover - defensive
            pass


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _git_head() -> str | None:
    try:
        proc = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            timeout=2,
            check=False,
        )
        return proc.stdout.strip() or None
    except Exception:  # pragma: no cover - defensive
        return None
