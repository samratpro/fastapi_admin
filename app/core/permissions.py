from functools import wraps
from fastapi import HTTPException
from sqlalchemy.orm import Session
from app.models.role_permission import RolePermissionModel

def has_permission(permission_type: str):
    """
    Decorator to check if user has permission for a specific action.
    permission_type: 'create', 'read', 'update', 'delete'
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user, db: Session, **kwargs):
            # Admin bypass
            if current_user.role and current_user.role.name == "admin":
                return await func(*args, current_user=current_user, db=db, **kwargs)

            # Get model name from the function's module
            model_name = func.__module__.split('.')[-1].split('_')[0].capitalize()
            
            # Check permission
            permission = db.query(RolePermissionModel).filter(
                RolePermissionModel.role_id == current_user.role_id,
                RolePermissionModel.model_name == model_name
            ).first()

            if not permission or permission_type not in permission.permissions:
                raise HTTPException(
                    status_code=403,
                    detail=f"No {permission_type} permission for {model_name}"
                )

            return await func(*args, current_user=current_user, db=db, **kwargs)
        return wrapper
    return decorator