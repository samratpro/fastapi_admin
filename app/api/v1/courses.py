from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from app.core.security import get_current_active_user
from app.core.db_permissions import has_permission
from app.db.base import get_db
from app.models.user import User
from app.models.course import Course
from app.schemas.course import CourseCreate, CourseUpdate, Course as CourseSchema
from app.utils.audit import log_activity
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get(
    "/",
    response_model=dict,
    summary="List all courses",
    description="Retrieve a paginated list of courses. Requires 'read' permission for the Course model."
)
@has_permission("read", model_name="course")
async def list_courses(
    request: Request,
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    try:
        logger.debug(f"Checking read permission for user {current_user.id} (role {current_user.role_id}) on course")
        courses = db.query(Course).offset(skip).limit(limit).all()
        course_ids = [course.id for course in courses]
        logger.debug(f"User {current_user.id} retrieved courses: {course_ids}")

        await log_activity(
            db=db,
            user=current_user,
            action="READ",
            resource_type="Course",
            resource_id=None,
            changes={"course_ids": course_ids, "skip": skip, "limit": limit},
            request=request
        )

        return {"items": [CourseSchema.from_orm(course) for course in courses]}
    except Exception as e:
        logger.error(f"Error in list_courses: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post(
    "/",
    response_model=CourseSchema,
    summary="Create a new course",
    description="Create a new course. Requires 'create' permission for the Course model."
)
@has_permission("create", model_name="course")
async def create_course(
    request: Request,
    course_in: CourseCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    try:
        logger.debug(f"Checking create permission for user {current_user.id} (role {current_user.role_id}) on course")
        course = Course(**course_in.dict())
        db.add(course)
        db.commit()
        db.refresh(course)
        logger.debug(f"User {current_user.id} created course {course.id}")

        await log_activity(
            db=db,
            user=current_user,
            action="CREATE",
            resource_type="Course",
            resource_id=course.id,
            changes=course_in.dict(),
            request=request
        )

        return CourseSchema.from_orm(course)
    except Exception as e:
        db.rollback()
        logger.error(f"Error in create_course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get(
    "/{course_id}",
    response_model=CourseSchema,
    summary="Get a specific course",
    description="Retrieve a course by ID. Requires 'read' permission for the Course model."
)
@has_permission("read", model_name="course")
async def get_course(
    request: Request,
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    try:
        logger.debug(f"Checking read permission for user {current_user.id} (role {current_user.role_id}) on course")
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        logger.debug(f"User {current_user.id} retrieved course {course_id}")

        await log_activity(
            db=db,
            user=current_user,
            action="READ",
            resource_type="Course",
            resource_id=course_id,
            changes={},
            request=request
        )

        return CourseSchema.from_orm(course)
    except Exception as e:
        logger.error(f"Error in get_course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put(
    "/{course_id}",
    response_model=CourseSchema,
    summary="Update a course",
    description="Update an existing course by ID. Requires 'update' permission for the Course model."
)
@has_permission("update", model_name="course")
async def update_course(
    request: Request,
    course_id: int,
    course_in: CourseUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    try:
        logger.debug(f"Checking update permission for user {current_user.id} (role {current_user.role_id}) on course")
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        changes = {}
        for field, value in course_in.dict(exclude_unset=True).items():
            old_value = getattr(course, field)
            if value != old_value:
                changes[field] = {"old": old_value, "new": value}
                setattr(course, field, value)

        db.add(course)
        db.commit()
        db.refresh(course)
        logger.debug(f"User {current_user.id} updated course {course_id}")

        if changes:
            await log_activity(
                db=db,
                user=current_user,
                action="UPDATE",
                resource_type="Course",
                resource_id=course_id,
                changes=changes,
                request=request
            )

        return CourseSchema.from_orm(course)
    except Exception as e:
        db.rollback()
        logger.error(f"Error in update_course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete(
    "/{course_id}",
    response_model=dict,
    summary="Delete a course",
    description="Delete a course by ID. Requires 'delete' permission for the Course model."
)
@has_permission("delete", model_name="course")
async def delete_course(
    request: Request,
    course_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    try:
        logger.debug(f"Checking delete permission for user {current_user.id} (role {current_user.role_id}) on course")
        course = db.query(Course).filter(Course.id == course_id).first()
        if not course:
            raise HTTPException(status_code=404, detail="Course not found")

        db.delete(course)
        db.commit()
        logger.debug(f"User {current_user.id} deleted course {course_id}")

        await log_activity(
            db=db,
            user=current_user,
            action="DELETE",
            resource_type="Course",
            resource_id=course_id,
            changes={},
            request=request
        )

        return {"message": "Course deleted successfully"}
    except Exception as e:
        db.rollback()
        logger.error(f"Error in delete_course: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))