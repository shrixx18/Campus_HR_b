import asyncio
from datetime import datetime, timezone
from email.message import EmailMessage
from uuid import UUID

import aiosmtplib
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.config import settings
from app.models import Notification, NotificationDeliveryLog, Query, QueryMessage
from app.schemas import QueryCreate, QueryReply, QueryStatusUpdate
from campushire_common.enums import QueryStatus, UserRole
from campushire_events import DomainEvent, EventPublisher, EventType


async def send_email(to: str, subject: str, body: str) -> bool:
    if not settings.smtp_user:
        return False
    message = EmailMessage()
    message["From"] = settings.smtp_from
    message["To"] = to
    message["Subject"] = subject
    message.set_content(body)
    try:
        await aiosmtplib.send(
            message,
            hostname=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_user,
            password=settings.smtp_password,
            start_tls=True,
        )
        return True
    except Exception:
        return False


def create_notification(db: Session, user_id: UUID, ntype: str, title: str, body: str) -> Notification:
    note = Notification(user_id=user_id, type=ntype, title=title, body=body)
    db.add(note)
    db.commit()
    db.refresh(note)
    return note


def create_query(db: Session, student_id: UUID, data: QueryCreate, publisher: EventPublisher | None = None) -> Query:
    q = Query(
        student_id=student_id,
        coordinator_id=data.coordinator_id,
        opportunity_id=data.opportunity_id,
        subject=data.subject,
    )
    db.add(q)
    db.flush()
    db.add(QueryMessage(query_id=q.id, sender_id=student_id, body=data.body))
    db.commit()
    db.refresh(q)
    return q


def reply_query(db: Session, query_id: UUID, sender_id: UUID, role: UserRole, data: QueryReply) -> Query:
    q = db.query(Query).filter(Query.id == query_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    if role == UserRole.STUDENT and q.student_id != sender_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    if role == UserRole.COORDINATOR:
        q.coordinator_id = sender_id
        if q.status == QueryStatus.OPEN.value:
            q.status = QueryStatus.IN_PROGRESS.value
    db.add(QueryMessage(query_id=q.id, sender_id=sender_id, body=data.body))
    db.commit()
    db.refresh(q)
    return q


def update_query_status(db: Session, query_id: UUID, coordinator_id: UUID, data: QueryStatusUpdate) -> Query:
    q = db.query(Query).filter(Query.id == query_id).first()
    if not q:
        raise HTTPException(status_code=404, detail="Query not found")
    if q.coordinator_id and q.coordinator_id != coordinator_id:
        raise HTTPException(status_code=403, detail="Forbidden")
    q.status = data.status.value
    db.commit()
    db.refresh(q)
    return q


def list_queries(db: Session, user_id: UUID, role: UserRole) -> list[Query]:
    q = db.query(Query)
    if role == UserRole.STUDENT:
        q = q.filter(Query.student_id == user_id)
    elif role == UserRole.COORDINATOR:
        q = q.filter((Query.coordinator_id == user_id) | (Query.coordinator_id.is_(None)))
    return q.order_by(Query.created_at.desc()).all()


def list_notifications(db: Session, user_id: UUID) -> list[Notification]:
    return db.query(Notification).filter(Notification.user_id == user_id).order_by(Notification.created_at.desc()).all()


def mark_read(db: Session, notification_id: UUID, user_id: UUID) -> Notification:
    note = db.query(Notification).filter(Notification.id == notification_id, Notification.user_id == user_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Not found")
    note.read_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(note)
    return note


async def handle_domain_event(event: DomainEvent):
    from app.database import SessionLocal

    db = SessionLocal()
    try:
        payload = event.payload
        user_id = payload.get("student_id")
        if not user_id:
            return
        titles = {
            EventType.APPLICATION_SUBMITTED: ("Application Submitted", "Your application was submitted successfully."),
            EventType.APPLICATION_SHORTLISTED: ("Shortlisted", "You have been shortlisted."),
            EventType.APPLICATION_REJECTED: ("Application Update", "Your application status was updated to rejected."),
            EventType.QUERY_RESPONDED: ("Query Response", payload.get("body", "You received a reply.")),
        }
        if event.event_type not in titles:
            return
        title, body = titles[event.event_type]
        note = create_notification(db, UUID(user_id), event.event_type.value, title, body)
        db.add(NotificationDeliveryLog(notification_id=note.id, channel="email", status="pending"))
        db.commit()
    finally:
        db.close()
