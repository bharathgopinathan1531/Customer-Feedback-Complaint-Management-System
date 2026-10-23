from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from datetime import datetime

from sqlalchemy import or_
from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.category import Category
from app.models.complaint import Complaint, ComplaintPriority, ComplaintStatus
from app.models.customer import Customer
from app.models.notification import Notification
from app.models.complaint_status_history import ComplaintStatusHistory
from app.models.audit_log import AuditLog
from app.models.user import User, UserRole
from app.schemas.complaint import (
    ComplaintAssignment,
    ComplaintCreate,
    ComplaintResponse,
    ComplaintStatusUpdate,
    ComplaintUpdate,
)
router = APIRouter(prefix="/complaints", tags=["Complaints"])

staff_roles = [UserRole.ADMIN, UserRole.MANAGER, UserRole.AGENT]


@router.post("", response_model=ComplaintResponse, status_code=status.HTTP_201_CREATED)
def create_complaint(
    payload: ComplaintCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CUSTOMER)),
):
    customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
    if not customer:
        raise HTTPException(status_code=400, detail="Create your customer profile first")

    category = db.query(Category).filter(
        Category.id == payload.category_id,
        Category.is_active.is_(True),
    ).first()
    if not category:
        raise HTTPException(status_code=404, detail="Active category not found")

    complaint = Complaint(
        customer_id=customer.id,
        category_id=payload.category_id,
        subject=payload.subject,
        description=payload.description,
        priority=payload.priority,
        attachment_urls=payload.attachment_urls,
    )
    db.add(complaint)
    db.flush()
    complaint.reference_number = f"CMP-{complaint.id:06d}"
    db.add(
        AuditLog(
            user_id=current_user.id,
            action="COMPLAINT_CREATED",
            resource_type="complaint",
            resource_id=str(complaint.id),
            details={"reference_number": complaint.reference_number},
        )
    )
    db.commit()
    db.refresh(complaint)
    return complaint



@router.get("/me", response_model=list[ComplaintResponse])
def get_my_complaints(
    complaint_status: ComplaintStatus | None = Query(default=None, alias="status"),
    category_id: int | None = Query(default=None, gt=0),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CUSTOMER)),
):
    customer = (
        db.query(Customer)
        .filter(Customer.user_id == current_user.id)
        .first()
    )
    if customer is None:
        return []

    query = db.query(Complaint).filter(Complaint.customer_id == customer.id)

    if complaint_status is not None:
        query = query.filter(Complaint.status == complaint_status)

    if category_id is not None:
        query = query.filter(Complaint.category_id == category_id)

    return (
        query.order_by(Complaint.created_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("", response_model=list[ComplaintResponse])
def list_complaints(
    complaint_status: ComplaintStatus | None = Query(default=None, alias="status"),
    priority: ComplaintPriority | None = None,
    category_id: int | None = Query(default=None, gt=0),
    customer_id: int | None = Query(default=None, gt=0),
    search: str | None = Query(default=None, min_length=1, max_length=200),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    sort_by: str = Query(
        default="created_at",
        pattern="^(id|created_at|updated_at|priority|status)$",
    ),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*staff_roles)),
):
    query = db.query(Complaint)

    if complaint_status is not None:
        query = query.filter(Complaint.status == complaint_status)

    if priority is not None:
        query = query.filter(Complaint.priority == priority)

    if category_id is not None:
        query = query.filter(Complaint.category_id == category_id)

    if customer_id is not None:
        query = query.filter(Complaint.customer_id == customer_id)

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            or_(
                Complaint.reference_number.ilike(term),
                Complaint.subject.ilike(term),
                Complaint.description.ilike(term),
            )
        )

    if created_from is not None:
        query = query.filter(Complaint.created_at >= created_from)

    if created_to is not None:
        query = query.filter(Complaint.created_at <= created_to)

    if (
        created_from is not None
        and created_to is not None
        and created_from > created_to
    ):
        raise HTTPException(
            status_code=422,
            detail="created_from must be before or equal to created_to",
        )

    sort_columns = {
        "id": Complaint.id,
        "created_at": Complaint.created_at,
        "updated_at": Complaint.updated_at,
        "priority": Complaint.priority,
        "status": Complaint.status,
    }
    sort_column = sort_columns[sort_by]

    if sort_order == "asc":
        query = query.order_by(sort_column.asc(), Complaint.id.asc())
    else:
        query = query.order_by(sort_column.desc(), Complaint.id.desc())

    return query.offset(skip).limit(limit).all()

