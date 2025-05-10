from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from app.db.base import Base

class RolePermissionModel(Base):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    model_name = Column(String, nullable=False)  # e.g., "Student", "Teacher", "Course"
    permissions = Column(JSON, nullable=False)  # ["create", "read", "update", "delete"]