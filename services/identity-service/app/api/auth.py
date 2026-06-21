from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import (
    LoginRequest,
    ProfileResponse,
    ProfileUpdate,
    RefreshRequest,
    RegisterRequest,
    TokenResponse,
    UserResponse,
    ValidateTokenResponse,
)
from app.services.auth_service import (
    authenticate,
    blacklist_token,
    issue_tokens,
    refresh_access_token,
    register_user,
    update_profile,
    validate_token,
)
from campushire_common.auth_deps import CurrentUser, get_current_user
from campushire_common.enums import UserRole

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return register_user(db, data)


@router.post("/login", response_model=TokenResponse)
def login(data: LoginRequest, db: Session = Depends(get_db)):
    user = authenticate(db, data.email, data.password)
    access, refresh = issue_tokens(db, user)
    return TokenResponse(access_token=access, refresh_token=refresh)


@router.post("/refresh", response_model=TokenResponse)
def refresh(data: RefreshRequest, db: Session = Depends(get_db)):
    access = refresh_access_token(db, data.refresh_token)
    return TokenResponse(access_token=access, refresh_token=data.refresh_token)


@router.post("/logout", status_code=204)
def logout(authorization: str | None = Header(default=None)):
    if authorization and authorization.startswith("Bearer "):
        blacklist_token(authorization.removeprefix("Bearer ").strip())


@router.get("/validate", response_model=ValidateTokenResponse)
def validate(authorization: str | None = Header(default=None)):
    from fastapi.responses import JSONResponse

    user_id, role = validate_token(authorization)
    body = ValidateTokenResponse(user_id=user_id, role=role)
    return JSONResponse(
        content=body.model_dump(mode="json"),
        headers={"X-User-Id": str(user_id), "X-User-Role": role.value},
    )


@router.get("/me", response_model=UserResponse)
def me(user: CurrentUser = Depends(get_current_user), db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.id == user.id).first()
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user


@router.get("/profile/{user_id}", response_model=ProfileResponse)
def get_profile(user_id: UUID, db: Session = Depends(get_db)):
    from app.services.auth_service import get_or_create_profile

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    profile = get_or_create_profile(db, user)
    return profile


@router.put("/profile", response_model=ProfileResponse)
def put_profile(
    data: ProfileUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Only students have profiles")
    db_user = db.query(User).filter(User.id == user.id).first()
    return update_profile(db, db_user, data)
