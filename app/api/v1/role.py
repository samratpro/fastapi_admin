from fastapi import APIRouter, Depends, HTTPException, status
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
import json
from app.core.admin import AdminModelRegister

router = APIRouter()

@router.post("/roles", response_model=RoleSchema)
async def create_role(
    *,
    db: Session = Depends(get_db),
    role_in: RoleCreate,
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new role (admin only).
    """
    # Verify if the current user is an admin
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can create roles."
        )
    
    # Normalize the role name to lowercase for consistency
    role_name = role_in.name.strip().lower()
    
    # Check if the role already exists
    existing_role = db.query(Role).filter(Role.name == role_name).first()
    if existing_role:
        raise HTTPException(
            status_code=400,
            detail=f"Role '{role_name}' already exists."
        )
    
    # Create the role if all checks pass
    new_role = Role(name=role_name)
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role


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