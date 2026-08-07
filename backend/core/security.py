import hmac
from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from core.config import get_settings


def create_ws_token(session_id: str) -> str:
    settings = get_settings()
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes)

    # Payload
    # sub: session_id
    # exp: expiration time
    # type: "ws_auth" to prevent reusing access tokens (if added later) for WS
    to_encode = {"sub": session_id, "exp": expire, "type": "ws_auth"}

    encoded_jwt = jwt.encode(
        to_encode, settings.jwt_secret_key, algorithm=settings.jwt_algorithm
    )
    return encoded_jwt


def verify_ws_token(token: str, session_id: str) -> bool:
    if not token:
        return False

    settings = get_settings()

    try:
        payload = jwt.decode(
            token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm]
        )

        # Verify token type
        if payload.get("type") != "ws_auth":
            return False

        token_session_id = payload.get("sub")
        if not token_session_id:
            return False

        # Verify ownership with constant time comparison
        return hmac.compare_digest(str(token_session_id), str(session_id))

    except JWTError:
        return False
