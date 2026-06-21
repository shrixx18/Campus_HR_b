from datetime import datetime, timezone
from uuid import UUID

import httpx
from fastapi import HTTPException, UploadFile
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Application, AuditLog, WorkflowStage
from app.schemas import ApplicationCreate, StatusUpdate
from campushire_common.enums import ApplicationStatus
from campushire_events import DomainEvent, EventPublisher, EventType
from campushire_storage import create_storage_backend, validate_upload


def get_storage():
    if settings.storage_backend == "azure":
        return create_storage_backend(
            "azure",
            connection_string=settings.azure_storage_connection_string,
            container=settings.azure_storage_container,
        )
    return create_storage_backend("local", local_path=settings.local_storage_path, public_base_url="/api/v1/files")


async def fetch_profile(user_id: UUID) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.identity_service_url}/api/v1/auth/profile/{user_id}")
        return resp.json() if resp.status_code == 200 else {}


async def fetch_opportunity(opportunity_id: UUID) -> dict:
    async with httpx.AsyncClient() as client:
        resp = await client.get(f"{settings.opportunity_service_url}/api/v1/opportunities/{opportunity_id}")
        if resp.status_code != 200:
            raise HTTPException(status_code=404, detail="Opportunity not found")
        return resp.json()


def log_audit(db: Session, application_id: UUID, entity: str, action: str, payload: dict | None = None):
    db.add(AuditLog(application_id=application_id, entity=entity, action=action, payload=payload))


async def apply(db: Session, student_id: UUID, data: ApplicationCreate, publisher: EventPublisher) -> Application:
    await fetch_opportunity(data.opportunity_id)
    existing = (
        db.query(Application)
        .filter(Application.opportunity_id == data.opportunity_id, Application.student_id == student_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already applied")
    profile = await fetch_profile(student_id)
    app = Application(
        opportunity_id=data.opportunity_id,
        student_id=student_id,
        resume_url=data.resume_url,
        profile_snapshot=profile,
        overrides=data.overrides,
        status=ApplicationStatus.APPLIED.value,
    )
    db.add(app)
    db.flush()
    db.add(WorkflowStage(application_id=app.id, stage_name="Registration"))
    log_audit(db, app.id, "application", "created", {"status": app.status})
    db.commit()
    db.refresh(app)
    await publisher.publish(
        DomainEvent(
            event_type=EventType.APPLICATION_SUBMITTED,
            payload={"application_id": str(app.id), "student_id": str(student_id), "opportunity_id": str(data.opportunity_id)},
            actor_id=student_id,
        )
    )
    return app


def withdraw(db: Session, application_id: UUID, student_id: UUID, publisher: EventPublisher | None = None):
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    if app.student_id != student_id:
        raise HTTPException(status_code=403, detail="Not your application")
    app.status = "Withdrawn"
    log_audit(db, app.id, "application", "withdrawn")
    db.commit()
    return app


async def update_status(db: Session, application_id: UUID, actor_id: UUID, data: StatusUpdate, publisher: EventPublisher) -> Application:
    app = db.query(Application).filter(Application.id == application_id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    old_status = app.status
    app.status = data.status.value
    current_stage = (
        db.query(WorkflowStage)
        .filter(WorkflowStage.application_id == app.id, WorkflowStage.exited_at.is_(None))
        .first()
    )
    if current_stage:
        current_stage.exited_at = datetime.now(timezone.utc)
    db.add(WorkflowStage(application_id=app.id, stage_name=data.status.value, actor_id=actor_id))
    log_audit(db, app.id, "application", "status_changed", {"from": old_status, "to": app.status})
    db.commit()
    db.refresh(app)
    event_map = {
        ApplicationStatus.SHORTLISTED: EventType.APPLICATION_SHORTLISTED,
        ApplicationStatus.REJECTED: EventType.APPLICATION_REJECTED,
    }
    if data.status in event_map:
        await publisher.publish(
            DomainEvent(
                event_type=event_map[data.status],
                payload={"application_id": str(app.id), "student_id": str(app.student_id)},
                actor_id=actor_id,
            )
        )
    return app


async def upload_resume(file: UploadFile, student_id: UUID) -> str:
    validate_upload(file)
    storage = get_storage()
    return await storage.save(file, f"resumes/{student_id}")
