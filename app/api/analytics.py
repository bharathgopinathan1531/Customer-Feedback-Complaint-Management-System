from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.feedback import Feedback, FeedbackStatus
from app.models.user import User, UserRole

router = APIRouter(prefix="/analytics", tags=["Satisfaction Analytics"])

analytics_roles = [UserRole.ADMIN, UserRole.MANAGER]


@router.get("/satisfaction")
def satisfaction_summary(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*analytics_roles)),
):
    total = db.query(func.count(Feedback.id)).scalar() or 0
    average = db.query(func.avg(Feedback.rating)).scalar()

    satisfied = db.query(func.count(Feedback.id)).filter(
        Feedback.rating >= 4
    ).scalar() or 0

    return {
        "total_feedback": total,
        "average_rating": round(float(average), 2) if average is not None else None,
        "satisfied_feedback_count": satisfied,
        "satisfaction_percentage": round(satisfied * 100 / total, 2) if total else 0.0,
        "satisfaction_definition": "Percentage of feedback ratings that are 4 or 5",
    }


@router.get("/ratings")
def rating_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*analytics_roles)),
):
    rows = (
        db.query(Feedback.rating, func.count(Feedback.id))
        .group_by(Feedback.rating)
        .order_by(Feedback.rating)
        .all()
    )
    counts = {int(rating): int(count) for rating, count in rows}

    return {
        "ratings": [
            {"rating": rating, "count": counts.get(rating, 0)}
            for rating in range(1, 6)
        ]
    }


@router.get("/categories")
def category_satisfaction(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*analytics_roles)),
):
    rows = (
        db.query(
            Feedback.category,
            func.count(Feedback.id).label("feedback_count"),
            func.avg(Feedback.rating).label("average_rating"),
        )
        .group_by(Feedback.category)
        .order_by(Feedback.category)
        .all()
    )

    return {
        "categories": [
            {
                "category": category,
                "feedback_count": int(count),
                "average_rating": round(float(avg), 2) if avg is not None else None,
            }
            for category, count, avg in rows
        ]
    }


@router.get("/feedback-statuses")
def feedback_status_distribution(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*analytics_roles)),
):
    rows = (
        db.query(Feedback.status, func.count(Feedback.id))
        .group_by(Feedback.status)
        .all()
    )
    counts = {status.value: int(count) for status, count in rows}

    return {
        "statuses": [
            {"status": item.value, "count": counts.get(item.value, 0)}
            for item in FeedbackStatus
        ]
    }
