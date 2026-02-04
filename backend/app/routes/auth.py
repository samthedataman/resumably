"""
Authentication routes - login, register, 2FA setup, password reset, Google OAuth.
"""
import secrets
import logging
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from google.oauth2 import id_token
from google.auth.transport import requests as google_requests

from app.database import get_db
from app.models import User
from app.schemas import (
    UserCreate, UserLogin, Token, UserResponse,
    TwoFactorSetup, TwoFactorVerify,
    PasswordResetRequest, PasswordResetConfirm,
    GoogleAuthRequest, GoogleAuthResponse
)
from app.auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, generate_totp_secret, get_totp_uri,
    generate_qr_code, verify_totp
)
from app.config import get_settings
from app.services.email_service import send_password_reset_email, send_welcome_email

logger = logging.getLogger(__name__)
settings = get_settings()
router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/register", response_model=UserResponse)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if email exists
    existing = db.query(User).filter(User.email == user_data.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )

    # Create user
    hashed_password = get_password_hash(user_data.password)
    user = User(
        email=user_data.email,
        hashed_password=hashed_password
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    return user


@router.post("/login", response_model=Token)
async def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """Login user. If 2FA enabled, requires TOTP code."""
    user = db.query(User).filter(User.email == user_data.email).first()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password"
        )

    # Check if 2FA is enabled
    if user.is_2fa_enabled:
        if not user_data.totp_code:
            return Token(
                access_token="",
                token_type="bearer",
                requires_2fa=True
            )

        # Verify TOTP code
        if not verify_totp(user.totp_secret, user_data.totp_code):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid 2FA code"
            )

    # Create access token
    access_token = create_access_token(
        data={"sub": user.id},
        expires_delta=timedelta(minutes=settings.jwt_expire_minutes)
    )

    return Token(
        access_token=access_token,
        token_type="bearer",
        requires_2fa=False
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return current_user


@router.post("/2fa/setup", response_model=TwoFactorSetup)
async def setup_2fa(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Setup 2FA for current user. Returns QR code to scan."""
    if current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is already enabled"
        )

    # Generate new secret
    secret = generate_totp_secret()
    uri = get_totp_uri(secret, current_user.email)
    qr_code = generate_qr_code(uri)

    # Store secret (not yet enabled)
    current_user.totp_secret = secret
    db.commit()

    return TwoFactorSetup(
        secret=secret,
        qr_code=qr_code,
        uri=uri
    )


@router.post("/2fa/verify")
async def verify_2fa_setup(
    data: TwoFactorVerify,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Verify 2FA setup with a code. Enables 2FA if successful."""
    if not current_user.totp_secret:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA setup not initiated. Call /2fa/setup first."
        )

    if not verify_totp(current_user.totp_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )

    # Enable 2FA
    current_user.is_2fa_enabled = True
    db.commit()

    return {"message": "2FA enabled successfully"}


@router.post("/2fa/disable")
async def disable_2fa(
    data: TwoFactorVerify,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disable 2FA. Requires current TOTP code."""
    if not current_user.is_2fa_enabled:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="2FA is not enabled"
        )

    if not verify_totp(current_user.totp_secret, data.code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid verification code"
        )

    # Disable 2FA
    current_user.is_2fa_enabled = False
    current_user.totp_secret = None
    db.commit()

    return {"message": "2FA disabled successfully"}


# ==================== Password Reset ====================

@router.post("/forgot-password")
async def forgot_password(data: PasswordResetRequest, db: Session = Depends(get_db)):
    """Request a password reset email."""
    user = db.query(User).filter(User.email == data.email).first()

    # Always return success to prevent email enumeration
    if not user:
        return {"message": "If an account exists with that email, a reset link has been sent."}

    # Check if user signed up with Google (can't reset password)
    if user.auth_provider == "google" and not user.hashed_password:
        return {"message": "If an account exists with that email, a reset link has been sent."}

    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    user.reset_token = reset_token
    user.reset_token_expires = datetime.utcnow() + timedelta(hours=1)
    db.commit()

    # Send email
    reset_url = f"{settings.frontend_url}/reset-password"
    send_password_reset_email(user.email, reset_token, reset_url)

    return {"message": "If an account exists with that email, a reset link has been sent."}


@router.post("/reset-password")
async def reset_password(data: PasswordResetConfirm, db: Session = Depends(get_db)):
    """Reset password using token from email."""
    user = db.query(User).filter(User.reset_token == data.token).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Check if token expired
    if user.reset_token_expires and user.reset_token_expires < datetime.utcnow():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Reset token has expired. Please request a new one."
        )

    # Update password
    user.hashed_password = get_password_hash(data.new_password)
    user.reset_token = None
    user.reset_token_expires = None
    db.commit()

    return {"message": "Password has been reset successfully. You can now log in."}


# ==================== Google OAuth ====================

@router.post("/google", response_model=GoogleAuthResponse)
async def google_auth(data: GoogleAuthRequest, db: Session = Depends(get_db)):
    """Authenticate with Google Sign-In."""
    try:
        # Verify the Google ID token
        idinfo = id_token.verify_oauth2_token(
            data.credential,
            google_requests.Request(),
            settings.google_client_id
        )

        # Get user info from token
        google_id = idinfo.get("sub")
        email = idinfo.get("email")
        name = idinfo.get("name")

        if not email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email not provided by Google"
            )

        # Check if user exists by Google ID or email
        user = db.query(User).filter(
            (User.google_id == google_id) | (User.email == email)
        ).first()

        is_new_user = False

        if not user:
            # Create new user
            user = User(
                email=email,
                full_name=name,
                google_id=google_id,
                auth_provider="google",
                is_active=True
            )
            db.add(user)
            db.commit()
            db.refresh(user)
            is_new_user = True

            # Send welcome email
            send_welcome_email(email, name)

        elif not user.google_id:
            # Link existing email account with Google
            user.google_id = google_id
            user.auth_provider = "google"
            if name and not user.full_name:
                user.full_name = name
            db.commit()

        # Create access token
        access_token = create_access_token(
            data={"sub": user.id},
            expires_delta=timedelta(minutes=settings.jwt_expire_minutes)
        )

        return GoogleAuthResponse(
            access_token=access_token,
            token_type="bearer",
            is_new_user=is_new_user
        )

    except ValueError as e:
        logger.error(f"Google token verification failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token"
        )


@router.get("/google/client-id")
async def get_google_client_id():
    """Get Google Client ID for frontend."""
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google Sign-In is not configured"
        )
    return {"client_id": settings.google_client_id}
