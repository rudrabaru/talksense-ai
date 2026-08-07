from collections import defaultdict
import time
from fastapi import HTTPException, Request

# In-memory store: IP -> list of timestamps
_request_records = defaultdict(list)

# Max requests per minute per IP for REST endpoints
MAX_REQUESTS_PER_MINUTE = 60


async def rate_limit_dependency(request: Request):
    ip = request.client.host if request.client else "unknown"
    now = time.time()

    # Clean up old records
    _request_records[ip] = [t for t in _request_records[ip] if now - t < 60]

    if len(_request_records[ip]) >= MAX_REQUESTS_PER_MINUTE:
        raise HTTPException(status_code=429, detail="Too Many Requests")

    _request_records[ip].append(now)
    return True


# Active sessions per IP for concurrent limit
_active_sessions_per_ip = defaultdict(int)
MAX_CONCURRENT_SESSIONS_PER_IP = 5


def check_concurrent_limit(ip: str):
    if _active_sessions_per_ip[ip] >= MAX_CONCURRENT_SESSIONS_PER_IP:
        raise HTTPException(
            status_code=429, detail="Too many concurrent sessions from this IP"
        )
    _active_sessions_per_ip[ip] += 1


def release_concurrent_limit(ip: str):
    if _active_sessions_per_ip[ip] > 0:
        _active_sessions_per_ip[ip] -= 1
