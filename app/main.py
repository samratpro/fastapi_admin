from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.core.admin import AdminModelRegister
from app.models.user import User
from app.models.course import Course
from app.models.student_profile import StudentProfile
from app.core.security import get_current_active_user, is_staff_or_admin
from app.db.base import Base, engine, get_db
from app.api.v1 import admin, auth, courses, rbac, student_profiles, admin, users


# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Custom Title",
    description="Custom description.",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)


# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Register models
AdminModelRegister.register(User)
AdminModelRegister.register(Course)
AdminModelRegister.register(StudentProfile)

# Include routers
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(rbac.router, prefix="/api/rbac", tags=["rbac"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(courses.router, prefix="/api/courses", tags=["courses"])
app.include_router(student_profiles.router, prefix="/api/student-profiles", tags=["student-profiles"])

@app.get("/api/metadata")
async def get_metadata(
    current_user: User = Depends(get_current_active_user)
):
    if not is_staff_or_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return AdminModelRegister.get_metadata()

@app.get("/")
async def root():
    return {"message": "FastAPI Admin API"}