@router.get("/{complaint_id}", response_model=ComplaintResponse)
def get_complaint(
    complaint_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    if current_user.role == UserRole.CUSTOMER:
        customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
        if not customer or complaint.customer_id != customer.id:
            raise HTTPException(status_code=403, detail="Not allowed to view this complaint")
    elif current_user.role not in staff_roles:
        raise HTTPException(status_code=403, detail="Not allowed to view this complaint")

    return complaint


@router.put("/{complaint_id}", response_model=ComplaintResponse)
def update_complaint(
    complaint_id: int,
    payload: ComplaintUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.CUSTOMER)),
):
    customer = db.query(Customer).filter(Customer.user_id == current_user.id).first()
    complaint = db.query(Complaint).filter(Complaint.id == complaint_id).first()

    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")
    if not customer or complaint.customer_id != customer.id:
        raise HTTPException(status_code=403, detail="Cannot update another customer's complaint")
    if complaint.status != ComplaintStatus.OPEN:
        raise HTTPException(status_code=400, detail="Only open complaints can be edited")

    changed_fields = payload.model_dump(exclude_unset=True)
    for field, value in changed_fields.items():
        setattr(complaint, field, value)

    db.add(
        AuditLog(
            user_id=current_user.id,
            action="COMPLAINT_UPDATED",
            resource_type="complaint",
            resource_id=str(complaint.id),
            details={"updated_fields": list(changed_fields.keys())},
        )
    )
    db.commit()
    db.refresh(complaint)
    return complaint
@router.patch("/{complaint_id}/status", response_model=ComplaintResponse)
def update_complaint_status(
    complaint_id: int,
    payload: ComplaintStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(*staff_roles)),
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .first()
    )

    if complaint is None:
        raise HTTPException(status_code=404, detail="Complaint not found")

    allowed_transitions = {
        ComplaintStatus.OPEN: {
            ComplaintStatus.ASSIGNED,
            ComplaintStatus.IN_PROGRESS,
        },
        ComplaintStatus.ASSIGNED: {
            ComplaintStatus.IN_PROGRESS,
            ComplaintStatus.OPEN,
        },
        ComplaintStatus.IN_PROGRESS: {
            ComplaintStatus.WAITING_FOR_CUSTOMER,
            ComplaintStatus.RESOLVED,
        },
        ComplaintStatus.WAITING_FOR_CUSTOMER: {
            ComplaintStatus.IN_PROGRESS,
            ComplaintStatus.REOPENED,
        },
        ComplaintStatus.RESOLVED: {
            ComplaintStatus.CLOSED,
            ComplaintStatus.REOPENED,
        },
        ComplaintStatus.CLOSED: {ComplaintStatus.REOPENED},
        ComplaintStatus.REOPENED: {
            ComplaintStatus.ASSIGNED,
            ComplaintStatus.IN_PROGRESS,
        },
    }

    if payload.status == complaint.status:
        raise HTTPException(
            status_code=400,
            detail="Complaint already has this status",
        )

    if payload.status not in allowed_transitions.get(complaint.status, set()):
        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid status transition from "
                f"'{complaint.status.value}' to '{payload.status.value}'"
            ),
        )

    if (
        payload.status == ComplaintStatus.RESOLVED
        and not payload.resolution_notes
    ):
        raise HTTPException(
            status_code=400,
            detail="Resolution notes are required to resolve a complaint",
        )

    from datetime import datetime, timezone

    old_status = complaint.status
    now = datetime.now(timezone.utc)
    complaint.status = payload.status

    if payload.status == ComplaintStatus.RESOLVED:
        complaint.resolution_notes = payload.resolution_notes
        complaint.resolved_at = now
        complaint.closed_at = None
    elif payload.status == ComplaintStatus.CLOSED:
        complaint.closed_at = now
    elif payload.status == ComplaintStatus.OPEN:
        complaint.resolution_notes = None
        complaint.resolved_at = None
        complaint.closed_at = None

    history = ComplaintStatusHistory(
        complaint_id=complaint.id,
        old_status=old_status.value,
        new_status=payload.status.value,
        changed_by_user_id=current_user.id,
        note=payload.resolution_notes,
    )
    db.add(history)
    db.add(
        AuditLog(
            user_id=current_user.id,
            action="COMPLAINT_STATUS_CHANGED",
            resource_type="complaint",
            resource_id=str(complaint.id),
            details={
                "old_status": old_status.value,
                "new_status": payload.status.value,
            },
        )
    )

    # Notify the customer in the same transaction as the status change.
    customer = (
        db.query(Customer)
        .filter(Customer.id == complaint.customer_id)
        .first()
    )
    if customer is not None:
        reference = complaint.reference_number or f"#{complaint.id}"
        db.add(
            Notification(
                user_id=customer.user_id,
                title=f"Complaint {reference} status updated",
                message=(
                    f"Your complaint status changed to "
                    f"{payload.status.value.replace('_', ' ')}."
                ),
                notification_type="complaint_status",
            )
        )

    try:
        db.commit()
        db.refresh(complaint)
    except Exception:
        db.rollback()
        raise

    return complaint


