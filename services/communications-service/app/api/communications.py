from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas import (
    NotificationResponse,
    QueryCreate,
    QueryReply,
    QueryResponse,
    QueryStatusUpdate,
)
from app.services.communications_service import (
    create_query,
    list_notifications,
    list_queries,
    mark_read,
    reply_query,
    update_query_status,
)
from campushire_common.auth_deps import CurrentUser, get_current_user
from campushire_common.enums import UserRole

router = APIRouter(tags=["communications"])


@router.post("/api/v1/queries", response_model=QueryResponse, status_code=201)
def post_query(
    data: QueryCreate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != UserRole.STUDENT:
        raise HTTPException(status_code=403, detail="Student only")
    return create_query(db, user.id, data)


@router.get("/api/v1/queries", response_model=list[QueryResponse])
def get_queries(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_queries(db, user.id, user.role)


@router.post("/api/v1/queries/{query_id}/reply", response_model=QueryResponse)
def post_reply(
    query_id: UUID,
    data: QueryReply,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return reply_query(db, query_id, user.id, user.role, data)


@router.patch("/api/v1/queries/{query_id}/status", response_model=QueryResponse)
def patch_query_status(
    query_id: UUID,
    data: QueryStatusUpdate,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if user.role != UserRole.COORDINATOR:
        raise HTTPException(status_code=403, detail="Coordinator only")
    return update_query_status(db, query_id, user.id, data)


@router.get("/api/v1/notifications", response_model=list[NotificationResponse])
def get_notifications(
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return list_notifications(db, user.id)


@router.post("/api/v1/notifications/{notification_id}/read", response_model=NotificationResponse)
def read_notification(
    notification_id: UUID,
    user: CurrentUser = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    return mark_read(db, notification_id, user.id)
