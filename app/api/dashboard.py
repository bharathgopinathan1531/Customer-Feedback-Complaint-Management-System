from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.complaint import Complaint, ComplaintPriority, ComplaintStatus
from app.models.feedback import Feedback
from app.models.user import User, UserRole
from app.services.sla import get_sla_status

dashboard_router = APIRouter(prefix="/dashboard", tags=["Dashboard"])
reports_router = APIRouter(prefix="/reports", tags=["Reports"])

management_roles = [UserRole.ADMIN, UserRole.MANAGER]


@dashboard_router.get("/summary")
def dashboard_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*management_roles)),
):
    total = db.query(func.count(Complaint.id)).scalar() or 0
    resolved = db.query(func.count(Complaint.id)).filter(
        Complaint.status.in_([ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED])
    ).scalar() or 0

    active = db.query(func.count(Complaint.id)).filter(
        Complaint.status.notin_([ComplaintStatus.RESOLVED, ComplaintStatus.CLOSED])
    ).scalar() or 0

    complaints = db.query(Complaint).all()
    overdue = sum(1 for complaint in complaints if get_sla_status(complaint)["is_overdue"])

    return {
        "total_complaints": total,
        "active_complaints": active,
        "resolved_or_closed_complaints": resolved,
        "overdue_complaints": overdue,
        "total_feedback": db.query(func.count(Feedback.id)).scalar() or 0,
    }


@dashboard_router.get("/complaints-by-status")
def complaints_by_status(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*management_roles)),
):
    rows = (
        db.query(Complaint.status, func.count(Complaint.id))
        .group_by(Complaint.status)
        .all()
    )
    counts = {status.value: int(count) for status, count in rows}

    return {
        "items": [
            {"status": item.value, "count": counts.get(item.value, 0)}
            for item in ComplaintStatus
        ]
    }


@dashboard_router.get("/complaints-by-priority")
def complaints_by_priority(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*management_roles)),
):
    rows = (
        db.query(Complaint.priority, func.count(Complaint.id))
        .group_by(Complaint.priority)
        .all()
    )
    counts = {priority.value: int(count) for priority, count in rows}

    return {
        "items": [
            {"priority": item.value, "count": counts.get(item.value, 0)}
            for item in ComplaintPriority
        ]
    }


@reports_router.get("/overview")
def reports_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*management_roles)),
):
    total_complaints = db.query(func.count(Complaint.id)).scalar() or 0
    total_feedback = db.query(func.count(Feedback.id)).scalar() or 0
    average_rating = db.query(func.avg(Feedback.rating)).scalar()

    return {
        "total_complaints": total_complaints,
        "total_feedback": total_feedback,
        "average_feedback_rating": (
            round(float(average_rating), 2)
            if average_rating is not None
            else None
        ),
    }
