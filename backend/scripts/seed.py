#!/usr/bin/env python
"""Seed database with demo data."""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlmodel import Session, select
from app.db import engine, init_db
from app.models import User, Job, Candidate, Application, ApplicationStatus, UserRole
from app.auth import hash_password
from app.services.rubric import JUNIOR_BACKEND_RUBRIC

ADMIN_EMAIL = "admin@fictional-company.test"
ADMIN_PASSWORD = "admin123"
RECRUITER_EMAIL = "recruiter@fictional-company.test"
RECRUITER_PASSWORD = "recruiter123"


def seed():
    """Seed database."""
    print("Initializing database...")
    init_db()

    with Session(engine) as session:
        # Check if already seeded
        existing_user = session.exec(select(User)).first()
        if existing_user:
            print("Database already seeded. Skipping.")
            return

        print("Creating users...")
        admin = User(
            email=ADMIN_EMAIL,
            password_hash=hash_password(ADMIN_PASSWORD),
            role=UserRole.ADMIN,
        )
        recruiter = User(
            email=RECRUITER_EMAIL,
            password_hash=hash_password(RECRUITER_PASSWORD),
            role=UserRole.RECRUITER,
        )
        session.add(admin)
        session.add(recruiter)
        session.commit()

        print("Creating demo job...")
        job = Job(
            title="Junior Backend Developer (Python)",
            description=(
                "We are looking for a junior backend developer to build and maintain REST APIs.\n"
                "Must have: Python and at least one web framework (FastAPI, Django or Flask).\n"
                "Nice to have: SQL databases, Git, Docker, automated testing.\n"
                "Experience: 0-2 years; internships and personal projects count.\n"
                "Education: computer science degree or equivalent practical experience."
            ),
            rubric_json=JUNIOR_BACKEND_RUBRIC,
            rubric_approved_by=admin.id,
        )
        session.add(job)
        session.commit()
        print("(Candidates arrive by email: open the app and click 'Load demo emails'.)")

        print("\n✅ Database seeded successfully!")
        print(f"\nCredentials:")
        print(f"Admin:    {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        print(f"Recruiter: {RECRUITER_EMAIL} / {RECRUITER_PASSWORD}")


if __name__ == "__main__":
    seed()
