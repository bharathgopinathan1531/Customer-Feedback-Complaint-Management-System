from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.audit_log import AuditLog
from app.models.user import UserRole
from app.schemas.audit_log import AuditLogListResponse

router = APIRouter(
    prefix="/audit-logs",
    tags=["Audit Logs"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


@router.get("", response_model=AuditLogListResponse)
def list_audit_logs(
    user_id: int | None = Query(default=None, gt=0),
    action: str | None = Query(default=None, min_length=1, max_length=100),
    resource_type: str | None = Query(default=None, min_length=1, max_length=100),
    resource_id: str | None = Query(default=None, min_length=1, max_length=100),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    if created_from and created_to and created_from > created_to:
        raise HTTPException(
            status_code=400,
            detail="created_from must be before or equal to created_to",
        )

    filters = []

    if user_id is not None:
        filters.append(AuditLog.user_id == user_id)
    if action:
        filters.append(AuditLog.action.ilike(f"%{action.strip()}%"))
    if resource_type:
        filters.append(
            AuditLog.resource_type.ilike(f"%{resource_type.strip()}%")
        )
    if resource_id:
        filters.append(AuditLog.resource_id == resource_id.strip())
    if created_from:
        filters.append(AuditLog.created_at >= created_from)
    if created_to:
        filters.append(AuditLog.created_at <= created_to)

    total = db.scalar(
        select(func.count(AuditLog.id)).where(*filters)
    ) or 0

    created_order = (
        AuditLog.created_at.asc()
        if sort_order == "asc"
        else AuditLog.created_at.desc()
    )

    statement = (
        select(AuditLog)
        .where(*filters)
        .order_by(created_order, AuditLog.id.desc())
        .offset(skip)
        .limit(limit)
    )

    items = list(db.scalars(statement).all())

    return {
        "items": items,
        "total": total,
        "skip": skip,
        "limit": limit,
    }
