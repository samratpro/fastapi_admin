from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from app.db.base import Base

class RolePermissionModel(Base):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    model_name = Column(JSON, nullable=False)  # e.g., ["Student", "Teacher", "Course"]
    permissions = Column(JSON, nullable=False)  # ["create", "read", "update", "delete"]
    user_role_and_permission = Column(
        JSON, 
        nullable=False,
        default={},
        server_default='{}'
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.user_role_and_permission is None:
            self.user_role_and_permission = {}
    """
        {"3" : {
            "1": ["create", "read", "update", "delete"],
            "2": ["create", "read", "update"],
            "3": ["read"]
             },
        "1" : {
            "3": ["create", "read", "update", "delete"],
            "2": ["create", "read", "update"],
            "1": ["read"]
        }
    """
