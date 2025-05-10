from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
import logging

from app.db.base_class import Base  # noqa
from app.models.user import User  # noqa
from app.models.role import Role  # noqa
from app.models.course import Course  # noqa
from app.models.student_profile import StudentProfile  # noqa
from app.models.course import Course  # noqa

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