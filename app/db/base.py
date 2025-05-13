from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

from app.db.base_class import Base
# Import all models to register with Base.metadata
from app.models.user import User
from app.models.role import Role
from app.models.db_user_permission import RolePermissionModel
from app.models.public_role import PublicRole
from app.models.admin_access_role import AdminAccessRole

logger = logging.getLogger(__name__)

# Create database engine and session
try:
    engine = create_engine(settings.DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
except Exception as e:
    logger.error(f"Failed to connect to database: {e}")
    raise

# Dependency for getting database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Optional: Create tables for development/testing (comment out in production)
# Base.metadata.create_all(bind=engine)