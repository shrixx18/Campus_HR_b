from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import StreamingResponse
from io import BytesIO
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    OpportunityCreate,
    OpportunityResponse,
    OpportunityUpdate,
    RegistrationCreate,
    RegistrationResponse,
)
from app.services.opportunity_service import (
    create_opportunity,
    generate_excel_export,
    get_opportunity,
    list_opportunities,
    register_student,
    update_opportunity,
    upload_file,
)
from campushire_common.auth_deps import CurrentUser, get_current_user
from campushire_common.enums import UserRole

router = APIRouter(prefix="/api/v1/opportunities", tags=["opportunities"])


@router.post("", response_model=OpportunityResponse, status_code=201)
def create_opp(
    data: OpportunityCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != UserRole.COORDINATOR:
        raise HTTPException(status_code=403, detail="Coordinator only")
    return create_opportunity(db, user.id, data)


@router.get("", response_model=list[OpportunityResponse])
def list_opps(db: Session = Depends(get_db)):
    return list_opportunities(db)


@router.get("/{opportunity_id}", response_model=OpportunityResponse)
def get_opp(opportunity_id: UUID, db: Session = Depends(get_db)):
    return get_opportunity(db, opportunity_id)


@router.patch("/{opportunity_id}", response_model=OpportunityResponse)
def patch_opp(
    opportunity_id: UUID,
    data: OpportunityUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != UserRole.COORDINATOR:
        raise HTTPException(status_code=403, detail="Coordinator only")
    return update_opportunity(db, opportunity_id, user.id, data)


@router.post("/{opportunity_id}/registrations", response_model=RegistrationResponse, status_code=201)
async def create_registration(
    opportunity_id: UUID,
    data: RegistrationCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Student only")
    return await register_student(db, opportunity_id, user.id, data)


@router.get("/{opportunity_id}/registrations", response_model=list[RegistrationResponse])
def list_registrations(
    opportunity_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    opp = get_opportunity(db, opportunity_id)
    if user.role == UserRole.COORDINATOR and opp.coordinator_id != user.id:
        raise HTTPException(status_code=403, detail="Not your opportunity")
    return opp.registrations


@router.get("/{opportunity_id}/export")
def export_registrations(
    opportunity_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    opp = get_opportunity(db, opportunity_id)
    if user.role != UserRole.COORDINATOR or opp.coordinator_id != user.id:
        raise HTTPException(status_code=403, detail="Coordinator only")
    content = generate_excel_export(db, opportunity_id)
    return StreamingResponse(
        BytesIO(content),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": f"attachment; filename=registrations_{opportunity_id}.xlsx"},
    )


@router.post("/files/upload")
async def upload_drive_file(
    file: UploadFile = File(...),
    user: CurrentUser = Depends(get_current_user),
):
    url = await upload_file(file, f"drives/{user.id}")
    return {"url": url}
