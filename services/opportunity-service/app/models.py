import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from campushire_common.enums import FormFieldType


class Base(DeclarativeBase):
    pass


class Opportunity(Base):
    __tablename__ = "opportunities"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    coordinator_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    deadline: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(String(50), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    form_fields: Mapped[list["FormField"]] = relationship(back_populates="opportunity", cascade="all, delete-orphan")
    registrations: Mapped[list["Registration"]] = relationship(back_populates="opportunity", cascade="all, delete-orphan")
    eligibility_rules: Mapped[list["EligibilityRule"]] = relationship(back_populates="opportunity", cascade="all, delete-orphan")


class FormField(Base):
    __tablename__ = "form_fields"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("opportunities.id"))
    field_type: Mapped[FormFieldType] = mapped_column(String(50), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    required: Mapped[bool] = mapped_column(default=False)
    options: Mapped[dict | None] = mapped_column(JSONB)
    maps_to_profile_field: Mapped[str | None] = mapped_column(String(100))
    sort_order: Mapped[int] = mapped_column(default=0)
    opportunity: Mapped[Opportunity] = relationship(back_populates="form_fields")


class Registration(Base):
    __tablename__ = "registrations"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("opportunities.id"), index=True)
    student_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), index=True)
    field_responses: Mapped[dict] = mapped_column(JSONB, default=dict)
    resume_url: Mapped[str | None] = mapped_column(String(500))
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    opportunity: Mapped[Opportunity] = relationship(back_populates="registrations")


class EligibilityRule(Base):
    __tablename__ = "eligibility_rules"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    opportunity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("opportunities.id"))
    rule: Mapped[dict] = mapped_column(JSONB, nullable=False)
    opportunity: Mapped[Opportunity] = relationship(back_populates="eligibility_rules")
