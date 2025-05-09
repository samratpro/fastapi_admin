from pydantic import BaseModel
from typing import List, Optional

class PermissionBase(BaseModel):
    name: str
    description: Optional[str] = None

class PermissionCreate(PermissionBase):
    pass

class Permission(PermissionBase):
    id: int

    class Config:
        from_attributes = True

class RoleBase(BaseModel):
    name: str
    description: Optional[str] = None

class RoleCreate(RoleBase):
    permissions: List[int]

class RoleUpdate(RoleBase):
    permissions: Optional[List[int]] = None

class Role(RoleBase):
    id: int
    permissions: List[Permission]

    class Config:
        from_attributes = True
