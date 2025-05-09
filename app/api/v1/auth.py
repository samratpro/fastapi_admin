from datetime import timedelta
from typing import Any
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.security import (
    get_password_hash,
    verify_password,
    create_access_token,
    get_current_active_user
)
from app.db.base import get_db
from app.models.user import User, Role
from app.schemas.user import UserCreate, User as UserSchema, Token, RoleCreate, Role as RoleSchema
from app.utils.email import EmailSender
import secrets
from app.core.security import is_admin

router = APIRouter()


@router.post("/roles", response_model=RoleSchema)
def create_role(
    *,
    db: Session = Depends(get_db),
    role_in: RoleCreate,
    current_user: User = Depends(get_current_active_user),  # Get the current authenticated user
):
    """
    Create a new role (admin only).
    """
    # Verify if the current user is an admin
    if not is_admin(current_user):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can create roles."
        )
    
    # Check if the role already exists
    existing_role = db.query(Role).filter(Role.name == role_in.name.lower()).first()
    if existing_role:
        raise HTTPException(
            status_code=400,
            detail=f"Role '{role_in.name.lower()}' already exists."
        )
    
    # Create the role if all checks pass
    new_role = Role(name=role_in.name.lower())
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role


@router.post("/register", response_model=UserSchema)
async def register(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    """
    Register new user.
    """
    # Check if the email is already registered
    user = db.query(User).filter(User.email == user_in.email).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="A user with this email already exists."
        )
    
    # Check if the username is already taken
    user = db.query(User).filter(User.username == user_in.username).first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="A user with this username already exists."
        )

    # Fetch the role for the user (e.g., role "user")
    role = db.query(Role).filter(Role.name == "user").first()
    if not role:
        raise HTTPException(
            status_code=400,
            detail="Role 'user' does not exist. Please seed roles first."
        )

    # Generate a verification token
    verification_token = secrets.token_urlsafe(32)

    # Create the user with the appropriate role_id
    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        role_id=role.id,  # Use role_id instead of role
        verification_token=verification_token
    )
    
    # Save the user to the database
    db.add(user)
    db.commit()
    db.refresh(user)

    # Send verification email
    await EmailSender.send_verification_email(user.email, verification_token)

    return user

@router.post("/login", response_model=Token)
async def login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login.
    """
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email not found"
        )
    if not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect password"
        )
    if not user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Please verify your email first"
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Account is inactive"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/verify/{token}")
async def verify_email(
    token: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Verify user email.
    """
    user = db.query(User).filter(User.verification_token == token).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Invalid verification token"
        )
    
    user.is_verified = True
    user.verification_token = None
    db.commit()
    
    return {"message": "Email verified successfully"}

@router.get("/me", response_model=UserSchema)
async def read_users_me(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user