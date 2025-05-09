from sqlalchemy.orm import Session
from app.models.permission import Role, Permission
from app.core.security import get_password_hash
from app.models.user import User

DEFAULT_PERMISSIONS = [
    ("view_users", "Can view user list"),
    ("create_users", "Can create users"),
    ("edit_users", "Can edit users"),
    ("delete_users", "Can delete users"),
    ("view_courses", "Can view course list"),
    ("create_courses", "Can create courses"),
    ("edit_courses", "Can edit courses"),
    ("delete_courses", "Can delete courses"),
    ("view_profiles", "Can view student profiles"),
    ("create_profiles", "Can create student profiles"),
    ("edit_profiles", "Can edit student profiles"),
    ("delete_profiles", "Can delete student profiles"),
    ("manage_roles", "Can manage roles and permissions"),
]

DEFAULT_ROLES = {
    "admin": {
        "description": "Administrator with full access",
        "permissions": [p[0] for p in DEFAULT_PERMISSIONS]
    },
    "staff": {
        "description": "Staff member with limited access",
        "permissions": [
            "view_users",
            "view_courses",
            "create_courses",
            "edit_courses",
            "view_profiles",
        ]
    },
    "user": {
        "description": "Regular user",
        "permissions": [
            "view_courses",
            "create_profiles",
            "edit_profiles",
        ]
    }
}

def init_rbac(db: Session) -> None:
    # Create permissions
    permissions = {}
    for perm_name, perm_desc in DEFAULT_PERMISSIONS:
        permission = Permission(name=perm_name, description=perm_desc)
        db.add(permission)
        permissions[perm_name] = permission
    
    # Create roles
    roles = {}
    for role_name, role_data in DEFAULT_ROLES.items():
        role = Role(
            name=role_name,
            description=role_data["description"],
            permissions=[
                permissions[perm_name]
                for perm_name in role_data["permissions"]
            ]
        )
        db.add(role)
        roles[role_name] = role
    
    db.commit()

    # Create default admin user if it doesn't exist
    admin_email = "admin@example.com"
    if not db.query(User).filter(User.email == admin_email).first():
        admin_user = User(
            email=admin_email,
            username="admin",
            hashed_password=get_password_hash("admin123"),
            first_name="Admin",
            last_name="User",
            role_obj=roles["admin"],
            is_verified=True,
            is_active=True
        )
        db.add(admin_user)
        db.commit()
