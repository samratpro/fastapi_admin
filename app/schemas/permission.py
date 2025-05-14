from pydantic import BaseModel, Field
from typing import List, Optional

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    pass

class RoleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None

class Role(RoleBase):
    id: int

    class Config:
        from_attributes = True

class PermissionList(BaseModel):
    permission_list: List[str]

    class Config:
        schema_extra = {
            "examples": {
                "student_permissions": {
                    "summary": "Permissions for Student model",
                    "description": "Grant create and read permissions for the Student model.",
                    "value": {
                        "permission_list": ["create", "read"]
                    }
                },
                "teacher_permissions": {
                    "summary": "Permissions for Teacher model",
                    "description": "Grant update permission for the Teacher model.",
                    "value": {
                        "permission_list": ["update"]
                    }
                }
            }
        }

class RolePermissionCreate(BaseModel):
    role_id: int
    model_name: str
    permission_list: List[str]

class RolePermission(RolePermissionCreate):
    id: int

    class Config:
        from_attributes = True


class PublicRoleSchema(BaseModel):
    id: int
    role_ids: List[int]

    class Config:
        orm_mode = True

class AdminAccessRoleSchema(BaseModel):
    id: int
    role_ids: List[int]

    class Config:
        orm_mode = True