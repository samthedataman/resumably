"""
Email processing routes - scan, classify, create drafts.
"""
import json
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Resume, ProcessedEmail, EmailDraft, SkillLearning
from app.schemas import (
    EmailPreview, ProcessedEmailResponse, DraftCreate, DraftResponse,
    JobDetails, DashboardStats
)
from app.auth import get_current_user
from app.services.gmail_service import GmailService
from app.services.claude_service import ClaudeService
from app.services.pdf_service import PDFService

router = APIRouter(prefix="/api/emails", tags=["emails"])
claude_service = ClaudeService()
pdf_service = PDFService()


def get_gmail_service(user: User) -> GmailService:
    """Get Gmail service for user."""
    if not user.gmail_connected or not user.gmail_token:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Gmail not connected"
        )
    token_data = json.loads(user.gmail_token)
    return GmailService(token_data)


@router.get("/scan")
async def scan_emails(
    max_results: int = 20,
    query: str = "is:unread category:primary",
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Scan Gmail for unread emails."""
    gmail = get_gmail_service(current_user)
    result = gmail.list_emails(max_results=max_results, query=query)

    emails = []
    for msg in result.get('messages', []):
        email_data = gmail.get_email(msg['id'])
        emails.append({
            'gmail_id': email_data['id'],
            'subject': email_data['subject'],
            'sender': email_data['from'],
            'snippet': email_data['snippet'],
            'date': email_data['date'].isoformat()
        })

    return {
        'emails': emails,
        'next_page_token': result.get('next_page_token')
    }


@router.post("/classify/{gmail_id}")
async def classify_email(
    gmail_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Classify a single email using Claude Haiku."""
    gmail = get_gmail_service(current_user)
    email_data = gmail.get_email(gmail_id)

    # Classify with Claude
    job_details = claude_service.classify_email(email_data)

    # Store processed email
    processed = ProcessedEmail(
        user_id=current_user.id,
        gmail_id=gmail_id,
        subject=email_data['subject'],
        sender=email_data['from'],
        body=email_data['body'][:5000],  # Truncate for storage
        job_title=job_details.job_title,
        company=job_details.company,
        job_requirements=job_details.key_requirements,
        technologies=job_details.key_technologies,
        is_recruiter_email=job_details.is_recruiter_email,
        confidence=job_details.confidence
    )
    db.add(processed)
    db.commit()
    db.refresh(processed)

    # Learn skills from email if it's a recruiter email
    if job_details.is_recruiter_email:
        await learn_skills_from_email(email_data, current_user.id, db)

    return {
        'processed_email_id': processed.id,
        'job_details': job_details.model_dump()
    }


@router.post("/batch-classify")
async def batch_classify_emails(
    gmail_ids: List[str],
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Classify multiple emails in background."""
    # Queue background processing
    background_tasks.add_task(
        process_emails_batch,
        gmail_ids,
        current_user.id,
        db
    )

    return {"message": f"Processing {len(gmail_ids)} emails in background"}


async def process_emails_batch(gmail_ids: List[str], user_id: int, db: Session):
    """Background task to process multiple emails."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user or not user.gmail_connected:
        return

    gmail = get_gmail_service(user)

    for gmail_id in gmail_ids:
        try:
            # Check if already processed
            existing = db.query(ProcessedEmail).filter(
                ProcessedEmail.gmail_id == gmail_id,
                ProcessedEmail.user_id == user_id
            ).first()
            if existing:
                continue

            email_data = gmail.get_email(gmail_id)
            job_details = claude_service.classify_email(email_data)

            processed = ProcessedEmail(
                user_id=user_id,
                gmail_id=gmail_id,
                subject=email_data['subject'],
                sender=email_data['from'],
                body=email_data['body'][:5000],
                job_title=job_details.job_title,
                company=job_details.company,
                job_requirements=job_details.key_requirements,
                technologies=job_details.key_technologies,
                is_recruiter_email=job_details.is_recruiter_email,
                confidence=job_details.confidence
            )
            db.add(processed)
            db.commit()

            if job_details.is_recruiter_email:
                await learn_skills_from_email(email_data, user_id, db)

        except Exception as e:
            print(f"Error processing email {gmail_id}: {e}")
            continue


async def learn_skills_from_email(email_data: dict, user_id: int, db: Session):
    """Extract and learn skills from an email."""
    skills = claude_service.extract_skills_from_email(email_data)

    for skill in skills:
        # Check if skill already tracked
        existing = db.query(SkillLearning).filter(
            SkillLearning.user_id == user_id,
            SkillLearning.skill_name == skill['name'].lower()
        ).first()

        if existing:
            existing.occurrence_count += 1
            existing.contexts = existing.contexts + [skill.get('context', '')]
        else:
            learning = SkillLearning(
                user_id=user_id,
                skill_name=skill['name'].lower(),
                category=skill.get('category', 'other'),
                occurrence_count=1,
                contexts=[skill.get('context', '')]
            )
            db.add(learning)

    db.commit()


@router.get("/processed", response_model=List[ProcessedEmailResponse])
async def list_processed_emails(
    recruiter_only: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List processed emails."""
    query = db.query(ProcessedEmail).filter(
        ProcessedEmail.user_id == current_user.id
    )

    if recruiter_only:
        query = query.filter(ProcessedEmail.is_recruiter_email == True)

    emails = query.order_by(ProcessedEmail.processed_at.desc()).limit(limit).all()
    return emails


@router.get("/processed/{email_id}", response_model=ProcessedEmailResponse)
async def get_processed_email(
    email_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific processed email."""
    email = db.query(ProcessedEmail).filter(
        ProcessedEmail.id == email_id,
        ProcessedEmail.user_id == current_user.id
    ).first()

    if not email:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processed email not found"
        )

    return email


@router.post("/draft")
async def create_draft(
    draft_data: DraftCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a reply draft with tailored resume."""
    # Get processed email
    processed = db.query(ProcessedEmail).filter(
        ProcessedEmail.id == draft_data.processed_email_id,
        ProcessedEmail.user_id == current_user.id
    ).first()

    if not processed:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Processed email not found"
        )

    # Get resume
    if draft_data.resume_id:
        resume = db.query(Resume).filter(
            Resume.id == draft_data.resume_id,
            Resume.user_id == current_user.id
        ).first()
    else:
        resume = db.query(Resume).filter(
            Resume.user_id == current_user.id,
            Resume.is_default == True
        ).first()

    if not resume:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No resume found. Please create one first."
        )

    # Build base resume dict
    base_resume = {
        'personal': resume.personal_info,
        'summary': resume.summary,
        'skills': resume.skills,
        'experience': resume.experience,
        'education': resume.education,
        'projects': resume.projects,
        'certifications': resume.certifications
    }

    # Build job details
    job_details = JobDetails(
        is_recruiter_email=processed.is_recruiter_email,
        confidence=processed.confidence,
        job_title=processed.job_title,
        company=processed.company,
        key_requirements=processed.job_requirements,
        key_technologies=processed.technologies
    )

    # Tailor resume with Claude Sonnet
    tailored_resume = claude_service.tailor_resume(base_resume, job_details)

    # Generate reply email
    email_data = {
        'from': processed.sender,
        'subject': processed.subject,
        'body': processed.body
    }
    candidate_info = resume.personal_info
    reply_text = claude_service.generate_reply_email(
        email_data,
        job_details,
        candidate_info,
        list(job_details.key_technologies)
    )

    # Generate PDF
    pdf_bytes = pdf_service.generate_resume_pdf(tailored_resume)

    # Create Gmail draft
    gmail = get_gmail_service(current_user)

    # Extract email address from sender
    sender_email = processed.sender
    if '<' in sender_email:
        sender_email = sender_email.split('<')[1].split('>')[0]

    draft_result = gmail.create_draft(
        to=sender_email,
        subject=f"Re: {processed.subject}",
        body=reply_text,
        pdf_attachment=pdf_bytes,
        attachment_name=f"{resume.personal_info.get('name', 'Resume').replace(' ', '_')}_Resume.pdf"
    )

    # Store draft in database
    draft = EmailDraft(
        user_id=current_user.id,
        processed_email_id=processed.id,
        gmail_draft_id=draft_result.get('id'),
        subject=f"Re: {processed.subject}",
        body=reply_text,
        tailored_resume=tailored_resume,
        matched_skills=list(job_details.key_technologies),
        status='draft'
    )
    db.add(draft)
    db.commit()
    db.refresh(draft)

    return {
        'draft_id': draft.id,
        'gmail_draft_id': draft_result.get('id'),
        'reply_text': reply_text,
        'matched_skills': draft.matched_skills
    }


@router.get("/drafts", response_model=List[DraftResponse])
async def list_drafts(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all created drafts."""
    drafts = db.query(EmailDraft).filter(
        EmailDraft.user_id == current_user.id
    ).order_by(EmailDraft.created_at.desc()).all()
    return drafts


@router.get("/drafts/{draft_id}", response_model=DraftResponse)
async def get_draft(
    draft_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific draft."""
    draft = db.query(EmailDraft).filter(
        EmailDraft.id == draft_id,
        EmailDraft.user_id == current_user.id
    ).first()

    if not draft:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Draft not found"
        )

    return draft


@router.get("/stats", response_model=DashboardStats)
async def get_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dashboard statistics."""
    total_emails = db.query(ProcessedEmail).filter(
        ProcessedEmail.user_id == current_user.id
    ).count()

    recruiter_emails = db.query(ProcessedEmail).filter(
        ProcessedEmail.user_id == current_user.id,
        ProcessedEmail.is_recruiter_email == True
    ).count()

    drafts_created = db.query(EmailDraft).filter(
        EmailDraft.user_id == current_user.id
    ).count()

    skills_learned = db.query(SkillLearning).filter(
        SkillLearning.user_id == current_user.id
    ).count()

    # Get top requested skills
    top_skills = db.query(SkillLearning).filter(
        SkillLearning.user_id == current_user.id
    ).order_by(SkillLearning.occurrence_count.desc()).limit(10).all()

    top_requested = [
        {'name': s.skill_name, 'category': s.category, 'count': s.occurrence_count}
        for s in top_skills
    ]

    return DashboardStats(
        total_emails_processed=total_emails,
        recruiter_emails_found=recruiter_emails,
        drafts_created=drafts_created,
        skills_learned=skills_learned,
        top_requested_skills=top_requested
    )
