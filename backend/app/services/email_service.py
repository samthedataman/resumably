"""
Email service for sending transactional emails (password reset, etc.)
"""
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import Optional

from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


def send_email(
    to_email: str,
    subject: str,
    html_body: str,
    text_body: Optional[str] = None
) -> bool:
    """Send an email using SMTP."""
    if not settings.smtp_user or not settings.smtp_password:
        logger.warning("SMTP not configured, skipping email send")
        # In development, just log the email
        logger.info(f"Would send email to {to_email}: {subject}")
        return True

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.email_from
        msg["To"] = to_email

        # Add text and HTML parts
        if text_body:
            msg.attach(MIMEText(text_body, "plain"))
        msg.attach(MIMEText(html_body, "html"))

        # Connect and send
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)

        logger.info(f"Email sent to {to_email}: {subject}")
        return True

    except Exception as e:
        logger.error(f"Failed to send email to {to_email}: {e}")
        return False


def send_password_reset_email(to_email: str, reset_token: str, reset_url: str) -> bool:
    """Send password reset email with link."""
    full_reset_url = f"{reset_url}?token={reset_token}"

    subject = "Reset Your Resumably Password"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .button {{
                display: inline-block;
                background-color: #3b82f6;
                color: white;
                padding: 12px 24px;
                text-decoration: none;
                border-radius: 6px;
                margin: 20px 0;
            }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Reset Your Password</h2>
            <p>We received a request to reset your password for your Resumably account.</p>
            <p>Click the button below to create a new password:</p>
            <a href="{full_reset_url}" class="button">Reset Password</a>
            <p>Or copy and paste this link into your browser:</p>
            <p style="word-break: break-all; color: #3b82f6;">{full_reset_url}</p>
            <p>This link will expire in 1 hour.</p>
            <p>If you didn't request this password reset, you can safely ignore this email.</p>
            <div class="footer">
                <p>This email was sent by Resumably - AI-Powered Resume Tailoring</p>
            </div>
        </div>
    </body>
    </html>
    """

    text_body = f"""
    Reset Your Password

    We received a request to reset your password for your Resumably account.

    Click the link below to create a new password:
    {full_reset_url}

    This link will expire in 1 hour.

    If you didn't request this password reset, you can safely ignore this email.

    - Resumably Team
    """

    return send_email(to_email, subject, html_body, text_body)


def send_welcome_email(to_email: str, name: Optional[str] = None) -> bool:
    """Send welcome email to new users."""
    display_name = name or "there"
    subject = "Welcome to Resumably!"

    html_body = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
            .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
            .feature {{ margin: 15px 0; padding-left: 20px; border-left: 3px solid #3b82f6; }}
            .footer {{ margin-top: 30px; font-size: 12px; color: #666; }}
        </style>
    </head>
    <body>
        <div class="container">
            <h2>Welcome to Resumably, {display_name}!</h2>
            <p>Your account has been created successfully. Here's what you can do:</p>

            <div class="feature">
                <strong>Connect Gmail</strong>
                <p>Link your Gmail to automatically scan for recruiter emails.</p>
            </div>

            <div class="feature">
                <strong>Build Your Resume</strong>
                <p>Create your base resume that will be tailored for each opportunity.</p>
            </div>

            <div class="feature">
                <strong>Auto-Tailor Responses</strong>
                <p>Let AI craft perfect responses with customized resumes.</p>
            </div>

            <p>Get started by logging in and connecting your Gmail account!</p>

            <div class="footer">
                <p>This email was sent by Resumably - AI-Powered Resume Tailoring</p>
            </div>
        </div>
    </body>
    </html>
    """

    return send_email(to_email, subject, html_body)
