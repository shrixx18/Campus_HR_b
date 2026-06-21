import uuid
from datetime import datetime, timedelta, timezone

import redis
from fastapi import Header, HTTPException, status
from jose import JWTError, jwt
from sqlalchemy.orm import Session

from app.config import settings
from app.models import RefreshToken, StudentProfile, User
from app.schemas import ProfileUpdate, RegisterRequest
from campushire_common.enums import UserRole
from campushire_common.jwt import create_access_token, create_refresh_token
from campushire_common.security import hash_password, verify_password


def get_redis() -> redis.Redis:
    return redis.Redis(
        host=settings.redis_host,
        port=settings.redis_port,
        password=settings.redis_password or None,
        decode_responses=True,
    )


def register_user(db: Session, data: RegisterRequest) -> User:
    if db.query(User).filter(User.email == data.email).first():
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    db.flush()
    if data.role == UserRole.STUDENT:
        db.add(StudentProfile(user_id=user.id))
    db.commit()
    db.refresh(user)
    return user


def authenticate(db: Session, email: str, password: str) -> User:
    user = db.query(User).filter(User.email == email).first()
    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Account disabled")
    return user


def issue_tokens(db: Session, user: User) -> tuple[str, str]:
    access = create_access_token(
        user_id=user.id,
        role=user.role.value,
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.access_token_expire_minutes,
    )
    refresh = create_refresh_token(
        user_id=user.id,
        role=user.role.value,
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expire_days=settings.refresh_token_expire_days,
    )
    payload = jwt.get_unverified_claims(refresh)
    jti = payload.get("jti") or str(uuid.uuid4())
    db.add(
        RefreshToken(
            user_id=user.id,
            token_jti=jti,
            expires_at=datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days),
        )
    )
    db.commit()
    return access, refresh


def refresh_access_token(db: Session, refresh_token: str) -> str:
    try:
        payload = jwt.decode(refresh_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid refresh token") from exc
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Invalid token type")
    user = db.query(User).filter(User.id == payload["sub"]).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    return create_access_token(
        user_id=user.id,
        role=user.role.value,
        secret_key=settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
        expire_minutes=settings.access_token_expire_minutes,
    )


def blacklist_token(token: str) -> None:
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError:
        return
    exp = payload.get("exp")
    if not exp:
        return
    ttl = max(int(exp - datetime.now(timezone.utc).timestamp()), 1)
    get_redis().setex(f"blacklist:{token}", ttl, "1")


def is_token_blacklisted(token: str) -> bool:
    return get_redis().exists(f"blacklist:{token}") == 1


def validate_token(authorization: str | None) -> tuple[uuid.UUID, UserRole]:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    if is_token_blacklisted(token):
        raise HTTPException(status_code=401, detail="Token revoked")
    try:
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise HTTPException(status_code=401, detail="Invalid token") from exc
    if payload.get("type") != "access":
        raise HTTPException(status_code=401, detail="Invalid token type")
    return uuid.UUID(payload["sub"]), UserRole(payload["role"])


def get_or_create_profile(db: Session, user: User) -> StudentProfile:
    profile = db.query(StudentProfile).filter(StudentProfile.user_id == user.id).first()
    if not profile:
        profile = StudentProfile(user_id=user.id)
        db.add(profile)
        db.commit()
        db.refresh(profile)
    return profile


def update_profile(db: Session, user: User, data: ProfileUpdate) -> StudentProfile:
    profile = get_or_create_profile(db, user)
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)
    db.commit()
    db.refresh(profile)
    return profile
