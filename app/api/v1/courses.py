from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security import get_current_active_user
from app.core.permissions import has_permission
from app.db.base import get_db
from app.models.user import User
from app.models.course import Course
from app.schemas.course import CourseCreate, CourseUpdate, Course as CourseSchema

router = APIRouter()

@router.get("/", response_model=List[CourseSchema])
@has_permission("read", model_name="Course")
async def list_courses(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    courses = db.query(Course).offset(skip).limit(limit).all()
    return courses

@router.post("/", response_model=CourseSchema)
@has_permission("create", model_name="Course")
async def create_course(
    course_in: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    course = Course(**course_in.dict())
    db.add(course)
    db.commit()
    db.refresh(course)
    return course

@router.get("/{course_id}", response_model=CourseSchema)
@has_permission("read", model_name="Course")
async def get_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    return course

@router.put("/{course_id}", response_model=CourseSchema)
@has_permission("update", model_name="Course")
async def update_course(
    course_id: int,
    course_in: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    for field, value in course_in.dict(exclude_unset=True).items():
        setattr(course, field, value)
    
    db.add(course)
    db.commit()
    db.refresh(course)
    return course

@router.delete("/{course_id}")
@has_permission("delete", model_name="Course")
async def delete_course(
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    course = db.query(Course).filter(Course.id == course_id).first()
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")
    
    db.delete(course)
    db.commit()
    return {"message": "Course deleted successfully"}