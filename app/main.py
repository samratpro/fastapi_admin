# app/main.py
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from app.core.admin import AdminModelRegister
from app.models.user import User
from app.models.student_profile import StudentProfile
from app.models.course import Course
from app.core.security import get_current_active_user, is_staff_or_admin
from app.db.base import Base, engine
from app.api.v1 import admin, auth, courses, rbac, student_profiles, users

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Fast API Admin Panel API",
    description="API for FastAPI dynamic admin panel.",
    version="1.0.0",
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register models with metadata options - these are just examples
AdminModelRegister.register(
    User,
    list_display=["username", "email", "is_active"],
    search_fields=["username", "email"],
    filter_fields=["is_active"],
    ordering=["-created_at"]
)

AdminModelRegister.register(
    StudentProfile,
    list_display=["student_id", "department", "gender"],
    search_fields=["student_id", "department"],
    filter_fields=["gender", "department"],
    ordering=["-created_at"]
)

# Register Course model once with its metadata
AdminModelRegister.register(
    Course,
    list_display=["code", "title", "credits"],
    search_fields=["code", "title"],
    filter_fields=["credits"],
    ordering=["-created_at"]
)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(rbac.router, prefix="/api/rbac", tags=["rbac"])
app.include_router(courses.router, prefix="/api/courses", tags=["courses"])
app.include_router(student_profiles.router, prefix="/api/student-profiles", tags=["student-profiles"])

@app.get("/api/metadata")
async def get_metadata(
    current_user: User = Depends(get_current_active_user)
):
    """Get metadata for admin panel"""
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return AdminModelRegister.get_metadata()

@app.get("/")
async def root():
    return {"message": "School Management System API"}

