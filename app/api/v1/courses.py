from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security import get_current_active_user, is_staff_or_admin
from app.db.base import get_db
from app.models.user import User
from app.models.course import Course
from app.schemas.course import CourseCreate, CourseUpdate, Course as CourseSchema

router = APIRouter()

@router.get("/", response_model=List[CourseSchema])
def list_courses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Retrieve courses.
    """
    courses = db.query(Course).offset(skip).limit(limit).all()
    return courses

@router.post("/", response_model=CourseSchema)
def create_course(
    *,
    db: Session = Depends(get_db),
    course_in: CourseCreate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Create new course.
    """
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    course = Course(
        **course_in.dict(),
        instructor_id=current_user.id
    )
    db.add(course)
    db.commit()
    db.refresh(course)
    return course

@router.get("/{course_id}", response_model=CourseSchema)
def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Get course by ID.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.put("/{course_id}", response_model=CourseSchema)
def update_course(
    *,
    db: Session = Depends(get_db),
    course_id: int,
    course_in: CourseUpdate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update course.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if not is_staff_or_admin(current_user) and course.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    for field, value in course_in.dict(exclude_unset=True).items():
        setattr(course, field, value)
    
    db.add(course)
    db.commit()
    db.refresh(course)
    return course

@router.delete("/{course_id}")
def delete_course(
    *,
    db: Session = Depends(get_db),
    course_id: int,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Delete course.
    """
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    if not is_staff_or_admin(current_user) and course.instructor_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    db.delete(course)
    db.commit()
    return {"message": "Course deleted successfully"}
