from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class EventType(str, Enum):
    APPLICATION_SUBMITTED = "APPLICATION_SUBMITTED"
    APPLICATION_WITHDRAWN = "APPLICATION_WITHDRAWN"
    APPLICATION_SHORTLISTED = "APPLICATION_SHORTLISTED"
    APPLICATION_REJECTED = "APPLICATION_REJECTED"
    DRIVE_CREATED = "DRIVE_CREATED"
    DRIVE_UPDATED = "DRIVE_UPDATED"
    QUERY_CREATED = "QUERY_CREATED"
    QUERY_RESPONDED = "QUERY_RESPONDED"
    REGISTRATION_DEADLINE_REACHED = "REGISTRATION_DEADLINE_REACHED"


class DomainEvent(BaseModel):
    event_type: EventType
    payload: dict[str, Any] = Field(default_factory=dict)
    actor_id: UUID | None = None
    correlation_id: str | None = None
