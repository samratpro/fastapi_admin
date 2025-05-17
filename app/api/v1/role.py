from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.db.base import get_db
from app.models.user import User
from app.models.role import Role as RoleModel
from app.models.public_role import PublicRole
from app.models.admin_access_role import AdminAccessRole
from app.schemas.permission import (
    RoleCreate,
    Role,
    RoleUpdate,
    PublicRoleSchema,
    AdminAccessRoleSchema
)
from app.core.security import get_current_active_user
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()

@router.post("/roles", response_model=Role)  # Fixed: Use Role, not RoleCreate
async def create_role(
    *,
    db: Session = Depends(get_db),
    role_in: RoleCreate,
    current_user: User = Depends(get_current_active_user),
):
    """
    Create a new role (admin only).
    """
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admin users can create roles."
        )
    
    role_name = role_in.name.strip().lower()
    existing_role = db.query(RoleModel).filter(RoleModel.name == role_name).first()
    if existing_role:
        raise HTTPException(
            status_code=400,
            detail=f"Role '{role_name}' already exists."
        )
    
    # Create the role with name and description
    new_role = RoleModel(name=role_name, description=role_in.description)
    db.add(new_role)
    db.commit()
    db.refresh(new_role)
    return new_role

@router.get("/roles", response_model=List[Role])  # Fixed: Use Role, not RoleSchema
async def list_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """List all roles (admin only)."""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    
    return db.query(RoleModel).all()

@router.put("/roles/{role_id}", response_model=Role)  # Fixed: Use Role, not RoleSchema
async def update_role(
    role_id: int,
    role_in: RoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Update a role (admin only)."""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.name == "admin" and role_in.name and role_in.name != "admin":
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
    """Delete a role (admin only)."""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.name == "admin":
        raise HTTPException(status_code=400, detail="Cannot delete admin role")

    if db.query(User).filter(User.role_id == role_id).first():
        raise HTTPException(
            status_code=400,
            detail="Cannot delete role that is assigned to users"
        )

    db.delete(role)
    db.commit()
    return {"message": "Role deleted successfully"}



# Public Role Management
@router.get("/public-roles", response_model=PublicRoleSchema)
async def get_public_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get the public roles list (admin only)"""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        public_role = db.query(PublicRole).first()
        if not public_role:
            public_role = PublicRole(role_ids=[])
            db.add(public_role)
            db.commit()
            db.refresh(public_role)
            logger.info("Created empty PublicRole for GET request")
        return public_role
    except Exception as e:
        logger.error(f"Error retrieving public roles: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving public roles."
        )
@router.post("/public-roles/{role_id}", response_model=PublicRoleSchema)
async def add_public_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Add a role to public roles (admin only)."""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admin users can manage public roles"
        )

    # Verify role exists
    role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.name == "admin":
        raise HTTPException(
            status_code=400,
            detail="Cannot add admin role to public roles"
        )

    try:
        public_role = db.query(PublicRole).first()
        if not public_role:
            # If no public roles exist, create new with single role_id
            public_role = PublicRole(role_ids=[role_id])
            db.add(public_role)
            logger.info(f"Created new public roles list with role_id: {role_id}")
        else:
            # Get existing role_ids
            existing_roles = public_role.role_ids or []
            
            if role_id in existing_roles:
                raise HTTPException(
                    status_code=400,
                    detail="Role is already public"
                )
            
            # Create new list with existing roles plus new role
            updated_roles = existing_roles.copy()
            updated_roles.append(role_id)
            
            # Update with new list
            public_role.role_ids = updated_roles
            logger.info(f"Added role_id {role_id} to existing roles: {existing_roles}")

        db.commit()
        db.refresh(public_role)
        return public_role

    except Exception as e:
        db.rollback()
        logger.error(f"Error adding public role: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error adding public role: {str(e)}")

@router.delete("/public-roles/{role_id}", response_model=PublicRoleSchema)
async def remove_public_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove a role from public roles (admin only)."""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        public_role = db.query(PublicRole).first()
        if not public_role:
            raise HTTPException(
                status_code=404, 
                detail="No public roles configuration exists"
            )

        existing_roles = public_role.role_ids or []
        if not existing_roles:
            raise HTTPException(
                status_code=404, 
                detail="Public roles list is empty"
            )

        if role_id not in existing_roles:
            raise HTTPException(
                status_code=404, 
                detail="Role is not in public roles list"
            )

        # Create new list without the role_id to remove
        updated_roles = [r for r in existing_roles if r != role_id]
        
        # Update with new list
        public_role.role_ids = updated_roles
        logger.info(f"Removed role_id {role_id} from public roles. New list: {updated_roles}")

        db.commit()
        db.refresh(public_role)
        return public_role

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error removing public role: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error removing public role: {str(e)}"
        )

