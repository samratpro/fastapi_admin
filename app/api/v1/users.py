from typing import List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from app.core.security import get_current_active_user, is_admin, get_password_hash
from app.db.base import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    User as UserSchema,
    UserWithPermissions
)
from app.utils.audit import log_activity

router = APIRouter()

@router.get("/", response_model=List[UserSchema])
async def list_users(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    skip: int = 0,
    limit: int = 100,
    role: Optional[str] = None,
    is_active: Optional[bool] = None,
    is_verified: Optional[bool] = None,
    search: Optional[str] = None
) -> Any:
    """
    Retrieve users with filtering options.
    """
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    query = db.query(User)

    if role:
        query = query.filter(User.role_obj.has(name=role))
    if is_active is not None:
        query = query.filter(User.is_active == is_active)
    if is_verified is not None:
        query = query.filter(User.is_verified == is_verified)
    if search:
        query = query.filter(
            (User.email.ilike(f"%{search}%")) |
            (User.username.ilike(f"%{search}%")) |
            (User.first_name.ilike(f"%{search}%")) |
            (User.last_name.ilike(f"%{search}%"))
        )

    return query.offset(skip).limit(limit).all()

@router.post("/", response_model=UserSchema)
async def create_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    current_user: User = Depends(get_current_active_user),
    request: Request
) -> Any:
    """
    Create a new user.
    """

    # Check if username or email already exists
    if db.query(User).filter(User.username == user_in.username).first():
        raise HTTPException(
            status_code=400,
            detail=f"Username '{user_in.username}' is already in use."
        )

    if db.query(User).filter(User.email == user_in.email).first():
        raise HTTPException(
            status_code=400,
            detail=f"Email '{user_in.email}' is already in use."
        )

    # If no conflict, proceed to create the new user
    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        role_id=user_in.role_id,
        is_active=True,
        is_verified=True  # Admin-created users are automatically verified
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    await log_activity(
        db=db,
        user=current_user,
        action="CREATE",
        resource_type="User",
        resource_id=user.id,
        changes=user_in.dict(exclude={"password"}),
        request=request
    )

    return user

@router.put("/{user_id}", response_model=UserSchema)
async def update_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    request: Request
) -> Any:
    """
    Update user.
    """
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    changes = {}
    for field, value in user_in.dict(exclude_unset=True).items():
        if field == "password" and value:
            changes[field] = "***"
            value = get_password_hash(value)
        elif value != getattr(user, field):
            changes[field] = value
        setattr(user, field, value)

    db.add(user)
    db.commit()
    db.refresh(user)

    if changes:
        await log_activity(
            db=db,
            user=current_user,
            action="UPDATE",
            resource_type="User",
            resource_id=user.id,
            changes=changes,
            request=request
        )

    return user

@router.delete("/{user_id}")
async def delete_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    request: Request
) -> Any:
    """
    Delete user.
    """
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    db.delete(user)
    db.commit()

    await log_activity(
        db=db,
        user=current_user,
        action="DELETE",
        resource_type="User",
        resource_id=user_id,
        request=request
    )

    return {"message": "User deleted successfully"}
