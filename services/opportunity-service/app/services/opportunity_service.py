from io import BytesIO
from pathlib import Path
from uuid import UUID

import httpx
from fastapi import HTTPException, UploadFile
from openpyxl import Workbook
from sqlalchemy.orm import Session

from app.config import settings
from app.models import EligibilityRule, FormField, Opportunity, Registration
from app.schemas import OpportunityCreate, OpportunityUpdate, RegistrationCreate
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
        if resp.status_code != 200:
            return {}
        return resp.json()


def check_eligibility(profile: dict, rules: list[EligibilityRule]) -> bool:
    for rule_obj in rules:
        rule = rule_obj.rule
        if "min_cgpa" in rule and profile.get("cgpa") is not None:
            if float(profile["cgpa"]) < float(rule["min_cgpa"]):
                return False
        if "allowed_branches" in rule and profile.get("branch"):
            if profile["branch"] not in rule["allowed_branches"]:
                return False
    return True


def create_opportunity(db: Session, coordinator_id: UUID, data: OpportunityCreate) -> Opportunity:
    opp = Opportunity(
        title=data.title,
        description=data.description,
        coordinator_id=coordinator_id,
        deadline=data.deadline,
        status="published",
    )
    db.add(opp)
    db.flush()
    for idx, field in enumerate(data.form_fields):
        db.add(
            FormField(
                opportunity_id=opp.id,
                field_type=field.field_type.value,
                label=field.label,
                required=field.required,
                options=field.options,
                maps_to_profile_field=field.maps_to_profile_field,
                sort_order=field.sort_order or idx,
            )
        )
    for rule in data.eligibility_rules:
        db.add(EligibilityRule(opportunity_id=opp.id, rule=rule))
    db.commit()
    db.refresh(opp)
    return opp


def list_opportunities(db: Session) -> list[Opportunity]:
    return db.query(Opportunity).order_by(Opportunity.created_at.desc()).all()


def get_opportunity(db: Session, opportunity_id: UUID) -> Opportunity:
    opp = db.query(Opportunity).filter(Opportunity.id == opportunity_id).first()
    if not opp:
        raise HTTPException(status_code=404, detail="Opportunity not found")
    return opp


def update_opportunity(db: Session, opportunity_id: UUID, coordinator_id: UUID, data: OpportunityUpdate) -> Opportunity:
    opp = get_opportunity(db, opportunity_id)
    if opp.coordinator_id != coordinator_id:
        raise HTTPException(status_code=403, detail="Not your opportunity")
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(opp, field, value)
    db.commit()
    db.refresh(opp)
    return opp


async def register_student(db: Session, opportunity_id: UUID, student_id: UUID, data: RegistrationCreate) -> Registration:
    opp = get_opportunity(db, opportunity_id)
    profile = await fetch_profile(student_id)
    if not check_eligibility(profile, opp.eligibility_rules):
        raise HTTPException(status_code=400, detail="Not eligible for this opportunity")
    existing = (
        db.query(Registration)
        .filter(Registration.opportunity_id == opportunity_id, Registration.student_id == student_id)
        .first()
    )
    if existing:
        raise HTTPException(status_code=400, detail="Already registered")
    reg = Registration(
        opportunity_id=opportunity_id,
        student_id=student_id,
        field_responses=data.field_responses,
        resume_url=data.resume_url,
    )
    db.add(reg)
    db.commit()
    db.refresh(reg)
    return reg


async def upload_file(file: UploadFile, folder: str) -> str:
    validate_upload(file)
    storage = get_storage()
    return await storage.save(file, folder)


def generate_excel_export(db: Session, opportunity_id: UUID) -> bytes:
    opp = get_opportunity(db, opportunity_id)
    regs = db.query(Registration).filter(Registration.opportunity_id == opportunity_id).all()
    wb = Workbook()
    ws = wb.active
    ws.title = "Registrations"
    headers = ["Student ID", "Responses", "Resume Link", "Submitted At"]
    ws.append(headers)
    for reg in regs:
        ws.append([
            str(reg.student_id),
            str(reg.field_responses),
            reg.resume_url or "",
            reg.submitted_at.isoformat() if reg.submitted_at else "",
        ])
    buffer = BytesIO()
    wb.save(buffer)
    return buffer.getvalue()


async def publish_event(publisher: EventPublisher, event_type: EventType, payload: dict, actor_id: UUID | None = None):
    await publisher.publish(DomainEvent(event_type=event_type, payload=payload, actor_id=actor_id))
