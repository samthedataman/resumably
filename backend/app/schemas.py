"""
Pydantic schemas for API request/response validation.
"""
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict, Any
from datetime import datetime


# Auth Schemas
class UserCreate(BaseModel):
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    email: EmailStr
    password: str
    totp_code: Optional[str] = None


class Token(BaseModel):
    access_token: str
    token_type: str
    requires_2fa: bool = False


class TokenData(BaseModel):
    user_id: Optional[int] = None


class TwoFactorSetup(BaseModel):
    secret: str
    qr_code: str
    uri: str


class TwoFactorVerify(BaseModel):
    code: str


class UserResponse(BaseModel):
    id: int
    email: str
    full_name: Optional[str] = None
    is_2fa_enabled: bool
    auth_provider: str = "email"
    gmail_connected: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


# Password Reset Schemas
class PasswordResetRequest(BaseModel):
    email: EmailStr


class PasswordResetConfirm(BaseModel):
    token: str
    new_password: str


# Google OAuth Schemas
class GoogleAuthRequest(BaseModel):
    credential: str  # Google ID token from frontend


class GoogleAuthResponse(BaseModel):
    access_token: str
    token_type: str
    is_new_user: bool = False


# Skill Schemas
class SkillBase(BaseModel):
    name: str
    category: str
    proficiency: str
    years_experience: Optional[float] = None
    proof_points: List[str] = []
    keywords: List[str] = []


class SkillCreate(SkillBase):
    pass


class SkillResponse(SkillBase):
    id: int
    user_id: int
    source: str
    created_at: datetime

    class Config:
        from_attributes = True


# Resume Schemas
class ResumeBase(BaseModel):
    name: str
    personal_info: Dict[str, Any]
    summary: str
    skills: Dict[str, List[str]]
    experience: List[Dict[str, Any]]
    education: List[Dict[str, Any]]
    projects: List[Dict[str, Any]] = []
    certifications: List[str] = []


class ResumeCreate(ResumeBase):
    pass


class ResumeUpdate(BaseModel):
    name: Optional[str] = None
    personal_info: Optional[Dict[str, Any]] = None
    summary: Optional[str] = None
    skills: Optional[Dict[str, List[str]]] = None
    experience: Optional[List[Dict[str, Any]]] = None
    education: Optional[List[Dict[str, Any]]] = None
    projects: Optional[List[Dict[str, Any]]] = None
    certifications: Optional[List[str]] = None


class ResumeResponse(ResumeBase):
    id: int
    user_id: int
    is_default: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Email Schemas
class EmailPreview(BaseModel):
    gmail_id: str
    subject: str
    sender: str
    snippet: str
    date: datetime


class ProcessedEmailResponse(BaseModel):
    id: int
    gmail_id: str
    subject: str
    sender: str
    job_title: Optional[str]
    company: Optional[str]
    job_requirements: List[str]
    technologies: List[str]
    is_recruiter_email: bool
    confidence: float
    processed_at: datetime

    class Config:
        from_attributes = True


# Draft Schemas
class DraftCreate(BaseModel):
    processed_email_id: int
    resume_id: Optional[int] = None


class DraftResponse(BaseModel):
    id: int
    user_id: int
    processed_email_id: int
    gmail_draft_id: Optional[str]
    subject: str
    body: str
    tailored_resume: Dict[str, Any]
    matched_skills: List[str]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


# Job Details (from email analysis)
class JobDetails(BaseModel):
    is_recruiter_email: bool
    confidence: float
    job_title: Optional[str] = None
    company: Optional[str] = None
    key_requirements: List[str] = []
    key_technologies: List[str] = []
    job_type: Optional[str] = None
    seniority_level: Optional[str] = None
    salary_range: Optional[str] = None
    recruiter_name: Optional[str] = None
    reason: str = ""


# Skill Learning Schemas
class SkillLearningResponse(BaseModel):
    id: int
    skill_name: str
    category: str
    occurrence_count: int
    last_seen: datetime
    contexts: List[str]

    class Config:
        from_attributes = True


# Dashboard Stats
class DashboardStats(BaseModel):
    total_emails_processed: int
    recruiter_emails_found: int
    drafts_created: int
    skills_learned: int
    top_requested_skills: List[Dict[str, Any]]
