import uuid
from datetime import datetime

from pydantic import BaseModel, Field

from campushire_common.enums import QueryStatus


class QueryCreate(BaseModel):
    subject: str
    body: str
    coordinator_id: uuid.UUID | None = None
    opportunity_id: uuid.UUID | None = None


class QueryReply(BaseModel):
    body: str


class QueryStatusUpdate(BaseModel):
    status: QueryStatus


class QueryMessageResponse(BaseModel):
    id: uuid.UUID
    sender_id: uuid.UUID
    body: str
    created_at: datetime

    model_config = {"from_attributes": True}


class QueryResponse(BaseModel):
    id: uuid.UUID
    student_id: uuid.UUID
    coordinator_id: uuid.UUID | None
    opportunity_id: uuid.UUID | None
    subject: str
    status: str
    created_at: datetime
    messages: list[QueryMessageResponse] = Field(default_factory=list)

    model_config = {"from_attributes": True}


class NotificationResponse(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    type: str
    title: str
    body: str
    read_at: datetime | None
    created_at: datetime

    model_config = {"from_attributes": True}