# Admin Access Role Management
@router.get("/admin-access-roles", response_model=AdminAccessRoleSchema)
async def get_admin_access_roles(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Get the admin access roles list (admin only)"""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        admin_access_role = db.query(AdminAccessRole).first()
        if not admin_access_role:
            admin_access_role = AdminAccessRole(role_ids=[])
            db.add(admin_access_role)
            db.commit()
            db.refresh(admin_access_role)
            logger.info("Created empty AdminAccessRole for GET request")
        return admin_access_role
    except Exception as e:
        logger.error(f"Error retrieving admin access roles: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail="Internal server error while retrieving admin access roles."
        )
@router.post("/admin-access-roles/{role_id}", response_model=AdminAccessRoleSchema)
async def add_admin_access_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user),
):
    """Add a role to admin access roles (admin only)."""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(
            status_code=403,
            detail="Only admin users can manage admin access roles"
        )

    # Verify role exists
    role = db.query(RoleModel).filter(RoleModel.id == role_id).first()
    if not role:
        raise HTTPException(status_code=404, detail="Role not found")

    if role.name == "admin":
        raise HTTPException(
            status_code=400,
            detail="Cannot add admin role to admin access roles"
        )

    try:
        admin_access_role = db.query(AdminAccessRole).first()
        if not admin_access_role:
            # If no admin access roles exist, create new with single role_id
            admin_access_role = AdminAccessRole(role_ids=[role_id])
            db.add(admin_access_role)
            logger.info(f"Created new admin access roles list with role_id: {role_id}")
        else:
            # Get existing role_ids
            existing_roles = admin_access_role.role_ids or []
            
            if role_id in existing_roles:
                raise HTTPException(
                    status_code=400,
                    detail="Role already has admin access"
                )
            
            # Create new list with existing roles plus new role
            updated_roles = existing_roles.copy()
            updated_roles.append(role_id)
            
            # Update with new list
            admin_access_role.role_ids = updated_roles
            logger.info(f"Added role_id {role_id} to existing admin access roles: {existing_roles}")

        db.commit()
        db.refresh(admin_access_role)
        return admin_access_role

    except Exception as e:
        db.rollback()
        logger.error(f"Error adding admin access role: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error adding admin access role: {str(e)}")

@router.delete("/admin-access-roles/{role_id}", response_model=AdminAccessRoleSchema)
async def remove_admin_access_role(
    role_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """Remove a role from admin access roles (admin only)."""
    if not current_user.role or current_user.role.name != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        admin_access_role = db.query(AdminAccessRole).first()
        if not admin_access_role:
            raise HTTPException(
                status_code=404, 
                detail="No admin access roles configuration exists"
            )

        existing_roles = admin_access_role.role_ids or []
        if not existing_roles:
            raise HTTPException(
                status_code=404, 
                detail="Admin access roles list is empty"
            )

        if role_id not in existing_roles:
            raise HTTPException(
                status_code=404, 
                detail="Role does not have admin access"
            )

        # Create new list without the role_id to remove
        updated_roles = [r for r in existing_roles if r != role_id]
        
        # Update with new list
        admin_access_role.role_ids = updated_roles
        logger.info(f"Removed role_id {role_id} from admin access roles. New list: {updated_roles}")

        db.commit()
        db.refresh(admin_access_role)
        return admin_access_role

    except HTTPException:
        raise
    except Exception as e:
        db.rollback()
        logger.error(f"Error removing admin access role: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error removing admin access role: {str(e)}"
        )