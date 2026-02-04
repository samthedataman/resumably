"""
SQLAlchemy database models.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, JSON, Float
from sqlalchemy.orm import relationship

from app.database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=True)  # Nullable for Google OAuth users
    full_name = Column(String(255))

    # 2FA
    totp_secret = Column(String(32), nullable=True)
    is_2fa_enabled = Column(Boolean, default=False)

    # Gmail OAuth (for email access)
    gmail_token = Column(Text, nullable=True)  # JSON string of OAuth tokens
    gmail_connected = Column(Boolean, default=False)

    # Google OAuth Login
    google_id = Column(String(255), unique=True, nullable=True)  # Google's sub claim
    auth_provider = Column(String(20), default="email")  # "email" or "google"

    # Password Reset
    reset_token = Column(String(255), nullable=True)
    reset_token_expires = Column(DateTime, nullable=True)

    # Status
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    skills = relationship("Skill", back_populates="user", cascade="all, delete-orphan")
    resumes = relationship("Resume", back_populates="user", cascade="all, delete-orphan")
    email_drafts = relationship("EmailDraft", back_populates="user", cascade="all, delete-orphan")
    processed_emails = relationship("ProcessedEmail", back_populates="user", cascade="all, delete-orphan")
    skill_learnings = relationship("SkillLearning", back_populates="user", cascade="all, delete-orphan")


class Skill(Base):
    """Skills extracted from resume and learned from emails."""
    __tablename__ = "skills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String(100), nullable=False)
    category = Column(String(50))  # e.g., "data_engineering", "ai_ml", "leadership"
    proficiency = Column(String(20))  # "beginner", "intermediate", "advanced", "expert"
    years_experience = Column(Float)

    # Proof points - achievements that demonstrate this skill
    proof_points = Column(JSON, default=list)

    # Keywords that map to this skill
    keywords = Column(JSON, default=list)

    # Source of skill (resume, email_learning, manual, import, learned)
    source = Column(String(20), default="manual")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="skills")


class Resume(Base):
    """User's resume templates."""
    __tablename__ = "resumes"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String(100), default="Default Resume")
    is_default = Column(Boolean, default=False)

    # Resume data as JSON
    personal_info = Column(JSON, default=dict)
    summary = Column(Text)
    skills = Column(JSON, default=dict)  # {"category": ["skill1", "skill2"]}
    experience = Column(JSON, default=list)
    education = Column(JSON, default=list)
    projects = Column(JSON, default=list)
    certifications = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="resumes")


class ProcessedEmail(Base):
    """Emails that have been processed by the system."""
    __tablename__ = "processed_emails"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    gmail_id = Column(String(255), unique=True, index=True)
    thread_id = Column(String(255))
    subject = Column(String(500))
    sender = Column(String(255))  # Full sender string
    body = Column(Text)  # Store truncated body for context

    # Extracted job details
    is_recruiter_email = Column(Boolean, default=False)
    confidence = Column(Float, default=0.0)
    job_title = Column(String(255))
    company = Column(String(255))
    job_requirements = Column(JSON, default=list)
    technologies = Column(JSON, default=list)

    # Processing status
    processed_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="processed_emails")
    drafts = relationship("EmailDraft", back_populates="processed_email")


class EmailDraft(Base):
    """Generated email drafts with tailored resumes."""
    __tablename__ = "email_drafts"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    processed_email_id = Column(Integer, ForeignKey("processed_emails.id"), nullable=True)

    # Draft content
    subject = Column(String(500))
    body = Column(Text)

    # Tailored resume (JSON)
    tailored_resume = Column(JSON)

    # Skills matched for this job
    matched_skills = Column(JSON, default=list)

    # Status
    status = Column(String(20), default="draft")  # draft, sent, archived
    gmail_draft_id = Column(String(255))  # ID in Gmail drafts

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="email_drafts")
    processed_email = relationship("ProcessedEmail", back_populates="drafts")


class SkillLearning(Base):
    """Track skills learned from processed emails over time."""
    __tablename__ = "skill_learnings"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    skill_name = Column(String(100), nullable=False)
    category = Column(String(50))
    occurrence_count = Column(Integer, default=1)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Contexts where this skill appeared
    contexts = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="skill_learnings")
