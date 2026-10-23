from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, require_role
from app.db.session import get_db
from app.models.category import Category
from app.models.user import User, UserRole
from app.schemas.category import (
    CategoryCreate,
    CategoryResponse,
    CategoryStatusUpdate,
    CategoryUpdate,
)

router = APIRouter(prefix="/categories", tags=["Categories"])


@router.post(
    "",
    response_model=CategoryResponse,
    status_code=status.HTTP_201_CREATED,
)
def create_category(
    payload: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN, UserRole.MANAGER)
    ),
):
    existing = (
        db.query(Category)
        .filter(func.lower(Category.name) == payload.name.lower())
        .first()
    )
    if existing:
        raise HTTPException(status_code=409, detail="Category name already exists")

    category = Category(
        name=payload.name,
        description=payload.description,
    )
    db.add(category)
    try:
        db.commit()
        db.refresh(category)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Category name already exists")

    return category


@router.get("", response_model=list[CategoryResponse])
def list_categories(
    active_only: bool = True,
    search: str | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    query = db.query(Category)

    if active_only:
        query = query.filter(Category.is_active.is_(True))

    if search:
        query = query.filter(Category.name.ilike(f"%{search.strip()}%"))

    return (
        query.order_by(Category.name.asc())
        .offset(skip)
        .limit(limit)
        .all()
    )


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    if not category.is_active and current_user.role == UserRole.CUSTOMER:
        raise HTTPException(status_code=404, detail="Category not found")

    return category


@router.patch("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    payload: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN, UserRole.MANAGER)
    ),
):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    updates = payload.model_dump(exclude_unset=True)

    if "name" in updates:
        if updates["name"] is None:
            raise HTTPException(status_code=422, detail="Category name cannot be null")

        duplicate = (
            db.query(Category)
            .filter(
                func.lower(Category.name) == updates["name"].lower(),
                Category.id != category_id,
            )
            .first()
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="Category name already exists")

    for field, value in updates.items():
        setattr(category, field, value)

    try:
        db.commit()
        db.refresh(category)
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Category name already exists")

    return category


@router.patch("/{category_id}/status", response_model=CategoryResponse)
def update_category_status(
    category_id: int,
    payload: CategoryStatusUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(
        require_role(UserRole.ADMIN, UserRole.MANAGER)
    ),
):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    category.is_active = payload.is_active
    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
def deactivate_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_role(UserRole.ADMIN)),
):
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")

    category.is_active = False
    db.commit()
