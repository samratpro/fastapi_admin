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
from app.models.user import User
from app.models.role import Role
from app.models.public_role import PublicRole
from app.schemas.user import UserCreate, User as UserSchema, Token
from app.utils.email import EmailSender
import secrets
import re
from app.models.admin_access_role import AdminAccessRole


router = APIRouter()

@router.post("/register", response_model=UserSchema)
async def register(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
) -> Any:
    """
    Register new user with a public role.
    """
    # Validate email format
    email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    if not re.match(email_regex, user_in.email):
        raise HTTPException(
            status_code=400,
            detail="Invalid email format. Please provide a valid email address.",
        )

    # Validate password strength
    if len(user_in.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long."
        )
    if not re.search(r'[A-Z]', user_in.password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one uppercase letter."
        )
    if not re.search(r'[a-z]', user_in.password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one lowercase letter."
        )
    if not re.search(r'[0-9]', user_in.password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one number."
        )
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', user_in.password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)."
        )

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

    # Get public roles
    public_role = db.query(PublicRole).first()
    public_role_ids = public_role.role_ids if public_role else []

    # Determine the role for the user
    if user_in.role_id:
        if user_in.role_id not in public_role_ids:
            raise HTTPException(
                status_code=400,
                detail=f"Role with ID {user_in.role_id} is not available for public registration."
            )
        role = db.query(Role).filter(Role.id == user_in.role_id).first()
        if not role:
            raise HTTPException(
                status_code=400,
                detail=f"Role with ID {user_in.role_id} does not exist."
            )
    else:
        # Default to "user" role
        role = db.query(Role).filter(Role.name == "user").first()
        if not role:
            raise HTTPException(
                status_code=400,
                detail="Role 'user' does not exist. Please seed roles first."
            )
        if role.id not in public_role_ids:
            raise HTTPException(
                status_code=400,
                detail="Default 'user' role is not available for public registration."
            )

    # Generate a verification code
    verification_code = secrets.token_hex(6)

    # Create the user with the selected role
    user = User(
        email=user_in.email,
        username=user_in.username,
        hashed_password=get_password_hash(user_in.password),
        first_name=user_in.first_name,
        last_name=user_in.last_name,
        role_id=role.id,
        verification_token=verification_code
    )
    
    # Save the user to the database
    db.add(user)
    db.commit()
    db.refresh(user)

    # Send verification email
    await EmailSender.send_verification_email(user.email, verification_code)

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

@router.post("/verify/{code}")
async def verify_email(
    code: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Verify user email using a code.
    """
    user = db.query(User).filter(User.verification_token == code).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="Invalid verification code."
        )
    
    user.is_verified = True
    user.verification_token = None
    db.commit()
    
    return {"message": "Email verified successfully"}


@router.post("/forgot-password")
async def forgot_password(
    email: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Request a password reset. A reset code is sent to the user's email if they exist.
    """
    # Search for the user by email
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(
            status_code=404,
            detail="User with this email does not exist."
        )
    
    # Generate a reset code
    reset_code = secrets.token_hex(6)  # Generate a 6-character hexadecimal code
    user.verification_token = reset_code  # Reuse the verification_token field for reset code
    db.commit()

    # Send the reset code to the user's email
    await EmailSender.send_password_reset_email(user.email, reset_code)

    return {"message": "Password reset code sent to your email."}

@router.post("/verify-reset-code")
async def verify_reset_code(
    code: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Verify if the reset code is valid.
    """
    # Search for the user by reset code
    user = db.query(User).filter(User.verification_token == code).first()
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset code."
        )
    
    return {"message": "Reset code is valid."}


@router.post("/reset-password")
async def reset_password(
    code: str,
    new_password: str,
    db: Session = Depends(get_db)
) -> Any:
    """
    Reset the user's password using a valid reset code.
    """
    # Validate password strength
    if len(new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long."
        )
    if not re.search(r'[A-Z]', new_password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one uppercase letter."
        )
    if not re.search(r'[a-z]', new_password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one lowercase letter."
        )
    if not re.search(r'[0-9]', new_password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one number."
        )
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)."
        )

    # Search for the user by reset code
    user = db.query(User).filter(User.verification_token == code).first()
    if not user:
        raise HTTPException(
            status_code=400,
            detail="Invalid or expired reset code."
        )
    
    # Update the user's password
    user.hashed_password = get_password_hash(new_password)
    user.verification_token = None  # Clear the reset code
    db.commit()

    return {"message": "Password updated successfully."}

@router.get("/me", response_model=UserSchema)
async def read_users_me(
    current_user: User = Depends(get_current_active_user),
) -> Any:
    """
    Get current user.
    """
    return current_user


@router.put("/update-password")
async def update_password(
    current_password: str,
    new_password: str,
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)
) -> Any:
    """
    Update the password for an authenticated user.
    """
    # Verify the current password
    if not verify_password(current_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect."
        )

    # Validate the new password strength
    if len(new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters long."
        )
    if not re.search(r'[A-Z]', new_password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one uppercase letter."
        )
    if not re.search(r'[a-z]', new_password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one lowercase letter."
        )
    if not re.search(r'[0-9]', new_password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one number."
        )
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', new_password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one special character (!@#$%^&*(),.?\":{}|<>)."
        )

    # Check if the new password is the same as the old password
    if verify_password(new_password, current_user.hashed_password):
        raise HTTPException(
            status_code=400,
            detail="The new password cannot be the same as the current password."
        )

    # Update the user's password
    current_user.hashed_password = get_password_hash(new_password)
    db.commit()

    return {"message": "Password updated successfully."}


# admin panel login

@router.post("/admin-login", response_model=Token)
async def admin_login(
    db: Session = Depends(get_db),
    form_data: OAuth2PasswordRequestForm = Depends()
) -> Any:
    """
    OAuth2 compatible token login for admin access roles or admin users.
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

    # Check if user has admin access
    if user.role and user.role.name.lower() == "admin":
        # Admin role bypass
        pass
    else:
        # Check if user's role_id is in admin_access_roles
        admin_access_role = db.query(AdminAccessRole).first()
        admin_access_role_ids = admin_access_role.role_ids if admin_access_role else []
        if user.role_id not in admin_access_role_ids:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User does not have admin access privileges"
            )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.email}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}