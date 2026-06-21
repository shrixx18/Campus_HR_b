import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from campushire_common.enums import ApplicationStatus


class ApplicationCreate(BaseModel):
    opportunity_id: uuid.UUID
    overrides: dict = Field(default_factory=dict)
    resume_url: str | None = None


class ApplicationResponse(BaseModel):
    id: uuid.UUID
    opportunity_id: uuid.UUID
    student_id: uuid.UUID
    status: str
    resume_url: str | None
    profile_snapshot: dict | None
    overrides: dict | None
    created_at: datetime

    model_config = {"from_attributes": True}


class StatusUpdate(BaseModel):
    status: ApplicationStatus


class StageResponse(BaseModel):
    id: uuid.UUID
    stage_name: str
    entered_at: datetime
    exited_at: datetime | None
    actor_id: uuid.UUID | None

    model_config = {"from_attributes": True}


class TimelineResponse(BaseModel):
    application: ApplicationResponse
    stages: list[StageResponse]
