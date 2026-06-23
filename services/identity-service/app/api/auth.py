from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models import User
from app.schemas import (
    LoginRequest,
    ProfileResponse,
    ProfileUpdate,
    RegisterRequest,
    UserResponse,
    ValidateTokenResponse,
)
from app.services.auth_service import (
    authenticate,
    blacklist_token,
    extract_access_token,
    issue_tokens,
    refresh_session,
    register_user,
    revoke_refresh_token,
    update_profile,
    validate_token,
)
from campushire_common.auth_deps import CurrentUser, get_current_user
from campushire_common.enums import UserRole

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def _set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    cookie_options = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "domain": settings.cookie_domain,
        "path": "/",
    }
    response.set_cookie(settings.access_token_cookie_name, access_token, **cookie_options)
    response.set_cookie(
        settings.refresh_token_cookie_name,
        refresh_token,
        max_age=settings.refresh_token_expire_days * 24 * 60 * 60,
        **cookie_options,
    )


def _clear_auth_cookies(response: Response) -> None:
    cookie_options = {
        "httponly": True,
        "secure": settings.cookie_secure,
        "samesite": settings.cookie_samesite,
        "domain": settings.cookie_domain,
        "path": "/",
    }
    response.delete_cookie(settings.access_token_cookie_name, **cookie_options)
    response.delete_cookie(settings.refresh_token_cookie_name, **cookie_options)


@router.post("/register", response_model=UserResponse, status_code=201)
def register(data: RegisterRequest, db: Session = Depends(get_db)):
    return register_user(db, data)


@router.post("/login", response_model=UserResponse)
def login(data: LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = authenticate(db, data.email, data.password)
    access, refresh = issue_tokens(db, user)
    _set_auth_cookies(response, access, refresh)
    return user


@router.post("/refresh", status_code=status.HTTP_204_NO_CONTENT)
def refresh(request: Request, response: Response, db: Session = Depends(get_db)):
    refresh_token = request.cookies.get(settings.refresh_token_cookie_name)
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Missing refresh token")
    access, refresh_token = refresh_session(db, refresh_token)
    _set_auth_cookies(response, access, refresh_token)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.post("/logout", status_code=204)
def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    authorization: str | None = Header(default=None),
):
    access_token = request.cookies.get(settings.access_token_cookie_name)
    refresh_token = request.cookies.get(settings.refresh_token_cookie_name)
    try:
        blacklist_token(extract_access_token(authorization, access_token))
    except HTTPException:
        pass
    revoke_refresh_token(db, refresh_token)
    _clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response


@router.get("/validate", response_model=ValidateTokenResponse)
def validate(request: Request, authorization: str | None = Header(default=None)):
    user_id, role = validate_token(
        authorization,
        request.cookies.get(settings.access_token_cookie_name),
    )
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
