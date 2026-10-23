from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.customer import Customer
from app.models.feedback import Feedback, FeedbackStatus
from app.models.user import User, UserRole
from app.schemas.feedback import (
    FeedbackCreate,
    FeedbackResponse,
    FeedbackUpdate,
    FeedbackStatusUpdate,
)

router = APIRouter(prefix="/feedback", tags=["Feedback"])


def get_customer_profile(db: Session, user: User) -> Customer:
    customer = db.query(Customer).filter(Customer.user_id == user.id).first()
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Customer profile not found. Create your profile first.",
        )
    return customer


@router.post(
    "",
    response_model=FeedbackResponse,
    status_code=status.HTTP_201_CREATED,
)
def submit_feedback(
    payload: FeedbackCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="Only customers can submit feedback")

    customer = get_customer_profile(db, current_user)

    feedback = Feedback(
        customer_id=customer.id,
        category=payload.category.strip(),
        rating=payload.rating,
        description=payload.description.strip(),
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("/me", response_model=list[FeedbackResponse])
def list_my_feedback(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="Only customers can access this endpoint")

    customer = get_customer_profile(db, current_user)

    return (
        db.query(Feedback)
        .filter(Feedback.customer_id == customer.id)
        .order_by(Feedback.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{feedback_id}", response_model=FeedbackResponse)
def get_feedback(
    feedback_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    feedback = db.get(Feedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback not found")

    if current_user.role == UserRole.CUSTOMER:
        customer = get_customer_profile(db, current_user)
        if feedback.customer_id != customer.id:
            raise HTTPException(status_code=403, detail="You cannot access another customer's feedback")
    elif current_user.role not in (UserRole.ADMIN, UserRole.MANAGER, UserRole.AGENT):
        raise HTTPException(status_code=403, detail="You do not have permission to access feedback")

    return feedback


@router.put("/{feedback_id}", response_model=FeedbackResponse)
def update_feedback(
    feedback_id: int,
    payload: FeedbackUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    if current_user.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=403, detail="Only customers can update feedback")

    customer = get_customer_profile(db, current_user)
    feedback = db.get(Feedback, feedback_id)

    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback not found")
    if feedback.customer_id != customer.id:
        raise HTTPException(status_code=403, detail="You cannot update another customer's feedback")
    if feedback.status != FeedbackStatus.SUBMITTED:
        raise HTTPException(status_code=409, detail="Only submitted feedback can be updated")

    updates = payload.model_dump(exclude_unset=True)
    for field, value in updates.items():
        if value is None:
            raise HTTPException(status_code=422, detail=f"{field} cannot be null")
        if isinstance(value, str):
            value = value.strip()
        setattr(feedback, field, value)

    db.commit()
    db.refresh(feedback)
    return feedback


@router.get("", response_model=list[FeedbackResponse])
def list_all_feedback(
    category: str | None = None,
    rating: int | None = Query(default=None, ge=1, le=5),
    feedback_status: FeedbackStatus | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.AGENT)
    ),
):
    query = db.query(Feedback)

    if category:
        query = query.filter(Feedback.category.ilike(f"%{category.strip()}%"))
    if rating is not None:
        query = query.filter(Feedback.rating == rating)
    if feedback_status is not None:
        query = query.filter(Feedback.status == feedback_status)

    return (
        query.order_by(Feedback.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.patch("/{feedback_id}/status", response_model=FeedbackResponse)
def update_feedback_status(
    feedback_id: int,
    payload: FeedbackStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN, UserRole.MANAGER, UserRole.AGENT)
    ),
):
    feedback = db.get(Feedback, feedback_id)
    if feedback is None:
        raise HTTPException(status_code=404, detail="Feedback not found")

    feedback.status = payload.status
    db.commit()
    db.refresh(feedback)
    return feedback
