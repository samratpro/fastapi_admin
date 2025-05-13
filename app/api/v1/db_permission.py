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


@router.get("/models-and-permissions")
async def get_models_and_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Retrieve all registered models and existing permissions
    """
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        # Get all registered models
        registered_models = AdminModelRegister.get_registered_models()
        model_list = [model.__name__ for model in registered_models]

        # Get all existing permissions from the database
        permissions = db.query(RolePermissionModel).all()
        permissions_list = []

        for perm in permissions:
            try:
                # Validate and parse model_name
                model_name = perm.model_name
                if isinstance(model_name, str):
                    model_name = json.loads(model_name)  # Parse JSON if stored as a string
                elif model_name is None:
                    model_name = []  # Default to an empty list if NULL
                elif not isinstance(model_name, list):
                    raise ValueError("Invalid model_name format")
                
                permissions_list.append({
                    "role_id": perm.role_id,
                    "model_name": model_name,
                    "permissions": perm.permissions
                })
            except (ValueError, TypeError, json.JSONDecodeError) as e:
                # Log invalid entries and skip them
                print(f"Skipping invalid entry: {perm.model_name} (Error: {e})")
                continue

        return {
            "models": model_list,
            "permissions": permissions_list
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"An error occurred while retrieving models and permissions: {str(e)}"
        )


@router.post("/permissions")
async def set_permissions(
    permission_in: RolePermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Set permissions for a role (replace existing permissions if role_id matches)."""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    valid_permissions = {"create", "read", "update", "delete"}
    if not all(p in valid_permissions for p in permission_in.permissions):
        raise HTTPException(status_code=400, detail="Invalid permissions")

    # Validate model_name
    if not isinstance(permission_in.model_name, list):
        permission_in.model_name = [permission_in.model_name]
    for model in permission_in.model_name:
        if not isinstance(model, str):
            raise HTTPException(status_code=400, detail="Invalid model name format")

    # Check if role exists
    role = db.query(Role).filter(Role.id == permission_in.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Delete existing permissions for the role_id
    db.query(RolePermissionModel).filter(RolePermissionModel.role_id == permission_in.role_id).delete()

    # Create new permissions
    for model in permission_in.model_name:
        permission_data = {
            "role_id": permission_in.role_id,
            "model_name": json.dumps([model]),  # Ensure it's a valid JSON array
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