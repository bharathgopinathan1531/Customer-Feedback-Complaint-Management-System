from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.complaint import Complaint
from app.models.customer import Customer
from app.models.user import User, UserRole
from app.services.sla import get_sla_status

router = APIRouter(tags=["SLA"])

STAFF_ROLES = {UserRole.ADMIN, UserRole.MANAGER, UserRole.AGENT}


@router.get("/complaints/{complaint_id}/sla")
def get_complaint_sla(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
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
            raise HTTPException(status_code=403, detail="Access denied")
    elif current_user.role not in STAFF_ROLES:
        raise HTTPException(status_code=403, detail="Access denied")

    return get_sla_status(complaint)


@router.get("/sla/overdue")
def list_overdue_complaints(
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*STAFF_ROLES)),
):
    complaints = (
        db.query(Complaint)
        .order_by(Complaint.created_at.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    results = [get_sla_status(item) for item in complaints]
    return [item for item in results if item["is_overdue"]]
