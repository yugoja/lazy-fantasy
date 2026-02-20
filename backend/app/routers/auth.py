import logging
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.schemas.auth import (
    GoogleAuthRequest,
    GoogleAuthResponse,
    Token,
    UserCreate,
    UserResponse,
)
from app.services.auth import (
    authenticate_user,
    create_access_token,
    create_google_user,
    create_user,
    get_user_by_email,
    get_user_by_google_id,
    get_user_by_username,
)

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
    return Token(access_token=access_token, token_type="bearer")


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

    # 1. Try to find by google_id (already linked)
    user = get_user_by_google_id(db, google_id)

    if not user:
        # 2. Try to find by email (existing account, link it)
        user = get_user_by_email(db, email)
        if user:
            user.google_id = google_id
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
            user = create_google_user(db, email, google_id, username)

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=access_token_expires,
    )
    return GoogleAuthResponse(
        access_token=access_token,
        token_type="bearer",
        username=user.username,
    )
