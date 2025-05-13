from functools import wraps
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.db_user_permission import RolePermissionModel
import json

def has_permission(permission_type: str, model_name: str = None):
    """
    Decorator to check if user has permission for a specific action.
    permission_type: 'create', 'read', 'update', 'delete'
    model_name: Optional explicit model name for permission checks.
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user, db: Session, **kwargs):
            # Admin bypass
            if current_user.role and current_user.role.name == "admin":
                return await func(*args, current_user=current_user, db=db, **kwargs)

            # Use explicit model_name if provided, otherwise infer from the module
            inferred_model_name = func.__module__.split('.')[-1].split('_')[0].capitalize()
            target_model_name = model_name or inferred_model_name

            # Check permission in model_permissions
            permission = db.query(RolePermissionModel).filter(
                RolePermissionModel.role_id == current_user.role_id
            ).first()

            if not permission or not permission.model_permissions:
                raise HTTPException(
                    status_code=403,
                    detail=f"No permissions found for role {current_user.role_id}"
                )

            # Get model-specific permissions for the role
            role_perms = permission.model_permissions.get(str(current_user.role_id), {})
            model_perms = role_perms.get(target_model_name, [])

            if permission_type not in model_perms:
                raise HTTPException(
                    status_code=403,
                    detail=f"No {permission_type} permission for {target_model_name}"
                )

            return await func(*args, current_user=current_user, db=db, **kwargs)
        return wrapper
    return decorator