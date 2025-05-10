from pydantic import BaseModel
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

class RolePermissionCreate(BaseModel):
    role_id: int
    model_name: str
    permissions: List[str]

class RolePermission(RolePermissionCreate):
    id: int

    class Config:
        from_attributes = True