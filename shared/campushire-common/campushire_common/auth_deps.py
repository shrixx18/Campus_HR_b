import os
from dataclasses import dataclass
from uuid import UUID

from fastapi import Header, HTTPException, status
from jose import JWTError, jwt

from campushire_common.enums import UserRole


@dataclass
class CurrentUser:
    id: UUID
    role: UserRole


def _decode_bearer(authorization: str | None) -> CurrentUser | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    secret = os.environ.get("JWT_SECRET_KEY", "dev_secret_change_in_production")
    algorithm = os.environ.get("JWT_ALGORITHM", "HS256")
    try:
        payload = jwt.decode(token, secret, algorithms=[algorithm])
        if payload.get("type") != "access":
            return None
        return CurrentUser(id=UUID(payload["sub"]), role=UserRole(payload["role"]))
    except (JWTError, ValueError, KeyError):
        return None


def get_current_user(
    x_user_id: str | None = Header(default=None, alias="X-User-Id"),
    x_user_role: str | None = Header(default=None, alias="X-User-Role"),
    authorization: str | None = Header(default=None),
) -> CurrentUser:
    if x_user_id and x_user_role:
        try:
            return CurrentUser(id=UUID(x_user_id), role=UserRole(x_user_role))
        except (ValueError, KeyError) as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication headers",
            ) from exc

    user = _decode_bearer(authorization)
    if user:
        return user

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing authentication",
    )


def require_roles(*roles: UserRole):
    from fastapi import Depends

    def _check(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
        if user.role not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return user

    return _check
