"""
PDF generation service for creating professional resume PDFs.
"""
from io import BytesIO
from typing import Dict, Any, List

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, ListFlowable, ListItem
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY


class PDFService:
    def __init__(self):
        self.styles = getSampleStyleSheet()
        self._setup_custom_styles()

    def _setup_custom_styles(self):
        """Setup custom paragraph styles for the resume."""
        # Name/Header style
        self.styles.add(ParagraphStyle(
            name='ResumeName',
            parent=self.styles['Heading1'],
            fontSize=18,
            spaceAfter=6,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#1a1a1a')
        ))

        # Contact info style
        self.styles.add(ParagraphStyle(
            name='ContactInfo',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_CENTER,
            textColor=colors.HexColor('#444444'),
            spaceAfter=12
        ))

        # Section header style
        self.styles.add(ParagraphStyle(
            name='SectionHeader',
            parent=self.styles['Heading2'],
            fontSize=12,
            spaceBefore=12,
            spaceAfter=6,
            textColor=colors.HexColor('#2c5282'),
            borderPadding=(0, 0, 3, 0)
        ))

        # Company/Job title style
        self.styles.add(ParagraphStyle(
            name='JobTitle',
            parent=self.styles['Normal'],
            fontSize=11,
            fontName='Helvetica-Bold',
            spaceAfter=2,
            textColor=colors.HexColor('#1a1a1a')
        ))

        # Company details style
        self.styles.add(ParagraphStyle(
            name='CompanyDetails',
            parent=self.styles['Normal'],
            fontSize=10,
            fontName='Helvetica-Oblique',
            spaceAfter=4,
            textColor=colors.HexColor('#666666')
        ))

        # Bullet point style
        self.styles.add(ParagraphStyle(
            name='BulletPoint',
            parent=self.styles['Normal'],
            fontSize=10,
            leftIndent=15,
            spaceAfter=3,
            alignment=TA_JUSTIFY,
            textColor=colors.HexColor('#333333')
        ))

        # Summary style
        self.styles.add(ParagraphStyle(
            name='Summary',
            parent=self.styles['Normal'],
            fontSize=10,
            alignment=TA_JUSTIFY,
            spaceAfter=6,
            textColor=colors.HexColor('#333333')
        ))

        # Skills style
        self.styles.add(ParagraphStyle(
            name='Skills',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=3,
            textColor=colors.HexColor('#333333')
        ))

    def generate_resume_pdf(self, resume_data: Dict[str, Any]) -> bytes:
        """Generate a professional PDF resume from resume data."""
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=letter,
            rightMargin=0.6*inch,
            leftMargin=0.6*inch,
            topMargin=0.5*inch,
            bottomMargin=0.5*inch
        )

        story = []

        # Personal Info / Header
        personal = resume_data.get('personal', {})
        name = personal.get('name', 'Name')
        story.append(Paragraph(name, self.styles['ResumeName']))

        # Contact line
        contact_parts = []
        if personal.get('email'):
            contact_parts.append(personal['email'])
        if personal.get('phone'):
            contact_parts.append(personal['phone'])
        if personal.get('location'):
            contact_parts.append(personal['location'])
        if personal.get('linkedin'):
            contact_parts.append(f"linkedin.com/in/{personal['linkedin']}")
        if personal.get('github'):
            contact_parts.append(f"github.com/{personal['github']}")
        if personal.get('website'):
            contact_parts.append(personal['website'])

        contact_line = " | ".join(contact_parts)
        story.append(Paragraph(contact_line, self.styles['ContactInfo']))

        # Horizontal line
        story.append(HRFlowable(
            width="100%",
            thickness=1,
            color=colors.HexColor('#2c5282'),
            spaceBefore=3,
            spaceAfter=10
        ))

        # Summary
        if resume_data.get('summary'):
            story.append(Paragraph("PROFESSIONAL SUMMARY", self.styles['SectionHeader']))
            story.append(Paragraph(resume_data['summary'], self.styles['Summary']))

        # Skills
        skills = resume_data.get('skills', {})
        if skills:
            story.append(Paragraph("TECHNICAL SKILLS", self.styles['SectionHeader']))
            for category, skill_list in skills.items():
                if skill_list:
                    category_name = category.replace('_', ' ').title()
                    skills_text = f"<b>{category_name}:</b> {', '.join(skill_list)}"
                    story.append(Paragraph(skills_text, self.styles['Skills']))
            story.append(Spacer(1, 6))

        # Experience
        experience = resume_data.get('experience', [])
        if experience:
            story.append(Paragraph("PROFESSIONAL EXPERIENCE", self.styles['SectionHeader']))
            for job in experience:
                # Job title and company
                title_line = f"<b>{job.get('title', '')}</b>"
                story.append(Paragraph(title_line, self.styles['JobTitle']))

                # Company, location, dates
                company_line = f"{job.get('company', '')} | {job.get('location', '')} | {job.get('start_date', '')} - {job.get('end_date', '')}"
                story.append(Paragraph(company_line, self.styles['CompanyDetails']))

                # Highlights/bullets
                highlights = job.get('highlights', [])
                for highlight in highlights:
                    bullet_text = f"• {highlight}"
                    story.append(Paragraph(bullet_text, self.styles['BulletPoint']))

                story.append(Spacer(1, 6))

        # Education
        education = resume_data.get('education', [])
        if education:
            story.append(Paragraph("EDUCATION", self.styles['SectionHeader']))
            for edu in education:
                edu_line = f"<b>{edu.get('degree', '')}</b>"
                story.append(Paragraph(edu_line, self.styles['JobTitle']))

                details = f"{edu.get('institution', '')} | {edu.get('graduation_date', '')}"
                if edu.get('gpa'):
                    details += f" | GPA: {edu['gpa']}"
                story.append(Paragraph(details, self.styles['CompanyDetails']))

                for highlight in edu.get('highlights', []):
                    story.append(Paragraph(f"• {highlight}", self.styles['BulletPoint']))

                story.append(Spacer(1, 4))

        # Projects
        projects = resume_data.get('projects', [])
        if projects:
            story.append(Paragraph("PROJECTS", self.styles['SectionHeader']))
            for project in projects:
                project_line = f"<b>{project.get('name', '')}</b>"
                if project.get('link'):
                    project_line += f" - {project['link']}"
                story.append(Paragraph(project_line, self.styles['JobTitle']))

                if project.get('description'):
                    story.append(Paragraph(project['description'], self.styles['BulletPoint']))

                if project.get('technologies'):
                    tech_line = f"<i>Technologies: {', '.join(project['technologies'])}</i>"
                    story.append(Paragraph(tech_line, self.styles['BulletPoint']))

                story.append(Spacer(1, 4))

        # Certifications
        certifications = resume_data.get('certifications', [])
        if certifications:
            story.append(Paragraph("CERTIFICATIONS", self.styles['SectionHeader']))
            for cert in certifications:
                story.append(Paragraph(f"• {cert}", self.styles['BulletPoint']))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()
