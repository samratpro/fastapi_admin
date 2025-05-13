import click
import re
from app.db.base import Base, SessionLocal, engine
from app.models.user import User
from app.models.role import Role
from app.models.public_role import PublicRole
from app.models.admin_access_role import AdminAccessRole
from app.core.security import get_password_hash
from sqlalchemy.exc import OperationalError

@click.group()
def cli():
    pass

def initialize_database():
    """Initialize the database by creating all tables and seeding initial roles."""
    try:
        # click.echo("Checking if the database is initialized...")
        Base.metadata.create_all(bind=engine)
        # click.echo("Database initialized successfully!")

        # Seed initial roles
        db = SessionLocal()
        roles = [
            {"name": "admin", "id": None},
            {"name": "editor", "id": None},
            {"name": "user", "id": None}
        ]

        # Create or verify roles
        for role_data in roles:
            role = db.query(Role).filter(Role.name == role_data["name"]).first()
            if not role:
                role = Role(name=role_data["name"])
                db.add(role)
                db.commit()
                # click.echo(f"Role '{role_data['name']}' created successfully!")
            role_data["id"] = role.id

        # Seed PublicRole (user role_id)
        user_role_id = next(r["id"] for r in roles if r["name"] == "user")
        public_role = db.query(PublicRole).first()
        if not public_role:
            public_role = PublicRole(role_ids=[user_role_id])
            db.add(public_role)
        elif user_role_id not in public_role.role_ids:
            public_role.role_ids.append(user_role_id)
        else:
            pass

        # Seed AdminAccessRole (editor role_id)
        editor_role_id = next(r["id"] for r in roles if r["name"] == "editor")
        admin_role = db.query(AdminAccessRole).first()
        if not admin_role:
            admin_role = AdminAccessRole(role_ids=[editor_role_id])
            db.add(admin_role)
        elif editor_role_id not in admin_role.role_ids:
            admin_role.role_ids.append(editor_role_id)
        else:
            pass

        db.commit()
    except OperationalError as e:
        click.echo(f"Database error: {e}")
    except Exception as e:
        click.echo(f"Error initializing database: {e}")
    finally:
        db.close()

@cli.command()
def create_user():
    """Create a new user with the selected role (no verification required)."""
    # Initialize database
    initialize_database()

    # Prompt for role first
    role = click.prompt("\n1: admin\n2: editor\n3: user\n\nSelect Role ", type=click.Choice(["1", "2", "3"]))

    # Map role choice to role name
    role_map = {
        "1": "admin",
        "2": "editor",
        "3": "user"
    }
    role_name = role_map[role]

    # Validate email with instant re-prompt
    email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    while True:
        email = click.prompt("Email")
        if re.match(email_pattern, email):
            break
        click.echo("Invalid email format. Provide a valid format!")

    # Prompt for username
    username = click.prompt("Username")

    # Validate password with instant re-prompt
    while True:
        password = click.prompt("Password", hide_input=True)
        confirm_password = click.prompt("Confirm Password", hide_input=True)
        if password == confirm_password:
            break
        click.echo("Passwords didn't match. Enter again!")

    db = SessionLocal()
    try:
        # Fetch the selected role
        db_role = db.query(Role).filter(Role.name == role_name).first()
        if not db_role:
            click.echo(f"Error: Role '{role_name}' does not exist!")
            return

        # Check if user already exists
        if db.query(User).filter(User.email == email).first():
            click.echo(f"Error: User with email {email} already exists!")
            return

        # Create the user
        user = User(
            email=email,
            username=username,
            hashed_password=get_password_hash(password),
            role_id=db_role.id,
            is_verified=True,  # All users are verified
            is_active=True
        )
        db.add(user)
        db.commit()
        click.echo(f"User {email} created successfully with role '{role_name}'!")
    except OperationalError as e:
        db.rollback()
        click.echo(f"Database schema error: {e}")
        click.echo("Please ensure your database schema is up-to-date.")
    except Exception as e:
        db.rollback()
        click.echo(f"Error creating user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    cli()