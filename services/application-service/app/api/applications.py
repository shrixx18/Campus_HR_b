from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Application
from app.schemas import ApplicationCreate, ApplicationResponse, StatusUpdate, TimelineResponse, StageResponse
from app.services.application_service import apply, update_status, upload_resume, withdraw
from campushire_common.auth_deps import CurrentUser, get_current_user
from campushire_common.enums import UserRole
from campushire_events import EventPublisher

router = APIRouter(prefix="/api/v1/applications", tags=["applications"])


def get_publisher(request):
    return request.app.state.publisher


@router.post("", response_model=ApplicationResponse, status_code=201)
async def create_application(
    data: ApplicationCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from fastapi import Request
    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Student only")
    # publisher injected via app state in route - use workaround
    from app.main import publisher
    return await apply(db, user.id, data, publisher)


@router.get("", response_model=list[ApplicationResponse])
def list_applications(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(Application)
    if user.role == UserRole.STUDENT:
        q = q.filter(Application.student_id == user.id)
    return q.order_by(Application.created_at.desc()).all()


@router.get("/{application_id}", response_model=ApplicationResponse)
def get_application(
    application_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    if user.role == UserRole.STUDENT and app.student_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return app


@router.post("/{application_id}/withdraw", response_model=ApplicationResponse)
def withdraw_application(
    application_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Student only")
    return withdraw(db, application_id, user.id)


@router.patch("/{application_id}/status", response_model=ApplicationResponse)
async def patch_status(
    application_id: UUID,
    data: StatusUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != UserRole.COORDINATOR:
        raise HTTPException(status_code=403, detail="Coordinator only")
    from app.main import publisher
    return await update_status(db, application_id, user.id, data, publisher)


@router.get("/{application_id}/timeline", response_model=TimelineResponse)
def timeline(
    application_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Not found")
    if user.role == UserRole.STUDENT and app.student_id != user.id:
        raise HTTPException(status_code=403, detail="Forbidden")
    return TimelineResponse(application=app, stages=app.stages)


@router.post("/files/resume")
async def resume_upload(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Student only")
    url = await upload_resume(file, user.id)
    return {"url": url}
