# api/user.py
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, Request, Query
from sqlalchemy.orm import Session
from pydantic import BaseModel, validator
from app.core.security import get_current_active_user, is_admin, get_password_hash
from app.db.base import get_db
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    User as UserSchema,
    UserWithPermissions,
    UserInDBBase
)
from app.utils.audit import log_activity
from app.core.user_permission import has_user_permission
from app.models.db_user_permission import RolePermissionModel
import json

router = APIRouter()


# Permission Management Endpoints
@router.get("/permissions", response_model=dict)
async def get_user_permissions(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Get user permissions based on role."""
    try:
        result = {}
        # if not current_user.role or current_user.role.name != "admin":
        #     raise HTTPException(status_code=403, detail="Admin access required")
        if current_user.role or current_user.role.name == "admin":
            # Admin can see all permissions
            permissions = db.query(RolePermissionModel).all()
            for permission in permissions:
                if permission.user_role_and_permission:
                    perms = permission.user_role_and_permission
                    if isinstance(perms, str):
                        perms = json.loads(perms)
                    result[str(permission.role_id)] = perms
        else:
            # Non-admin users can only see their own role's permissions
            permission = db.query(RolePermissionModel).filter(
                RolePermissionModel.role_id == current_user.role_id
            ).first()
            perms = permission.user_role_and_permission if permission else {}
            if isinstance(perms, str):
                perms = json.loads(perms)
            result[str(current_user.role_id)] = perms

        return {
            "permissions": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/permissions/{role_id}", response_model=dict)
async def update_user_permission(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    role_id: int,
    target_role_id: int,
    permissions: List[str],
    request: Request
) -> Any:
    """Update user permissions for a role."""
    try:
        # Check if user has permission to modify
        if not current_user.role or current_user.role.name != "admin":
            raise HTTPException(status_code=403, detail="Only admins can Update permissions")

        permission = db.query(RolePermissionModel).filter(
            RolePermissionModel.role_id == role_id
        ).first()

        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")

        # Validate permissions
        valid_permissions = {"create", "read", "update", "delete"}
        invalid_perms = set(permissions) - valid_permissions
        if invalid_perms:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid permissions found: {invalid_perms}"
            )

        # Store old permissions for logging
        old_permissions = permission.user_role_and_permission.get(str(target_role_id), [])

        # Update permissions
        updated_permissions = dict(permission.user_role_and_permission)
        updated_permissions[str(target_role_id)] = permissions
        
        permission.user_role_and_permission = updated_permissions
        db.add(permission)
        db.commit()
        db.refresh(permission)

        await log_activity(
            db=db,
            user=current_user,
            action="UPDATE",
            resource_type="UserPermission",
            resource_id=role_id,
            changes={
                "target_role": target_role_id,
                "old": old_permissions,
                "new": permissions
            },
            request=request
        )

        return {
            "message": "Permissions updated successfully",
            "role_id": role_id,
            "target_role_id": target_role_id,
            "old_permissions": old_permissions,
            "new_permissions": permissions
        }
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))




    
@router.delete("/permissions/{role_id}/{target_role_id}", response_model=dict)
async def delete_user_permission(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
    role_id: int,
    target_role_id: int,
    request: Request
) -> Any:
    """Remove user permissions for a role."""
    try:
        # Only admin can delete permissions
        if not current_user.role or current_user.role.name != "admin":
            raise HTTPException(status_code=403, detail="Only admins can delete permissions")

        # Fetch the permission record
        permission = db.query(RolePermissionModel).filter(
            RolePermissionModel.role_id == role_id
        ).first()

        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")

        # Get and parse the permissions
        permissions_data = permission.user_role_and_permission
        if isinstance(permissions_data, str):
            import json
            permissions_data = json.loads(permissions_data)
        
        # Make a copy of the permissions data to modify
        updated_permissions = dict(permissions_data)
        
        # Store old permissions for logging
        old_permissions = None
        
        # Check if the role exists in the permissions
        if str(target_role_id) in updated_permissions:
            old_permissions = updated_permissions[str(target_role_id)]
            # Remove the target_role_id and its permissions
            del updated_permissions[str(target_role_id)]
            
            print(f"DEBUG: Updated permissions data: {updated_permissions}")
            
            # Update the database
            permission.user_role_and_permission = updated_permissions
            db.add(permission)
            db.commit()
            db.refresh(permission)

            print(f"DEBUG: Final permissions in DB: {permission.user_role_and_permission}")

            await log_activity(
                db=db,
                user=current_user,
                action="DELETE",
                resource_type="UserPermission",
                resource_id=role_id,
                changes={
                    "target_role": target_role_id,
                    "deleted_permissions": old_permissions
                },
                request=request
            )

            return {
                "message": "Permissions removed successfully",
                "role_id": role_id,
                "target_role_id": target_role_id,
                "deleted_permissions": old_permissions
            }
        else:
            raise HTTPException(
                status_code=404,
                detail=f"No permissions found for target role {target_role_id}"
            )

    except Exception as e:
        db.rollback()
        print(f"DEBUG: Error occurred: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))




# User Management Endpoints
@router.get("/", response_model=dict)
@has_user_permission("read")
async def list_users(
    *,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
) -> Any:
    """Retrieve users based on read permissions."""
    try:
        query = db.query(User)

        # Admin can see all users
        if is_admin(current_user):
            users = query.all()
        else:
            # Retrieve permissions for the current user's role
            permission = db.query(RolePermissionModel).filter(
                RolePermissionModel.role_id == current_user.role_id
            ).first()

            if not permission or not permission.user_role_and_permission:
                raise HTTPException(
                    status_code=403,
                    detail="No permissions found for this role"
                )

            # Get role IDs where the user has 'read' permission
            readable_role_ids = [
                int(role_id) for role_id, perms in permission.user_role_and_permission.items()
                if "read" in perms
            ]

            if not readable_role_ids:
                raise HTTPException(
                    status_code=403,
                    detail="No read permissions for any roles"
                )

            # Filter users by roles the current user can read
            query = query.filter(User.role_id.in_(readable_role_ids))
            users = query.all()

        # Convert User model instances to UserSchema
        users_serialized = [UserSchema.from_orm(user) for user in users]

        return {
            "items": users_serialized
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/", response_model=UserSchema)
@has_user_permission("create")
async def create_user(
    *,
    db: Session = Depends(get_db),
    user_in: UserCreate,
    current_user: User = Depends(get_current_active_user),
    request: Request
) -> Any:
    """Create a new user."""
    try:
        # Check role-specific permission for non-admin users
        if not is_admin(current_user):
            permission = db.query(RolePermissionModel).filter(
                RolePermissionModel.role_id == current_user.role_id
            ).first()

            if not permission or not permission.user_role_and_permission:
                raise HTTPException(
                    status_code=403,
                    detail="No permissions found for this role"
                )

            target_role_perms = permission.user_role_and_permission.get(str(user_in.role_id), [])
            if "create" not in target_role_perms:
                raise HTTPException(
                    status_code=403,
                    detail=f"No permission to create users with role ID {user_in.role_id}"
                )

        if db.query(User).filter(User.username == user_in.username).first():
            raise HTTPException(
                status_code=400,
                detail=f"Username '{user_in.username}' is already in use"
            )

        if db.query(User).filter(User.email == user_in.email).first():
            raise HTTPException(
                status_code=400,
                detail=f"Email '{user_in.email}' is already in use"
            )

        user = User(
            email=user_in.email,
            username=user_in.username,
            hashed_password=get_password_hash(user_in.password),
            first_name=user_in.first_name,
            last_name=user_in.last_name,
            role_id=user_in.role_id,
            is_active=True,
            is_verified=True
        )

        db.add(user)
        db.commit()
        db.refresh(user)

        await log_activity(
            db=db,
            user=current_user,
            action="CREATE",
            resource_type="User",
            resource_id=user.id,
            changes=user_in.dict(exclude={"password"}),
            request=request
        )

        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{user_id}", response_model=UserSchema)
@has_user_permission("update")
async def update_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    user_in: UserUpdate,
    current_user: User = Depends(get_current_active_user),
    request: Request
) -> Any:
    """Update user."""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        # Check role-specific permission for non-admin users
        if not is_admin(current_user):
            permission = db.query(RolePermissionModel).filter(
                RolePermissionModel.role_id == current_user.role_id
            ).first()

            if not permission or not permission.user_role_and_permission:
                raise HTTPException(
                    status_code=403,
                    detail="No permissions found for this role"
                )

            current_role_perms = permission.user_role_and_permission.get(str(user.role_id), [])
            if "update" not in current_role_perms:
                raise HTTPException(
                    status_code=403,
                    detail=f"No permission to update users with role ID {user.role_id}"
                )

            update_data = user_in.dict(exclude_unset=True)
            if "role_id" in update_data and update_data["role_id"] != user.role_id:
                new_role_perms = permission.user_role_and_permission.get(str(update_data["role_id"]), [])
                if "update" not in new_role_perms:
                    raise HTTPException(
                        status_code=403,
                        detail=f"No permission to change user to role ID {update_data['role_id']}"
                    )

        update_data = user_in.dict(exclude_unset=True)
        if "username" in update_data and update_data["username"] != user.username:
            if db.query(User).filter(User.username == update_data["username"]).first():
                raise HTTPException(
                    status_code=400,
                    detail=f"Username '{update_data['username']}' is already in use"
                )

        if "email" in update_data and update_data["email"] != user.email:
            if db.query(User).filter(User.email == update_data["email"]).first():
                raise HTTPException(
                    status_code=400,
                    detail=f"Email '{update_data['email']}' is already in use"
                )

        changes = {}
        for field, value in update_data.items():
            if field == "password" and value:
                changes[field] = "***"
                value = get_password_hash(value)
            elif value != getattr(user, field):
                changes[field] = value
            setattr(user, field, value)

        db.add(user)
        db.commit()
        db.refresh(user)

        if changes:
            await log_activity(
                db=db,
                user=current_user,
                action="UPDATE",
                resource_type="User",
                resource_id=user.id,
                changes=changes,
                request=request
            )

        return user
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{user_id}")
@has_user_permission("delete")
async def delete_user(
    *,
    db: Session = Depends(get_db),
    user_id: int,
    current_user: User = Depends(get_current_active_user),
    request: Request
) -> Any:
    """Delete user."""
    try:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=404, detail="User not found")

        if user.id == current_user.id:
            raise HTTPException(status_code=400, detail="Cannot delete your own account")

        # Check role-specific permission for non-admin users
        if not is_admin(current_user):
            permission = db.query(RolePermissionModel).filter(
                RolePermissionModel.role_id == current_user.role_id
            ).first()

            if not permission or not permission.user_role_and_permission:
                raise HTTPException(
                    status_code=403,
                    detail="No permissions found for this role"
                )

            target_role_perms = permission.user_role_and_permission.get(str(user.role_id), [])
            if "delete" not in target_role_perms:
                raise HTTPException(
                    status_code=403,
                    detail=f"No permission to delete users with role ID {user.role_id}"
                )

        db.delete(user)
        db.commit()

        await log_activity(
            db=db,
            user=current_user,
            action="DELETE",
            resource_type="User",
            resource_id=user_id,
            request=request
        )

        return {"message": "User deleted successfully"}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))