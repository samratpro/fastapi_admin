from functools import wraps
from fastapi import HTTPException
from app.models.user import User

def has_permission(permission_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, current_user: User, **kwargs):
            if not current_user.role_obj:
                raise HTTPException(
                    status_code=403,
                    detail="No role assigned"
                )
            
            user_permissions = {
                p.name for p in current_user.role_obj.permissions
            }
            
            if permission_name not in user_permissions:
                raise HTTPException(
                    status_code=403,
                    detail="Not enough permissions"
                )
            
            return await func(*args, current_user=current_user, **kwargs)
        return wrapper
    return decorator
