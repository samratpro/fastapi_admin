from typing import List, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.security import get_current_active_user, is_admin
from app.db.base import get_db
from app.models.user import User
from app.models.permission import Permission
from app.models.role import Role
from app.schemas.permission import (
    RoleCreate,
    RoleUpdate,
    Role as RoleSchema,
    Permission as PermissionSchema
)

router = APIRouter()

@router.get("/roles", response_model=List[RoleSchema])
def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Retrieve roles.
    """
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return db.query(Role).all()

@router.post("/roles", response_model=RoleSchema)
def create_role(
    *,
    db: Session = Depends(get_db),
    role_in: RoleCreate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Create new role.
    """
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    permissions = db.query(Permission).filter(
        Permission.id.in_(role_in.permissions)
    ).all()
    
    role = Role(
        name=role_in.name,
        description=role_in.description,
        permissions=permissions
    )
    db.add(role)
    db.commit()
    db.refresh(role)
    return role

@router.put("/roles/{role_id}", response_model=RoleSchema)
def update_role(
    *,
    db: Session = Depends(get_db),
    role_id: int,
    role_in: RoleUpdate,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Update role.
    """
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    if role_in.permissions is not None:
        permissions = db.query(Permission).filter(
            Permission.id.in_(role_in.permissions)
        ).all()
        role.permissions = permissions
    
    for field in ["name", "description"]:
        value = getattr(role_in, field)
        if value is not None:
            setattr(role, field, value)
    
    db.add(role)
    db.commit()
    db.refresh(role)
    return role

@router.delete("/roles/{role_id}")
def delete_role(
    *,
    db: Session = Depends(get_db),
    role_id: int,
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Delete role.
    """
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    
    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")
    
    db.delete(role)
    db.commit()
    return {"message": "Role deleted successfully"}

@router.get("/permissions", response_model=List[PermissionSchema])
def list_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """
    Retrieve permissions.
    """
    if not is_admin(current_user):
        raise HTTPException(status_code=403, detail="Not enough permissions")
    return db.query(Permission).all()
