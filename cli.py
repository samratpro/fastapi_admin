import click
from app.db.base import Base, SessionLocal, engine
from app.models.user import User, Role
from app.core.security import get_password_hash
from sqlalchemy.exc import OperationalError

@click.group()
def cli():
    pass

def initialize_database():
    """Initialize the database by creating all tables if they don't exist and seed initial roles."""
    try:
        click.echo("Checking if the database is initialized...")
        Base.metadata.create_all(bind=engine)
        click.echo("Database initialized successfully!")

        # Seed initial roles
        db = SessionLocal()
        roles = ["user", "admin", "staff"]
        for role_name in roles:
            role = db.query(Role).filter(Role.name == role_name).first()
            if not role:
                new_role = Role(name=role_name)
                db.add(new_role)
                db.commit()
                click.echo(f"Role '{role_name}' created successfully!")
        db.close()

    except Exception as e:
        click.echo(f"Error initializing database: {e}")

def ensure_admin_role_exists(db):
    """Ensure that the 'admin' role exists in the roles table."""
    role = db.query(Role).filter(Role.name == "admin").first()
    if not role:
        click.echo("Creating 'admin' role...")
        role = Role(name="admin")
        db.add(role)
        db.commit()
        click.echo("'admin' role created successfully!")

@cli.command()
@click.option("--email", prompt=True)
@click.option("--username", prompt=True)
@click.option("--password", prompt=True, hide_input=True, confirmation_prompt=True)
def create_admin(email, username, password):
    """Create a new admin user"""
    # Ensure the database is initialized
    initialize_database()

    db = SessionLocal()
    
    try:
        # Ensure the 'admin' role exists
        ensure_admin_role_exists(db)

        # Fetch the 'admin' role from the database
        role = db.query(Role).filter(Role.name == "admin").first()

        # Create the admin user
        user = User(
            email=email,
            username=username,
            hashed_password=get_password_hash(password),
            role_id=role.id,  # Use role_id instead of role
            is_verified=True,
            is_active=True
        )
        db.add(user)
        db.commit()
        click.echo(f"Admin user {email} created successfully!")
    except OperationalError as e:
        db.rollback()
        click.echo(f"Database schema error: {e}")
        click.echo("Please ensure your database schema is up-to-date.")
    except Exception as e:
        db.rollback()
        click.echo(f"Error creating admin user: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    cli()