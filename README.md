# Customer Feedback and Complaint Management System

## Project Overview

A REST API built with FastAPI to manage customers, feedback, complaints, categories, complaint assignments, status workflows, service-level agreements (SLAs), notifications, analytics, reports, and audit logs.

## Technology Stack

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- SQLite for local development
- JWT authentication
- Password hashing
- Alembic database migrations
- Pytest for automated testing

## Features

- User registration, login, token refresh, and logout
- Password reset request and confirmation
- Role-based access control and account status management
- Customer profiles and customer management
- Feedback submission and feedback status management
- Category management
- Complaint creation, assignment, and status updates
- Complaint comments and status history
- SLA monitoring and overdue complaint tracking
- Notifications and unread notification counts
- Satisfaction analytics and ratings
- Reports and dashboard summaries
- Audit logs

## Requirements

- Python 3.11 or newer
- pip
- PowerShell on Windows

## Installation

Open PowerShell in the project directory.

Create and activate a virtual environment if you do not already have one:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

Install the dependencies:

```powershell
python -m pip install -r requirements.txt
```

## Environment Configuration

The project uses environment variables for configuration.

Copy the example configuration to create a local environment file:

```powershell
Copy-Item .env.example .env
```

Set a strong, private `SECRET_KEY` in `.env` before using the application beyond local development. Do not commit `.env` or expose authentication tokens.

The default local database configuration uses SQLite.

## Database Migrations

Apply the database migrations:

```powershell
alembic upgrade head
```

Check the current migration:

```powershell
alembic current
```

## Run the Application

Start the FastAPI development server:

```powershell
python -m uvicorn app.main:app --reload
```

The local application is available at:

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- Health check: http://127.0.0.1:8000/health

## Run Automated Tests

Run the test suite:

```powershell
pytest -q
```

Tests should be run before submitting changes. Review any failures and warnings.

## API Documentation

FastAPI generates interactive API documentation at `/docs` and an OpenAPI schema at `/openapi.json`.

## Postman

The `postman` directory is reserved for the API request collection. Import the collection into Postman after the collection file has been created.

## Project Structure

```text
customer-feedback-system/
├── alembic/
│   └── versions/
├── app/
│   ├── core/
│   ├── models/
│   ├── routes/
│   ├── schemas/
│   └── main.py
├── docs/
├── postman/
├── scripts/
├── tests/
├── .env.example
├── .gitignore
├── alembic.ini
├── README.md
└── requirements.txt
```

## Current Verification

The latest reported automated test run completed with 73 passed tests and 1 deprecation warning. Run `pytest -q` again to verify the current code before submission.

## Security Notes

- Keep `.env` private.
- Use a strong secret key.
- Do not commit local database files or database backups.
- Do not expose password reset tokens or authentication tokens.
- Use production-grade configuration before deployment.

## Project Status

The project includes API routes, database models, migrations, and automated tests. Verify all required assignment scenarios, authorization rules, API documentation, and Postman requests before final submission.
