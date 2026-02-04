"""
Claude AI service for email classification and resume tailoring.
Uses Haiku for cheap classification, Sonnet for quality resume generation.
"""
import json
from typing import Dict, Any, List, Optional, Tuple

import anthropic

from app.config import get_settings
from app.schemas import JobDetails

settings = get_settings()


class ClaudeService:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.haiku_model = "claude-3-5-haiku-20241022"
        self.sonnet_model = "claude-sonnet-4-20250514"

    def classify_email(self, email: Dict[str, Any]) -> JobDetails:
        """
        Use Haiku to quickly classify if an email is from a recruiter.
        Returns JobDetails with extracted information.
        """
        prompt = f"""Analyze this email and determine if it's a job opportunity from a recruiter or hiring manager.

EMAIL SUBJECT: {email.get('subject', '')}
FROM: {email.get('from', '')}
BODY:
{email.get('body', '')[:3000]}

Respond with a JSON object:
{{
    "is_recruiter_email": true/false,
    "confidence": 0.0-1.0,
    "job_title": "extracted job title or null",
    "company": "company name or null",
    "key_requirements": ["list", "of", "requirements"],
    "key_technologies": ["tech", "stack", "mentioned"],
    "job_type": "full-time/contract/remote/hybrid/null",
    "seniority_level": "junior/mid/senior/lead/null",
    "salary_range": "if mentioned or null",
    "recruiter_name": "name of recruiter if found or null",
    "reason": "brief explanation"
}}

Only return the JSON, no other text."""

        response = self.client.messages.create(
            model=self.haiku_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            text = response.content[0].text
            # Clean up potential markdown
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            result = json.loads(text.strip())
            return JobDetails(**result)
        except (json.JSONDecodeError, IndexError) as e:
            return JobDetails(
                is_recruiter_email=False,
                confidence=0.0,
                reason=f"Failed to parse response: {str(e)}"
            )

    def tailor_resume(
        self,
        base_resume: Dict[str, Any],
        job_details: JobDetails,
        skills_data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Use Sonnet to tailor resume for the specific job.
        Returns modified resume data optimized for the role.
        """
        skills_context = skills_data or {}

        prompt = f"""You are an expert resume writer tailoring a resume for a specific opportunity.

JOB DETAILS:
- Title: {job_details.job_title or 'Unknown'}
- Company: {job_details.company or 'Unknown'}
- Requirements: {', '.join(job_details.key_requirements)}
- Technologies: {', '.join(job_details.key_technologies)}
- Type: {job_details.job_type or 'Unknown'}
- Level: {job_details.seniority_level or 'Unknown'}

SKILLS ANALYSIS (if available):
{json.dumps(skills_context, indent=2) if skills_context else 'No pre-computed skills data'}

BASE RESUME:
{json.dumps(base_resume, indent=2)}

INSTRUCTIONS:
1. Craft a tailored summary that specifically mentions the company and role, highlighting relevant experience
2. Reorder skills sections to put matched skills first
3. Reorder experience to prioritize roles most relevant to this job
4. Adjust bullet points to emphasize achievements matching the job requirements
5. CRITICAL: Keep all facts accurate - only reframe/emphasize, NEVER fabricate
6. Optimize for ATS by including exact keywords from job requirements
7. Keep the same JSON structure as the base resume

Return the complete tailored resume as a JSON object with the EXACT same structure as the base resume.
Only return valid JSON, no other text."""

        response = self.client.messages.create(
            model=self.sonnet_model,
            max_tokens=4096,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            text = response.content[0].text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            return json.loads(text.strip())
        except (json.JSONDecodeError, IndexError) as e:
            print(f"Error parsing tailored resume: {e}")
            return base_resume

    def generate_reply_email(
        self,
        original_email: Dict[str, Any],
        job_details: JobDetails,
        candidate_info: Dict[str, Any],
        matched_skills: List[str] = None
    ) -> str:
        """
        Generate a personalized reply email.
        Uses Haiku for cost efficiency.
        """
        recruiter_name = job_details.recruiter_name or ''
        greeting = f"Hi {recruiter_name}," if recruiter_name else "Hi,"

        matched = matched_skills or job_details.key_technologies[:5]

        prompt = f"""Write a perfect reply email for a job seeker.

ORIGINAL EMAIL:
From: {original_email.get('from', '')}
Subject: {original_email.get('subject', '')}
Body: {original_email.get('body', '')[:2000]}

JOB DETAILS:
- Title: {job_details.job_title or 'the position'}
- Company: {job_details.company or 'your company'}
- Technologies needed: {', '.join(job_details.key_technologies)}

CANDIDATE MATCHED QUALIFICATIONS:
- Matched Skills: {', '.join(matched)}

CANDIDATE INFO:
- Name: {candidate_info.get('name', 'Candidate')}
- Current Role: {candidate_info.get('title', '')}
- Email: {candidate_info.get('email', '')}

EMAIL REQUIREMENTS:
1. Start with "{greeting}" (casual but professional)
2. Show genuine enthusiasm for THIS specific role and company
3. Mention 1-2 specific matched skills/achievements that align with their needs
4. Mention the attached resume
5. Offer specific availability (e.g., "I'm available this week for a call")
6. Keep it under 120 words - recruiters are busy
7. End with "Best, {candidate_info.get('name', '').split()[0] if candidate_info.get('name') else 'Candidate'}"
8. NO clichés like "I hope this finds you well" or "I'm excited to apply"
9. Sound human, confident, and direct - not like a form letter

Return ONLY the email body text, nothing else."""

        response = self.client.messages.create(
            model=self.haiku_model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}]
        )

        return response.content[0].text.strip()

    def extract_skills_from_email(self, email: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Extract skills mentioned in an email for learning purposes.
        Uses Haiku for cost efficiency.
        """
        prompt = f"""Extract all technical skills, tools, and technologies mentioned in this job-related email.

EMAIL:
Subject: {email.get('subject', '')}
Body: {email.get('body', '')[:3000]}

Return a JSON array of skills with this structure:
[
    {{
        "name": "skill name (lowercase)",
        "category": "data_engineering/cloud/ai_ml/frontend/backend/devops/analytics/other",
        "context": "brief context of how it was mentioned"
    }}
]

Only return the JSON array, no other text."""

        response = self.client.messages.create(
            model=self.haiku_model,
            max_tokens=1024,
            messages=[{"role": "user", "content": prompt}]
        )

        try:
            text = response.content[0].text
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]

            return json.loads(text.strip())
        except (json.JSONDecodeError, IndexError):
            return []
