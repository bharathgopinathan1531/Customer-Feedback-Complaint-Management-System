from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.api.deps import require_role
from app.db.session import get_db
from app.models.complaint import Complaint, ComplaintStatus
from app.models.user import User, UserRole
from app.schemas.auth import AccountStatusUpdate, UserResponse

router = APIRouter(
    prefix="/admin",
    tags=["Administration"],
    dependencies=[Depends(require_role(UserRole.ADMIN))],
)


@router.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    return list(
        db.scalars(select(User).order_by(User.id)).all()
    )


@router.patch("/users/{user_id}/status", response_model=UserResponse)
def update_user_status(
    user_id: int,
    data: AccountStatusUpdate,
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.is_active = data.is_active
    db.commit()
    db.refresh(user)
    return user


@router.get("/agents", response_model=list[UserResponse])
def list_agents(db: Session = Depends(get_db)):
    statement = (
        select(User)
        .where(User.role == UserRole.AGENT)
        .order_by(User.id)
    )
    return list(db.scalars(statement).all())


@router.get("/agents/workload")
def get_agent_workload(db: Session = Depends(get_db)):
    active_complaints = case(
        (
            Complaint.status.in_(
                [
                    ComplaintStatus.OPEN,
                    ComplaintStatus.IN_PROGRESS,
                ]
            ),
            1,
        ),
        else_=0,
    )

    statement = (
        select(
            User.id.label("agent_id"),
            User.full_name.label("agent_name"),
            User.email.label("email"),
            User.is_active.label("is_active"),
            func.count(Complaint.id).label("total_assigned"),
            func.coalesce(
                func.sum(active_complaints), 0
            ).label("active_complaints"),
        )
        .outerjoin(
            Complaint,
            Complaint.assigned_to_user_id == User.id,
        )
        .where(User.role == UserRole.AGENT)
        .group_by(
            User.id,
            User.full_name,
            User.email,
            User.is_active,
        )
        .order_by(User.id)
    )

    rows = db.execute(statement).mappings().all()
    return [dict(row) for row in rows]
