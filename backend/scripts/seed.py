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
            title="Senior Backend Engineer",
            description="We're looking for an experienced backend engineer to join our team.",
            rubric_json={
                "experience": {"weight": 0.3, "max_score": 10},
                "technical_skills": {"weight": 0.5, "max_score": 10},
                "communication": {"weight": 0.2, "max_score": 10},
            },
            rubric_approved_by=admin.id,
        )
        session.add(job)
        session.commit()

        print("Creating demo candidates...")
        candidates = [
            Candidate(name="Alice Smith", email="alice@example.com"),
            Candidate(name="Bob Jones", email="bob@example.com"),
            Candidate(name="Carol White", email="carol@example.com"),
        ]
        for candidate in candidates:
            session.add(candidate)
        session.commit()

        print("Creating demo applications...")
        for i, candidate in enumerate(candidates):
            app = Application(
                job_id=job.id,
                candidate_id=candidate.id,
                cv_path=f"data/uploads/cv_{i}.pdf",
                status=ApplicationStatus.SCREENED,
                anonymized_profile_json={
                    "experience_years": 5 + i,
                    "education": "Bachelor's in Computer Science",
                    "skills": ["Python", "FastAPI", "SQL"],
                },
            )
            session.add(app)
        session.commit()

        print("\n✅ Database seeded successfully!")
        print(f"\nCredentials:")
        print(f"Admin:    {ADMIN_EMAIL} / {ADMIN_PASSWORD}")
        print(f"Recruiter: {RECRUITER_EMAIL} / {RECRUITER_PASSWORD}")


if __name__ == "__main__":
    seed()
