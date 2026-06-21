from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import UUID

from jose import JWTError, jwt
from pydantic import BaseModel


class TokenPayload(BaseModel):
    sub: str
    role: str
    type: str
    exp: int | None = None


def create_access_token(
    *,
    user_id: UUID | str,
    role: str,
    secret_key: str,
    algorithm: str = "HS256",
    expire_minutes: int = 15,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=expire_minutes)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "access",
        "exp": expire,
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def create_refresh_token(
    *,
    user_id: UUID | str,
    role: str,
    secret_key: str,
    algorithm: str = "HS256",
    expire_days: int = 7,
) -> str:
    expire = datetime.now(timezone.utc) + timedelta(days=expire_days)
    payload = {
        "sub": str(user_id),
        "role": role,
        "type": "refresh",
        "exp": expire,
    }
    return jwt.encode(payload, secret_key, algorithm=algorithm)


def decode_token(token: str, secret_key: str, algorithm: str = "HS256") -> dict[str, Any]:
    try:
        return jwt.decode(token, secret_key, algorithms=[algorithm])
    except JWTError as exc:
        raise ValueError("Invalid token") from exc
