"""
Gmail OAuth and connection routes.
"""
import json
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google_auth_oauthlib.flow import Flow

from app.database import get_db
from app.models import User
from app.auth import get_current_user
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/api/gmail", tags=["gmail"])

SCOPES = [
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.compose'
]


def get_flow(redirect_uri: str) -> Flow:
    """Create OAuth flow from credentials."""
    credentials = json.loads(settings.google_credentials)
    flow = Flow.from_client_config(
        credentials,
        scopes=SCOPES,
        redirect_uri=redirect_uri
    )
    return flow


@router.get("/auth/url")
async def get_auth_url(
    request: Request,
    current_user: User = Depends(get_current_user)
):
    """Get Gmail OAuth URL for user authorization."""
    # Build redirect URI
    redirect_uri = str(request.url_for('gmail_callback'))

    flow = get_flow(redirect_uri)
    auth_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent'
    )

    return {"auth_url": auth_url, "state": state}


@router.get("/auth/callback", name="gmail_callback")
async def gmail_callback(
    request: Request,
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    """Handle Gmail OAuth callback."""
    redirect_uri = str(request.url_for('gmail_callback'))
    flow = get_flow(redirect_uri)

    try:
        flow.fetch_token(code=code)
        credentials = flow.credentials

        # Store tokens - in production, associate with user session
        token_data = {
            'token': credentials.token,
            'refresh_token': credentials.refresh_token,
            'token_uri': credentials.token_uri,
            'client_id': credentials.client_id,
            'client_secret': credentials.client_secret,
            'scopes': list(credentials.scopes)
        }

        # Redirect to frontend with success
        frontend_url = settings.frontend_url or "http://localhost:3000"
        return RedirectResponse(
            url=f"{frontend_url}/gmail/connected?success=true"
        )

    except Exception as e:
        frontend_url = settings.frontend_url or "http://localhost:3000"
        return RedirectResponse(
            url=f"{frontend_url}/gmail/connected?success=false&error={str(e)}"
        )


@router.post("/connect")
async def connect_gmail(
    token_data: dict,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Store Gmail OAuth tokens for user."""
    current_user.gmail_token = json.dumps(token_data)
    current_user.gmail_connected = True
    db.commit()

    return {"message": "Gmail connected successfully"}


@router.delete("/disconnect")
async def disconnect_gmail(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Disconnect Gmail from user account."""
    current_user.gmail_token = None
    current_user.gmail_connected = False
    db.commit()

    return {"message": "Gmail disconnected"}


@router.get("/status")
async def gmail_status(current_user: User = Depends(get_current_user)):
    """Check Gmail connection status."""
    return {
        "connected": current_user.gmail_connected,
        "has_token": current_user.gmail_token is not None
    }
