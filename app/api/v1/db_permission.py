from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified
from app.db.base import get_db
from app.models.user import User
from app.models.role import Role
from app.models.db_user_permission import RolePermissionModel
from app.schemas.permission import PermissionList
from app.core.security import get_current_active_user
from app.utils.audit import log_activity
from app.core.admin import AdminModelRegister
import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.get("/permissions", response_model=dict)
async def get_model_permissions(
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get model permissions based on role."""
    try:
        result = {}
        if current_user.role and current_user.role.name == "admin":
            permissions = db.query(RolePermissionModel).all()
            for permission in permissions:
                result[str(permission.role_id)] = permission.model_permissions.get(str(permission.role_id), {})
                logger.debug(f"Admin view - Role {permission.role_id} permissions: {result[str(permission.role_id)]}")
        else:
            permission = db.query(RolePermissionModel).filter(
                RolePermissionModel.role_id == current_user.role_id
            ).first()
            result[str(current_user.role_id)] = permission.model_permissions.get(str(current_user.role_id), {}) if permission else {}
            logger.debug(f"Non-admin view - Role {current_user.role_id} permissions: {result[str(current_user.role_id)]}")

        await log_activity(
            db=db,
            user=current_user,
            action="READ",
            resource_type="ModelPermission",
            resource_id=None,
            changes={"permissions_viewed": list(result.keys())},
            request=request
        )

        return {"permissions": result}
    except Exception as e:
        logger.error(f"Error in get_model_permissions: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/permissions/{role_id}/{model_name}", response_model=dict)
async def update_model_permission(
    role_id: int,
    model_name: str,
    permission_in: PermissionList,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update model permissions for a role."""
    try:
        # Check admin access
        if not current_user.role or current_user.role.name != "admin":
            raise HTTPException(status_code=403, detail="Only admins can update permissions")

        # Validate permission_list
        valid_permissions = {"create", "read", "update", "delete"}
        invalid_perms = set(permission_in.permission_list) - valid_permissions
        if invalid_perms:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid permissions: {invalid_perms}. Must be create, read, update, or delete"
            )

        # Validate model_name
        if not isinstance(model_name, str):
            raise HTTPException(status_code=400, detail="Model name must be a string")

        # Check if role exists
        role = db.query(Role).filter(Role.id == role_id).first()
        if not role:
            raise HTTPException(status_code=404, detail="Role not found")

        # Find or create permission entry
        permission = db.query(RolePermissionModel).filter(
            RolePermissionModel.role_id == role_id
        ).first()

        if not permission:
            permission = RolePermissionModel(
                role_id=role_id,
                model_permissions={str(role_id): {}},
                user_role_and_permission={}
            )
            db.add(permission)

        # Get current model_permissions
        model_perms = dict(permission.model_permissions)
        role_perms = model_perms.get(str(role_id), {})
        old_permissions = role_perms.get(model_name, [])
        logger.debug(f"Before update - Role {role_id}, Model {model_name}: {old_permissions}")

        # Update model_permissions
        role_perms[model_name] = permission_in.permission_list
        model_perms[str(role_id)] = role_perms
        permission.model_permissions = model_perms

        # Mark model_permissions as modified
        flag_modified(permission, "model_permissions")
        db.add(permission)
        db.commit()
        db.refresh(permission)

        logger.debug(f"After update - Role {role_id}, Model {model_name}: {permission.model_permissions[str(role_id)][model_name]}")

        # Log activity
        await log_activity(
            db=db,
            user=current_user,
            action="UPDATE",
            resource_type="ModelPermission",
            resource_id=role_id,
            changes={
                "model_name": model_name,
                "old_permissions": old_permissions,
                "new_permissions": permission_in.permission_list
            },
            request=request
        )

        return {
            "message": "Permissions updated successfully",
            "role_id": role_id,
            "model_name": model_name,
            "old_permissions": old_permissions,
            "new_permissions": permission_in.permission_list
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error in update_model_permission: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/permissions/{role_id}/{model_name}", response_model=dict)
async def delete_model_permission(
    role_id: int,
    model_name: str,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove model permissions for a role."""
    try:
        # Check admin access
        if not current_user.role or current_user.role.name != "admin":
            raise HTTPException(status_code=403, detail="Only admins can delete permissions")

        # Find permission record
        permission = db.query(RolePermissionModel).filter(
            RolePermissionModel.role_id == role_id
        ).first()

        if not permission:
            raise HTTPException(status_code=404, detail="Permission not found")

        # Get model_permissions
        model_perms = dict(permission.model_permissions)
        role_perms = model_perms.get(str(role_id), {})

        # Check if model_name exists
        if model_name not in role_perms:
            raise HTTPException(
                status_code=404,
                detail=f"No permissions found for model {model_name} on role {role_id}"
            )

        # Store old permissions for logging
        old_permissions = role_perms[model_name]
        logger.debug(f"Before delete - Role {role_id}, Model {model_name}: {old_permissions}")

        # Remove model_name permissions
        del role_perms[model_name]
        model_perms[str(role_id)] = role_perms
        permission.model_permissions = model_perms

        # Mark model_permissions as modified
        flag_modified(permission, "model_permissions")
        db.add(permission)
        db.commit()
        db.refresh(permission)

        logger.debug(f"After delete - Role {role_id} permissions: {permission.model_permissions.get(str(role_id), {})}")

        # Log activity
        await log_activity(
            db=db,
            user=current_user,
            action="DELETE",
            resource_type="ModelPermission",
            resource_id=role_id,
            changes={
                "model_name": model_name,
                "deleted_permissions": old_permissions
            },
            request=request
        )

        return {
            "message": "Permissions removed successfully",
            "role_id": role_id,
            "model_name": model_name,
            "deleted_permissions": old_permissions
        }
    except Exception as e:
        db.rollback()
        logger.error(f"Error in delete_model_permission: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))