@router.patch("/{complaint_id}/assign", response_model=ComplaintResponse)
def assign_complaint(
    complaint_id: int,
    payload: ComplaintAssignment,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN, UserRole.MANAGER)),
):
    complaint = (
        db.query(Complaint)
        .filter(Complaint.id == complaint_id)
        .first()
    )
    if not complaint:
        raise HTTPException(status_code=404, detail="Complaint not found")

    staff_member = (
        db.query(User)
        .filter(User.id == payload.assigned_to_user_id)
        .first()
    )
    if not staff_member:
        raise HTTPException(status_code=404, detail="Staff member not found")

    if not staff_member.is_active:
        raise HTTPException(status_code=400, detail="Staff member is inactive")

    if staff_member.role not in (UserRole.AGENT, UserRole.MANAGER):
        raise HTTPException(
            status_code=400,
            detail="Complaints can only be assigned to agents or managers",
        )

    previous_assignee_id = complaint.assigned_to_user_id
    complaint.assigned_to_user_id = staff_member.id

    db.add(
        AuditLog(
            user_id=current_user.id,
            action="COMPLAINT_ASSIGNED",
            resource_type="complaint",
            resource_id=str(complaint.id),
            details={
                "previous_assignee_id": previous_assignee_id,
                "assigned_to_user_id": staff_member.id,
            },
        )
    )

    # Notify the newly assigned agent or manager.
    if previous_assignee_id != staff_member.id:
        reference = complaint.reference_number or f"#{complaint.id}"
        db.add(
            Notification(
                user_id=staff_member.id,
                title=f"Complaint {reference} assigned to you",
                message=f"You have been assigned complaint: {complaint.subject}",
                notification_type="complaint_assigned",
            )
        )

    try:
        db.commit()
        db.refresh(complaint)
    except Exception:
        db.rollback()
        raise

    return complaint




@router.get("/{complaint_id}/history")
def get_complaint_status_history(
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
            raise HTTPException(
                status_code=403,
                detail="You can only view history for your own complaints",
            )
    elif current_user.role not in staff_roles:
        raise HTTPException(status_code=403, detail="Access denied")

    history = (
        db.query(ComplaintStatusHistory)
        .filter(ComplaintStatusHistory.complaint_id == complaint_id)
        .order_by(
            ComplaintStatusHistory.changed_at.asc(),
            ComplaintStatusHistory.id.asc(),
        )
        .all()
    )

    return [
        {
            "id": item.id,
            "complaint_id": item.complaint_id,
            "old_status": item.old_status,
            "new_status": item.new_status,
            "changed_by_user_id": item.changed_by_user_id,
            "note": item.note,
            "changed_at": item.changed_at,
        }
        for item in history
    ]
