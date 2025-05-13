from sqlalchemy import Column, Integer, JSON
from app.db.base_class import Base

class PublicRole(Base):
    __tablename__ = "public_roles"

    id = Column(Integer, primary_key=True)
    role_ids = Column(JSON, nullable=False, default=[])  # Stores a list, e.g., [2, 3, 5]