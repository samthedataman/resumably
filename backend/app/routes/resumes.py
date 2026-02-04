"""
Resume management routes.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Resume
from app.schemas import ResumeCreate, ResumeUpdate, ResumeResponse
from app.auth import get_current_user
from app.services.pdf_service import PDFService

router = APIRouter(prefix="/api/resumes", tags=["resumes"])
pdf_service = PDFService()


@router.get("/", response_model=List[ResumeResponse])
async def list_resumes(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all resumes for current user."""
    resumes = db.query(Resume).filter(Resume.user_id == current_user.id).all()
    return resumes


@router.post("/", response_model=ResumeResponse)
async def create_resume(
    resume_data: ResumeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new resume."""
    # Check if first resume - make it default
    existing = db.query(Resume).filter(Resume.user_id == current_user.id).count()
    is_default = existing == 0

    resume = Resume(
        user_id=current_user.id,
        name=resume_data.name,
        personal_info=resume_data.personal_info,
        summary=resume_data.summary,
        skills=resume_data.skills,
        experience=resume_data.experience,
        education=resume_data.education,
        projects=resume_data.projects,
        certifications=resume_data.certifications,
        is_default=is_default
    )
    db.add(resume)
    db.commit()
    db.refresh(resume)

    return resume


@router.get("/default", response_model=ResumeResponse)
async def get_default_resume(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the default resume."""
    resume = db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_default == True
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No default resume found"
        )

    return resume


@router.get("/{resume_id}", response_model=ResumeResponse)
async def get_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific resume."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )

    return resume


@router.put("/{resume_id}", response_model=ResumeResponse)
async def update_resume(
    resume_id: int,
    resume_data: ResumeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a resume."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )

    # Update fields
    update_data = resume_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(resume, field, value)

    db.commit()
    db.refresh(resume)

    return resume


@router.delete("/{resume_id}")
async def delete_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a resume."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )

    db.delete(resume)
    db.commit()

    return {"message": "Resume deleted"}


@router.post("/{resume_id}/set-default")
async def set_default_resume(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Set a resume as the default."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )

    # Unset current default
    db.query(Resume).filter(
        Resume.user_id == current_user.id,
        Resume.is_default == True
    ).update({"is_default": False})

    # Set new default
    resume.is_default = True
    db.commit()

    return {"message": "Default resume updated"}


@router.get("/{resume_id}/pdf")
async def download_resume_pdf(
    resume_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Download resume as PDF."""
    resume = db.query(Resume).filter(
        Resume.id == resume_id,
        Resume.user_id == current_user.id
    ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Resume not found"
        )

    # Build resume data dict
    resume_data = {
        'personal': resume.personal_info,
        'summary': resume.summary,
        'skills': resume.skills,
        'experience': resume.experience,
        'education': resume.education,
        'projects': resume.projects,
        'certifications': resume.certifications
    }

    # Generate PDF
    pdf_bytes = pdf_service.generate_resume_pdf(resume_data)

    # Get name for filename
    name = resume.personal_info.get('name', 'resume').replace(' ', '_')
    filename = f"{name}_Resume.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )
