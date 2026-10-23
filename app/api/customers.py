from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import asc, desc, func, or_, select
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models import Customer, User, UserRole
from app.schemas.customer import (
    CustomerListItem,
    CustomerProfileCreate,
    CustomerProfileResponse,
    CustomerProfileUpdate,
    CustomerStatusUpdate,
)

router = APIRouter(prefix="/customers", tags=["Customers"])


def require_customer(user: User):
    if user.role != UserRole.CUSTOMER:
        raise HTTPException(
            status_code=403,
            detail="This endpoint is for customer accounts only",
        )


@router.post(
    "/me",
    response_model=CustomerProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_my_profile(
    data: CustomerProfileCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_customer(current_user)

    existing = db.scalar(
        select(Customer).where(Customer.user_id == current_user.id)
    )
    if existing:
        raise HTTPException(
            status_code=409,
            detail="Customer profile already exists; use PUT /customers/me",
        )

    profile = Customer(user_id=current_user.id, **data.model_dump())
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile


@router.get("/me", response_model=CustomerProfileResponse)
def get_my_profile(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_customer(current_user)
    profile = db.scalar(
        select(Customer).where(Customer.user_id == current_user.id)
    )
    if profile is None:
        raise HTTPException(status_code=404, detail="Customer profile not found")
    return profile


@router.put("/me", response_model=CustomerProfileResponse)
def update_my_profile(
    data: CustomerProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    require_customer(current_user)
    profile = db.scalar(
        select(Customer).where(Customer.user_id == current_user.id)
    )
    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Create your profile first using POST /customers/me",
        )

    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(profile, field, value)

    db.commit()
    db.refresh(profile)
    return profile


@router.get("", response_model=list[CustomerListItem])
def list_customers(
    search: str | None = Query(default=None, max_length=120),
    active: bool | None = None,
    city: str | None = Query(default=None, max_length=100),
    sort_by: str = Query(default="id", pattern="^(id|full_name|email|city)$"),
    sort_order: str = Query(default="asc", pattern="^(asc|desc)$"),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    current_user: User = Depends(
        require_role(UserRole.ADMIN, UserRole.MANAGER)
    ),
    db: Session = Depends(get_db),
):
    query = (
        select(Customer, User)
        .join(User, Customer.user_id == User.id)
        .where(User.role == UserRole.CUSTOMER)
    )

    if search:
        term = f"%{search.strip()}%"
        query = query.where(
            or_(User.full_name.ilike(term), User.email.ilike(term))
        )

    if active is not None:
        query = query.where(User.is_active == active)

    if city:
        query = query.where(Customer.city.ilike(f"%{city.strip()}%"))

    sort_columns = {
        "id": Customer.id,
        "full_name": User.full_name,
        "email": User.email,
        "city": Customer.city,
    }
    sort_column = sort_columns[sort_by]
    query = query.order_by(
        (desc(sort_column) if sort_order == "desc" else asc(sort_column)),
        asc(User.id),
    ).offset(skip).limit(limit)

    rows = db.execute(query).all()
    return [
        CustomerListItem(
            id=customer.id,
            user_id=user.id,
            full_name=user.full_name,
            email=user.email,
            is_active=user.is_active,
            phone=customer.phone,
            address=customer.address,
            city=customer.city,
        )
        for customer, user in rows
    ]


@router.get("/{user_id}", response_model=CustomerListItem)
def get_customer(
    user_id: int,
    current_user: User = Depends(
        require_role(UserRole.ADMIN, UserRole.MANAGER)
    ),
    db: Session = Depends(get_db),
):
    row = db.execute(
        select(Customer, User)
        .join(User, Customer.user_id == User.id)
        .where(User.id == user_id, User.role == UserRole.CUSTOMER)
    ).first()

    if row is None:
        raise HTTPException(status_code=404, detail="Customer profile not found")

    customer, user = row
    return CustomerListItem(
        id=customer.id,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        is_active=user.is_active,
        phone=customer.phone,
        address=customer.address,
        city=customer.city,
    )


@router.patch("/{user_id}/status", response_model=CustomerListItem)
def update_customer_status(
    user_id: int,
    data: CustomerStatusUpdate,
    current_user: User = Depends(require_role(UserRole.ADMIN)),
    db: Session = Depends(get_db),
):
    user = db.get(User, user_id)
    if user is None or user.role != UserRole.CUSTOMER:
        raise HTTPException(status_code=404, detail="Customer not found")

    user.is_active = data.is_active
    profile = db.scalar(
        select(Customer).where(Customer.user_id == user_id)
    )
    db.commit()

    if profile is None:
        raise HTTPException(
            status_code=404,
            detail="Customer account updated, but profile has not been created",
        )

    db.refresh(profile)
    db.refresh(user)
    return CustomerListItem(
        id=profile.id,
        user_id=user.id,
        full_name=user.full_name,
        email=user.email,
        is_active=user.is_active,
        phone=profile.phone,
        address=profile.address,
        city=profile.city,
    )
