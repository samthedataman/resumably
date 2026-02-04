"""
Skills management routes.
"""
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User, Skill, SkillLearning
from app.schemas import SkillCreate, SkillResponse, SkillLearningResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/skills", tags=["skills"])


@router.get("/", response_model=List[SkillResponse])
async def list_skills(
    category: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all skills for current user."""
    query = db.query(Skill).filter(Skill.user_id == current_user.id)

    if category:
        query = query.filter(Skill.category == category)

    skills = query.order_by(Skill.category, Skill.name).all()
    return skills


@router.post("/", response_model=SkillResponse)
async def create_skill(
    skill_data: SkillCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new skill."""
    # Check if skill already exists
    existing = db.query(Skill).filter(
        Skill.user_id == current_user.id,
        Skill.name == skill_data.name.lower()
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skill already exists"
        )

    skill = Skill(
        user_id=current_user.id,
        name=skill_data.name.lower(),
        category=skill_data.category,
        proficiency=skill_data.proficiency,
        years_experience=skill_data.years_experience,
        proof_points=skill_data.proof_points,
        keywords=skill_data.keywords,
        source='manual'
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)

    return skill


@router.put("/{skill_id}", response_model=SkillResponse)
async def update_skill(
    skill_id: int,
    skill_data: SkillCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a skill."""
    skill = db.query(Skill).filter(
        Skill.id == skill_id,
        Skill.user_id == current_user.id
    ).first()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found"
        )

    skill.name = skill_data.name.lower()
    skill.category = skill_data.category
    skill.proficiency = skill_data.proficiency
    skill.years_experience = skill_data.years_experience
    skill.proof_points = skill_data.proof_points
    skill.keywords = skill_data.keywords

    db.commit()
    db.refresh(skill)

    return skill


@router.delete("/{skill_id}")
async def delete_skill(
    skill_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a skill."""
    skill = db.query(Skill).filter(
        Skill.id == skill_id,
        Skill.user_id == current_user.id
    ).first()

    if not skill:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Skill not found"
        )

    db.delete(skill)
    db.commit()

    return {"message": "Skill deleted"}


@router.get("/learned", response_model=List[SkillLearningResponse])
async def list_learned_skills(
    category: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List skills learned from processed emails."""
    query = db.query(SkillLearning).filter(
        SkillLearning.user_id == current_user.id
    )

    if category:
        query = query.filter(SkillLearning.category == category)

    skills = query.order_by(SkillLearning.occurrence_count.desc()).all()
    return skills


@router.post("/learned/{learning_id}/convert")
async def convert_learned_skill(
    learning_id: int,
    proficiency: str = "intermediate",
    years_experience: float = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Convert a learned skill to a permanent skill entry."""
    learned = db.query(SkillLearning).filter(
        SkillLearning.id == learning_id,
        SkillLearning.user_id == current_user.id
    ).first()

    if not learned:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Learned skill not found"
        )

    # Check if skill already exists
    existing = db.query(Skill).filter(
        Skill.user_id == current_user.id,
        Skill.name == learned.skill_name
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Skill already exists in your profile"
        )

    # Create skill
    skill = Skill(
        user_id=current_user.id,
        name=learned.skill_name,
        category=learned.category,
        proficiency=proficiency,
        years_experience=years_experience,
        proof_points=[],
        keywords=[],
        source='learned'
    )
    db.add(skill)
    db.commit()
    db.refresh(skill)

    return {"message": "Skill converted", "skill_id": skill.id}


@router.get("/categories")
async def list_skill_categories(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List all skill categories with counts."""
    skills = db.query(Skill).filter(Skill.user_id == current_user.id).all()

    categories = {}
    for skill in skills:
        if skill.category not in categories:
            categories[skill.category] = 0
        categories[skill.category] += 1

    return categories


@router.post("/bulk-import")
async def bulk_import_skills(
    skills: List[SkillCreate],
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Bulk import skills."""
    imported = 0
    skipped = 0

    for skill_data in skills:
        # Check if exists
        existing = db.query(Skill).filter(
            Skill.user_id == current_user.id,
            Skill.name == skill_data.name.lower()
        ).first()

        if existing:
            skipped += 1
            continue

        skill = Skill(
            user_id=current_user.id,
            name=skill_data.name.lower(),
            category=skill_data.category,
            proficiency=skill_data.proficiency,
            years_experience=skill_data.years_experience,
            proof_points=skill_data.proof_points,
            keywords=skill_data.keywords,
            source='import'
        )
        db.add(skill)
        imported += 1

    db.commit()

    return {
        "imported": imported,
        "skipped": skipped,
        "message": f"Imported {imported} skills, skipped {skipped} duplicates"
    }
