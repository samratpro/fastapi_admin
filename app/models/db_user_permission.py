from sqlalchemy import Column, Integer, String, ForeignKey, JSON
from app.db.base import Base

class RolePermissionModel(Base):
    __tablename__ = "role_permissions"

    id = Column(Integer, primary_key=True)
    role_id = Column(Integer, ForeignKey("roles.id"))
    model_permissions = Column(
        JSON, 
        nullable=False,
        default={},
        server_default='{}'
    )
    user_role_and_permission = Column(
        JSON, 
        nullable=False,
        default={},
        server_default='{}'
    )

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        if self.model_permissions is None:
            self.model_permissions = {}
        if self.user_role_and_permission is None:
            self.user_role_and_permission = {}

"""
model_permissions
"role_id" : {
            "Teacher": ["create", "read", "update", "delete"],
            "Student": ["create", "read", "update"],
            "Anyother": ["read"]
             },
"role_id" : {
            "Teacher": ["create", "read", "update", "delete"],
            "Student": ["create", "read", "update"],
            "Anyother": ["read"]
             },

user_role_and_permission
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