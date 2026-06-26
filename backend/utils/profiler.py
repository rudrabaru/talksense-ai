import logging
import time
from contextlib import contextmanager
from typing import Dict, Generator, Optional

from core.config import get_settings

logger = logging.getLogger("profiler")


class SessionProfiler:
    """
    Session-level performance profiler.
    Measures and aggregates timings for different stages in the pipeline.
    """

    def __init__(self, session_id: str):
        self.session_id = session_id
        self.timings: Dict[str, float] = {}
        self.start_time: float = time.perf_counter()
        try:
            self.enabled: bool = get_settings().profiling_enabled
        except Exception:
            self.enabled = (
                True  # fallback to True if config loader fails during bootstrap
            )

    @contextmanager
    def profile(self, stage_name: str) -> Generator[None, None, None]:
        if not self.enabled:
            yield
            return
        t0 = time.perf_counter()
        try:
            yield
        finally:
            elapsed = (time.perf_counter() - t0) * 1000  # convert to ms
            self.timings[stage_name] = self.timings.get(stage_name, 0.0) + elapsed

    def log_results(self) -> None:
        if not self.enabled or not self.timings:
            return

        total_time = (time.perf_counter() - self.start_time) * 1000

        lines = []
        lines.append("")
        lines.append("[PROFILE]")
        lines.append("")

        for stage, duration in self.timings.items():
            dots = "." * max(2, 25 - len(stage))
            lines.append(f"{stage}{dots}{round(duration)} ms")

        lines.append("----------------------------")
        dots_total = "." * (25 - 5)
        lines.append(f"TOTAL{dots_total}{round(total_time)} ms")
        lines.append("")

        # Log to logger info
        logger.info("\n".join(lines))


# ── Global Profiler Registry ──────────────────────────────────────────────────

_profilers: Dict[str, SessionProfiler] = {}


def register_profiler(session_id: str) -> SessionProfiler:
    """Create and register a profiler for the given session_id."""
    profiler = SessionProfiler(session_id)
    _profilers[session_id] = profiler
    return profiler


def get_profiler(session_id: str) -> Optional[SessionProfiler]:
    """Retrieve the profiler for the session_id, if registered."""
    return _profilers.get(session_id)


def unregister_profiler(session_id: str) -> None:
    """Unregister and discard the profiler for the session_id."""
    _profilers.pop(session_id, None)


@contextmanager
def profile_stage(
    session_id: Optional[str], stage_name: str
) -> Generator[None, None, None]:
    """
    Context manager to profile a stage for a session.
    If session_id is None, unregistered, or profiling is disabled,
    operates with negligible overhead.
    """
    if not session_id:
        yield
        return

    profiler = get_profiler(session_id)
    if profiler and profiler.enabled:
        with profiler.profile(stage_name):
            yield
    else:
        yield
