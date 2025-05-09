from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security import get_current_active_user, is_staff_or_admin
from app.db.base import get_db
from app.models.user import User
from app.models.student_profile import StudentProfile
from app.schemas.student_profile import (
    StudentProfileCreate,
    StudentProfileUpdate,
    StudentProfile as StudentProfileSchema
)

router = APIRouter()

@router.get("/", response_model=List[StudentProfileSchema])
def list_student_profiles(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Retrieve student profiles.
    """
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    profiles = db.query(StudentProfile).offset(skip).limit(limit).all()
    return profiles

@router.post("/", response_model=StudentProfileSchema)
def create_student_profile(
    *,
    db: Session = Depends(get_db),
    profile_in: StudentProfileCreate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Create new student profile.
    """
    # Check if profile already exists for user
    existing_profile = db.query(StudentProfile).filter(
        StudentProfile.user_id == current_user.id
    ).first()
    if existing_profile:
        raise HTTPException(
            status_code=400,
            detail="Student profile already exists for this user"
        )
    
    profile = StudentProfile(
        **profile_in.dict(),
        user_id=current_user.id
    )
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile

@router.get("/{profile_id}", response_model=StudentProfileSchema)
def get_student_profile(
    profile_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get student profile by ID.
    """
    profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    if not is_staff_or_admin(current_user) and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    return profile

@router.put("/{profile_id}", response_model=StudentProfileSchema)
def update_student_profile(
    *,
    db: Session = Depends(get_db),
    profile_id: int,
    profile_in: StudentProfileUpdate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update student profile.
    """
    profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    if not is_staff_or_admin(current_user) and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    for field, value in profile_in.dict(exclude_unset=True).items():
        setattr(profile, field, value)
    
    db.add(profile)
    db.commit()
    db.refresh(profile)
    return profile

@router.delete("/{profile_id}")
def delete_student_profile(
    *,
    db: Session = Depends(get_db),
    profile_id: int,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Delete student profile.
    """
    profile = db.query(StudentProfile).filter(StudentProfile.id == profile_id).first()
    if not profile:
        raise HTTPException(status_code=404, detail="Student profile not found")
    
    if not is_staff_or_admin(current_user) and profile.user_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db.delete(profile)
    db.commit()
    return {"message": "Student profile deleted successfully"}
