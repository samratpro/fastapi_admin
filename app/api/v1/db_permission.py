from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.db.base import get_db
from app.models.user import User
from app.models.role import Role
from app.models.db_user_permission import RolePermissionModel
from app.schemas.permission import RolePermissionCreate
from app.core.security import get_current_active_user
import json
from app.core.admin import AdminModelRegister

router = APIRouter()

@router.post("/permissions")
async def set_permissions(
    permission_in: RolePermissionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Set or update model-specific permissions for a role in a single row."""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    # Validate permission_list
    valid_permissions = {"create", "read", "update", "delete"}
    if not all(p in valid_permissions for p in permission_in.permission_list):
        raise HTTPException(status_code=400, detail="Invalid permissions. Must be create, read, update, or delete")

    # Validate model_name
    if not isinstance(permission_in.model_name, str):
        raise HTTPException(status_code=400, detail="Model name must be a string")

    # Check if role exists
    role = db.query(Role).filter(Role.id == permission_in.role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    # Find existing permission entry for the role_id
    permission = db.query(RolePermissionModel).filter(
        RolePermissionModel.role_id == permission_in.role_id
    ).first()

    if permission:
        # Update existing entry
        user_role_perms = dict(permission.user_role_and_permission)
        role_perms = user_role_perms.get(str(permission_in.role_id), {})
        
        # Update or add model_name permissions
        role_perms[permission_in.model_name] = permission_in.permission_list
        user_role_perms[str(permission_in.role_id)] = role_perms
        
        permission.user_role_and_permission = user_role_perms
        permission.model_name = json.dumps(list(role_perms.keys()))
        permission.permissions = json.dumps([])  # Empty, as permissions are in user_role_and_permission
    else:
        # Create new entry
        role_perms = {permission_in.model_name: permission_in.permission_list}
        permission_data = {
            "role_id": permission_in.role_id,
            "model_name": json.dumps([permission_in.model_name]),
            "permissions": json.dumps([]),
            "user_role_and_permission": {str(permission_in.role_id): role_perms}
        }
        permission = RolePermissionModel(**permission_data)
        db.add(permission)

    db.commit()
    return {"message": "Permissions updated successfully"}

@router.get("/models-and-permissions")
async def get_models_and_permissions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        registered_models = AdminModelRegister.get_registered_models()
        model_list = [model.__name__ for model in registered_models]

        permissions = db.query(RolePermissionModel).all()
        permissions_list = []

        for perm in permissions:
            try:
                model_name = perm.model_name
                if isinstance(model_name, str):
                    model_name = json.loads(model_name)
                elif model_name is None:
                    model_name = []
                elif not isinstance(model_name, list):
                    raise ValueError("Invalid model_name format")
                
                user_role_perms = perm.user_role_and_permission.get(str(perm.role_id), {})
                
                permissions_list.append({
                    "role_id": perm.role_id,
                    "model_permissions": user_role_perms
                })
            except (ValueError, TypeError, json.JSONDecodeError) as e:
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

@router.get("/permissions/{role_id}")
async def get_role_permissions(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    role = db.query(Role).filter(Role.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    permission = db.query(RolePermissionModel).filter(
        RolePermissionModel.role_id == role_id
    ).first()
    
    if not permission:
        return {
            "role": role.name,
            "permissions": {}
        }

    return {
        "role": role.name,
        "permissions": permission.user_role_and_permission.get(str(role_id), {})
    }

@router.delete("/permissions/{role_id}/{model_name}")
async def remove_permissions(
    role_id: int,
    model_name: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    permission = db.query(RolePermissionModel).filter(
        RolePermissionModel.role_id == role_id
    ).first()

    if not permission:
        raise HTTPException(
            status_code=404, 
            detail=f"No permissions found for role {role_id}"
        )

    user_role_perms = dict(permission.user_role_and_permission)
    role_perms = user_role_perms.get(str(role_id), {})
    
    if model_name not in role_perms:
        raise HTTPException(
            status_code=404,
            detail=f"No permissions found for model {model_name} on role {role_id}"
        )

    del role_perms[model_name]
    user_role_perms[str(role_id)] = role_perms
    permission.user_role_and_permission = user_role_perms
    permission.model_name = json.dumps(list(role_perms.keys()))

    db.add(permission)
    db.commit()
    return {"message": "Permissions removed successfully"}