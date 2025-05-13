from functools import wraps
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.user import User
from app.models.role_permission import RolePermissionModel

def has_user_permission(action: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            current_user = kwargs.get("current_user")
            db = kwargs.get("db")

            if not current_user or not db:
                raise HTTPException(status_code=403, detail="Authentication required")

            # Admin bypass
            if current_user.role.name.lower() == "admin":
                return await func(*args, **kwargs)

            # Get user's role permissions
            permission = db.query(RolePermissionModel).filter(
                RolePermissionModel.role_id == current_user.role_id
            ).first()

            if not permission or not permission.user_role_and_permission:
                raise HTTPException(
                    status_code=403,
                    detail="No permissions found for this role"
                )

            # Check if the user has the specified action permission for any role
            has_permission = any(
                action in perms for role_id, perms in permission.user_role_and_permission.items()
            )

            if not has_permission:
                raise HTTPException(
                    status_code=403,
                    detail=f"No {action} permission for any roles"
                )

            return await func(*args, **kwargs)
        return wrapper
    return decorator