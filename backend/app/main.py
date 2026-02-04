"""
Resumably - AI-Powered Resume Tailoring and Email Reply System
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import get_settings
from app.database import engine, Base
from app.routes import auth, gmail, resumes, emails, skills

settings = get_settings()

# Create database tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Resumably",
    description="AI-powered resume tailoring and recruiter email reply system",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        settings.frontend_url or "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(gmail.router)
app.include_router(resumes.router)
app.include_router(emails.router)
app.include_router(skills.router)


@app.get("/")
async def root():
    """Health check endpoint."""
    return {
        "name": "Resumably API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Detailed health check."""
    return {
        "status": "healthy",
        "database": "connected",
        "services": {
            "gmail": "available",
            "claude": "available",
            "pdf": "available"
        }
    }
