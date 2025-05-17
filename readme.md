# FastAPI Application Setup and Management

This project is a FastAPI-based application with user role management, database integration, and Docker support. Below are instructions for setting up, running, and extending the application, including user management, model creation, and database migrations.

## Prerequisites
- Python 3.8+
- Docker and Docker Compose
- Virtualenv (optional, for local development)
- pip for Python package management

## Setup Instructions

### 1. Activate Virtual Environment
To isolate dependencies, activate the virtual environment:
```bash
source venv/scripts/activate
```

### 2. Run the Application with Docker
Build and start the application using Docker Compose:
```bash
docker-compose up -d --build
```

### 3. Create a User
Users can be created with specific roles (admin, editor, user) using the CLI. Run the following command:
```bash
python cli.py create-user
```
Or, if running inside the Docker container:
```bash
docker exec -it fastapi_app python cli.py create-user
```
Follow the prompts to select a role, provide an email, username, and password:
```
1: admin
2: editor
3: user
Select Role (1, 2, 3): 2
Email: editor@editor.com
Username: editor
Password: [Enter password]
Confirm Password: [Confirm password]
```

## Adding a New Model
To extend the application with a new model, follow these steps:

1. **Create Model**: Define the model in `app/db/base.py` and import it.
2. **Create Schema**: Add a Pydantic schema for the model in the appropriate schema file.
3. **Create Router**: Add a new router in the `app/api` section, following the `course.py` example. Use `has_permission` for access control (exclude `student_profile` if not needed).
4. **Import Model**: Ensure the model is imported in `app/db/base.py` and `app/models/__init__.py`.
5. **Register Model**: Add the model to `AdminModelRegister` in `app/main.py` for admin interface integration.
6. **Dynamic Router Handling**: The router will be dynamically handled via metadata. To include the router directly, add it to the router section in `app/main.py`.

## Database Migrations
The application uses Alembic for database migrations. Follow these steps to set up and manage migrations:

### 1. Install Alembic
```bash
pip install alembic
```

### 2. Initialize Alembic
Create the Alembic configuration:
```bash
alembic init alembic
```

### 3. Generate a Migration
Ensure `app/db/base.py` is imported, then create a new migration:
```bash
alembic revision --autogenerate -m "Describe change"
```

### 4. Apply Migrations
Run the migrations to update the database:
```bash
alembic upgrade head
```

### 5. Undo Last Migration
To revert the last migration:
```bash
alembic downgrade -1
```

## Project Structure
- `app/db/base.py`: Database models and base configuration.
- `app/api/`: API routers, including permission-based access control.
- `app/models/`: Model definitions.
- `app/main.py`: Application entry point and admin model registration.
- `cli.py`: CLI for user management.
- `alembic/`: Migration scripts and configuration.

## Notes
- Ensure environment variables (e.g., database credentials) are configured in `.env` or Docker Compose.
- The `has_permission` function in routers enforces role-based access control.
- Dynamic router metadata reduces boilerplate for new endpoints.
- Always test migrations in a development environment before applying to production.

## Contributing
1. Fork the repository.
2. Create a feature branch (`git checkout -b feature/your-feature`).
3. Commit changes (`git commit -m "Add your feature"`).
4. Push to the branch (`git push origin feature/your-feature`).
5. Open a pull request.

## License
This project is licensed under the MIT License.