from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from app.core.admin import AdminModelRegister
from app.models.user import User
from app.models.course import Course
from app.core.security import get_current_active_user
from app.core.db_permissions import has_permission
from app.db.base import get_db  # Import get_db from session
from app.db.base import Base, engine
from app.api.v1 import admin, auth, courses, db_permission, users, role

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


# Register Course model with its metadata
AdminModelRegister.register(
    Course,
    list_display=["code", "title", "credits"],
    search_fields=["code", "title"],
    filter_fields=["credits"],
    ordering=["-created_at"],
    title_help_text="Enter the full course title",
    description_help_text="Detailed course description",
    status_choices=[
        ("active", "Active"),
        ("inactive", "Inactive"),
        ("archived", "Archived")
    ],
    description_widget="rich_text",
    form_layout=[
        {"section": "Basic Information", "fields": ["code", "title", "credits"]},
        {"section": "Details", "fields": ["description", "prerequisites"]},
        {"section": "Settings", "fields": ["status", "is_active"]}
    ],
    students_display_fields=["id", "full_name", "email"]
)

# Include routers
app.include_router(role.router, prefix="/api/roles", tags=["roles"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(users.router, prefix="/api/users", tags=["users"])
app.include_router(db_permission.router, prefix="/api/db_model", tags=["db_permission"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])
app.include_router(courses.router, prefix="/api/courses", tags=["courses"])


@app.get("/api/metadata")
@has_permission("read", model_name="Metadata")
async def get_metadata(
    current_user: User = Depends(get_current_active_user),
    db: Session = Depends(get_db)  # Add the db dependency
):
    """
    Get metadata for the admin panel
    """
    return AdminModelRegister.get_metadata()


@app.get("/api")
async def root():
    return {"message": "FastAPI Admin Panel API"}