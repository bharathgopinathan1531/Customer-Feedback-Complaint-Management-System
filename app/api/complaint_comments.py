from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user
from app.db.session import get_db
from app.models.complaint import Complaint
from app.models.complaint_comment import ComplaintComment
from app.models.customer import Customer
from app.models.user import User, UserRole
from app.schemas.complaint_comment import (
    ComplaintCommentCreate,
    ComplaintCommentResponse,
)

router = APIRouter(prefix="/complaints", tags=["Complaint Comments"])

STAFF_ROLES = {UserRole.ADMIN, UserRole.MANAGER, UserRole.AGENT}


def get_accessible_complaint(
    complaint_id: int,
    db: Session,
    current_user: User,
) -> Complaint:
    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .first()
    )

    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if current_user.role == UserRole.CUSTOMER:
        customer = (
            db.query(Customer)
            .filter(Customer.user_id == current_user.id)
            .first()
        )
        if customer is None or customer.id != complaint.customer_id:
            raise HTTPException(
                status_code=403,
                detail="You can only access comments on your own complaints",
            )
    elif current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Access denied")

    return complaint


@router.post(
    "/{complaint_id}/comments",
    response_model=ComplaintCommentResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_complaint_comment(
    complaint_id: int,
    payload: ComplaintCommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_accessible_complaint(complaint_id, db, current_user)

    comment = ComplaintComment(
        complaint_id=complaint_id,
        user_id=current_user.id,
        comment=payload.comment,
    )
    db.add(comment)
    db.commit()
    db.refresh(comment)
    return comment


@router.get(
    "/{complaint_id}/comments",
    response_model=list[ComplaintCommentResponse],
)
def list_complaint_comments(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    get_accessible_complaint(complaint_id, db, current_user)

    return (
        db.query(ComplaintComment)
        .filter(ComplaintComment.complaint_id == complaint_id)
        .order_by(
            ComplaintComment.created_at.asc(),
            ComplaintComment.id.asc(),
        )
        .all()
    )
