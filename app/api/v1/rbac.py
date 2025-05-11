from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.db.base import get_db
from app.models.user import User
from app.models.role import Role
from app.models.role_permission import RolePermissionModel
from app.schemas.permission import (
    RoleCreate, 
    Role as RoleSchema, 
    RolePermissionCreate,
    RoleUpdate
)
from app.core.security import get_current_active_user

router = APIRouter()

@router.post("/roles", response_model=RoleSchema)
async def create_role(
    role_in: RoleCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Create a new role"""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    existing = db.query(Role).filter(Role.name == role_in.name).first()
    if existing:
        raise HTTPException(status_code=400, detail="Role already exists")

    role = Role(**role_in.dict())
    db.add(role)
    db.commit()
    db.refresh(role)
    return role

@router.get("/roles", response_model=List[RoleSchema])
async def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all roles"""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return db.query(Role).all()

@router.put("/roles/{role_id}", response_model=RoleSchema)
async def update_role(
    role_id: int,
    role_in: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a role"""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.name == "admin" and role_in.name != "admin":
        raise HTTPException(status_code=400, detail="Cannot modify admin role name")

    for field, value in role_in.dict(exclude_unset=True).items():
        setattr(role, field, value)

    db.commit()
    db.refresh(role)
    return role

@router.delete("/roles/{role_id}")
async def delete_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Delete a role"""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.name == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin role")

    # Check if role is assigned to any users
    if db.query(User).filter(User.role_id == role_id).first():
        raise HTTPException(
            status_code=400, 
            detail="Cannot delete role that is assigned to users"
        )

    db.delete(role)
    db.commit()
    return {"message": "Role deleted successfully"}


@router.post("/permissions")
async def set_permissions(
    permission_in: RolePermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Set permissions for a role on multiple models"""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    valid_permissions = {"create", "read", "update", "delete"}
    if not all(p in valid_permissions for p in permission_in.permissions):
        raise HTTPException(status_code=400, detail="Invalid permissions")

    # Check if role exists
    role = db.query(Role).filter(Role.id == permission_in.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Handle multiple models
    if not isinstance(permission_in.model_name, list):
        permission_in.model_name = [permission_in.model_name]

    for model in permission_in.model_name:
        # Update or create permission for each model
        permission = db.query(RolePermissionModel).filter(
            RolePermissionModel.role_id == permission_in.role_id,
            RolePermissionModel.model_name == model
        ).first()

        if permission:
            permission.permissions = permission_in.permissions
        else:
            permission_data = {
                "role_id": permission_in.role_id,
                "model_name": model,
                "permissions": permission_in.permissions,
            }
            permission = RolePermissionModel(**permission_data)
            db.add(permission)

    db.commit()
    return {"message": "Permissions updated successfully"}


@router.delete("/permissions/{role_id}/{model_name}")
async def remove_permissions(
    role_id: int,
    model_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove all permissions for a role on a specific model"""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    permission = db.query(RolePermissionModel).filter(
        RolePermissionModel.role_id == role_id,
        RolePermissionModel.model_name == model_name
    ).first()

    if not permission:
        raise HTTPException(
            status_code=404, 
            detail=f"No permissions found for role {role_id} on model {model_name}"
        )

    db.delete(permission)
    db.commit()
    return {"message": "Permissions removed successfully"}

@router.get("/permissions/{role_id}")
async def get_role_permissions(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get all permissions for a role"""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    permissions = db.query(RolePermissionModel).filter(
        RolePermissionModel.role_id == role_id
    ).all()
    
    return {
        "role": role.name,
        "permissions": [
            {
                "model": perm.model_name,
                "permissions": perm.permissions
            }
            for perm in permissions
        ]
    }