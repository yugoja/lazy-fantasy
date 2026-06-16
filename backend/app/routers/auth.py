import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.auth import (
    ForgotPasswordRequest,
    GoogleAuthRequest,
    GoogleAuthResponse,
    ProfileUpdate,
    ResetPasswordRequest,
    SimpleMessage,
    Token,
    UserCreate,
    UserResponse,
)
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_google_user,
    create_password_reset_token,
    create_user,
    get_current_user,
    get_password_hash,
    get_user_by_email,
    get_user_by_google_id,
    get_user_by_username,
    verify_password_reset_token,
)
from app.services.notifications import send_password_reset_email
from app.models import User
from app.utils.images import AVATARS_DIR, save_upload

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def signup(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.

    - **username**: Unique username
    - **email**: Valid email address
    - **password**: Password (will be hashed)
    """
    # Check if username already exists
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )

    # Check if email already exists
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    # Create user
    user = create_user(db, user_data.username, user_data.email, user_data.password)
    return user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
):
    """
    Login and get JWT access token.

    Uses OAuth2 password flow - send username and password as form data.
    """
    user = authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return Token(access_token=access_token, token_type="bearer", display_name=user.display_name)


@router.post("/forgot-password", response_model=SimpleMessage)
async def forgot_password(data: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """Email a password-reset link. Always returns 200 (never reveals whether an
    account exists)."""
    generic = SimpleMessage(message="If an account exists for that email, a reset link is on its way.")
    user = get_user_by_email(db, data.email)
    # Only for password accounts — Google-only users have no password to reset.
    if user and user.hashed_password:
        token = create_password_reset_token(user)
        reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
        try:
            send_password_reset_email(user.email, reset_url)
        except Exception as e:
            logger.error(f"forgot-password email failed for {user.email}: {e}")
    return generic


@router.post("/reset-password", response_model=Token)
async def reset_password(data: ResetPasswordRequest, db: Session = Depends(get_db)):
    """Set a new password from a valid reset token, and log the user straight in."""
    if len(data.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters.",
        )
    user = verify_password_reset_token(db, data.token)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This reset link is invalid or has expired. Request a new one.",
        )
    user.hashed_password = get_password_hash(data.new_password)
    db.commit()

    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return Token(access_token=access_token, token_type="bearer", display_name=user.display_name)


@router.post("/google", response_model=GoogleAuthResponse)
async def google_auth(data: GoogleAuthRequest, db: Session = Depends(get_db)):
    """
    Authenticate with Google SSO.

    Verifies the Google ID token, finds or creates the user, and returns a JWT.
    """
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google SSO is not configured",
        )

    # Verify the Google ID token
    try:
        idinfo = google_id_token.verify_oauth2_token(
            data.credential,
            google_requests.Request(),
            settings.GOOGLE_CLIENT_ID,
        )
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Google token",
        )

    google_id = idinfo["sub"]
    email = idinfo.get("email", "")
    google_display_name = idinfo.get("name")  # Full name from Google profile

    # 1. Try to find by google_id (already linked)
    user = get_user_by_google_id(db, google_id)

    if not user:
        # 2. Try to find by email (existing account, link it)
        user = get_user_by_email(db, email)
        if user:
            user.google_id = google_id
            # Populate display_name from Google if not already set
            if not user.display_name and google_display_name:
                user.display_name = google_display_name
            db.commit()
            db.refresh(user)
        else:
            # 3. Create new user with auto-generated username
            base_username = email.split("@")[0][:50]
            username = base_username
            suffix = 1
            while get_user_by_username(db, username):
                username = f"{base_username[:46]}{suffix}"
                suffix += 1
            user = create_google_user(db, email, google_id, username, display_name=google_display_name)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return GoogleAuthResponse(
        access_token=access_token,
        token_type="bearer",
        username=user.username,
        display_name=user.display_name,
    )


@router.get("/me", response_model=UserResponse)
async def get_me(current_user: User = Depends(get_current_user)):
    """Get current user's profile."""
    return current_user


@router.post("/me/avatar", response_model=UserResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload or replace the current user's profile picture."""
    file_bytes = await file.read()
    dest = AVATARS_DIR / f"{current_user.id}.jpg"
    save_upload(file_bytes, file.content_type or "", dest, (256, 256))
    current_user.avatar_url = f"/uploads/avatars/{current_user.id}.jpg"
    db.commit()
    db.refresh(current_user)
    return current_user


@router.put("/me", response_model=UserResponse)
async def update_me(
    data: ProfileUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Update current user's profile."""
    display_name = data.display_name.strip()
    if not display_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Display name cannot be empty",
        )
    current_user.display_name = display_name
    db.commit()
    db.refresh(current_user)
    return current_user
