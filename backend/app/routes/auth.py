"""
Authentication routes - login, register, 2FA setup.
"""
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.schemas import (
    UserCreate, UserLogin, Token, UserResponse,
    TwoFactorSetup, TwoFactorVerify
)
from app.auth import (
    verify_password, get_password_hash, create_access_token,
    get_current_user, generate_totp_secret, get_totp_uri,
    generate_qr_code, verify_totp
)
from app.config import get_settings

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
