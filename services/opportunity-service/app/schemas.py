import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from campushire_common.enums import FormFieldType


class FormFieldCreate(BaseModel):
    field_type: FormFieldType
    label: str
    required: bool = False
    options: dict | None = None
    maps_to_profile_field: str | None = None
    sort_order: int = 0


class OpportunityCreate(BaseModel):
    title: str
    description: str | None = None
    deadline: datetime | None = None
    form_fields: list[FormFieldCreate] = Field(default_factory=list)
    eligibility_rules: list[dict] = Field(default_factory=list)


class OpportunityUpdate(BaseModel):
    title: str | None = None
    description: str | None = None
    deadline: datetime | None = None
    status: str | None = None


class FormFieldResponse(BaseModel):
    id: uuid.UUID
    field_type: FormFieldType
    label: str
    required: bool
    options: dict | None = None
    maps_to_profile_field: str | None = None
    sort_order: int

    model_config = {"from_attributes": True}


class OpportunityResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    coordinator_id: uuid.UUID
    deadline: datetime | None
    status: str
    form_fields: list[FormFieldResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class RegistrationCreate(BaseModel):
    field_responses: dict = Field(default_factory=dict)
    resume_url: str | None = None


class RegistrationResponse(BaseModel):
    id: uuid.UUID
    opportunity_id: uuid.UUID
    student_id: uuid.UUID
    field_responses: dict
    resume_url: str | None
    submitted_at: datetime

    model_config = {"from_attributes": True}
