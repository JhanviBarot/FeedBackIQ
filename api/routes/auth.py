from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel, Field, field_validator

from api.middleware.rate_limiter import limiter

from api.storage.users import UserStore
from api.auth.password import hash_password, verify_password
from api.auth.tokens import (create_access_token, create_refresh_token,
                              decode_refresh_token)
from api.auth.dependencies import get_current_user

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ── Pydantic models ───────────────────────────────────────────────────

class SignupRequest(BaseModel):
    email: str
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=100)

    @field_validator("email")
    @classmethod
    def validate_email_format(cls, v: str) -> str:
        import re
        v = v.strip().lower()
        if not re.match(r'^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$', v):
            raise ValueError("Invalid email address format")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    has_profile: bool


class RefreshRequest(BaseModel):
    refresh_token: str


class ProfileUpdateRequest(BaseModel):
    company_name: str = Field(min_length=1, max_length=100)
    industry: str = Field(min_length=1)
    categories: List[str] = Field(min_length=2, max_length=8)
    description: Optional[str] = ""
    urgency_definition: Optional[str] = ""


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8, max_length=128)


class UserMeResponse(BaseModel):
    user_id: str
    email: str
    full_name: str
    created_at: str
    last_login: Optional[str]
    profile: Optional[dict]
    session_count: int
    has_profile: bool


# ── Helpers ───────────────────────────────────────────────────────────

def _validate_categories(categories: List[str]) -> None:
    def word_overlap(a: str, b: str) -> float:
        wa = set(a.lower().split())
        wb = set(b.lower().split())
        if not wa or not wb:
            return 0.0
        return len(wa & wb) / max(len(wa), len(wb))

    for i in range(len(categories)):
        for j in range(i + 1, len(categories)):
            a = categories[i].strip()
            b = categories[j].strip()
            if word_overlap(a, b) >= 0.6:
                raise HTTPException(
                    status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                    detail=(
                        f"Categories '{a}' and '{b}' are too similar "
                        f"(60%+ word overlap). Use more distinct names."
                    ),
                )


def _build_token_response(user: dict) -> TokenResponse:
    return TokenResponse(
        access_token=create_access_token(user["user_id"], user["email"]),
        refresh_token=create_refresh_token(user["user_id"]),
        token_type="bearer",
        user_id=user["user_id"],
        email=user["email"],
        full_name=user["full_name"],
        has_profile=user.get("profile") is not None,
    )


# ── Endpoints ─────────────────────────────────────────────────────────

@router.post("/signup", response_model=TokenResponse,
             status_code=status.HTTP_201_CREATED,
             summary="Register a new user account")
@limiter.limit("10/minute")
async def signup(request: Request, body: SignupRequest):
    store = UserStore()
    if store.email_exists(str(body.email)):
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )
    hashed = hash_password(body.password)
    try:
        user = store.create_user(
            email=str(body.email),
            hashed_password=hashed,
            full_name=body.full_name,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                            detail=str(e))
    return _build_token_response(user)


@router.post("/login", response_model=TokenResponse,
             summary="Login with email and password")
@limiter.limit("10/minute")
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    store = UserStore()
    _DUMMY_HASH = ("$argon2id$v=19$m=65536,t=3,p=4$"
                   "dGVzdHNhbHQ$dGVzdGhhc2g")
    invalid_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user = store.get_user_by_email(form_data.username)
    if user is None:
        verify_password(form_data.password, _DUMMY_HASH)
        raise invalid_exc
    if not verify_password(form_data.password, user["hashed_password"]):
        raise invalid_exc
    if not user.get("is_active", True):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated",
        )
    store.update_last_login(user["user_id"])
    return _build_token_response(user)


@router.post("/refresh", response_model=TokenResponse,
             summary="Refresh access token using refresh token")
async def refresh_token(request: RefreshRequest):
    store = UserStore()
    exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired refresh token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    user_id = decode_refresh_token(request.refresh_token)
    if not user_id:
        raise exc
    user = store.get_user(user_id)
    if not user or not user.get("is_active", True):
        raise exc
    return TokenResponse(
        access_token=create_access_token(user["user_id"], user["email"]),
        refresh_token=request.refresh_token,
        token_type="bearer",
        user_id=user["user_id"],
        email=user["email"],
        full_name=user["full_name"],
        has_profile=user.get("profile") is not None,
    )


@router.get("/me", response_model=UserMeResponse,
            summary="Get current user profile and stats")
async def get_me(current_user: dict = Depends(get_current_user)):
    return UserMeResponse(
        user_id=current_user["user_id"],
        email=current_user["email"],
        full_name=current_user["full_name"],
        created_at=current_user["created_at"],
        last_login=current_user.get("last_login"),
        profile=current_user.get("profile"),
        session_count=len(current_user.get("session_history", [])),
        has_profile=current_user.get("profile") is not None,
    )


@router.put("/profile", summary="Save or update company profile")
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: dict = Depends(get_current_user),
):
    categories = [c.strip() for c in request.categories if c.strip()]
    if len(categories) < 2:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="At least 2 non-empty categories required",
        )
    _validate_categories(categories)
    profile = {
        "company_name": request.company_name.strip(),
        "industry": request.industry.strip(),
        "categories": categories,
        "description": (request.description or "").strip(),
        "urgency_definition": (request.urgency_definition or "").strip(),
    }
    store = UserStore()
    store.update_profile(current_user["user_id"], profile)
    return {"message": "Profile saved successfully", "profile": profile}


@router.get("/profile", summary="Get saved company profile")
async def get_profile(current_user: dict = Depends(get_current_user)):
    profile = current_user.get("profile")
    if not profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No company profile saved. Complete profile setup first.",
        )
    return {"profile": profile}


@router.post("/change-password", summary="Change account password")
async def change_password(
    request: ChangePasswordRequest,
    current_user: dict = Depends(get_current_user),
):
    if not verify_password(request.current_password,
                           current_user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Current password is incorrect",
        )
    new_hash = hash_password(request.new_password)
    store = UserStore()
    store.change_password(current_user["user_id"], new_hash)
    return {"message": "Password changed successfully"}


@router.get("/history", summary="Get analysis session history")
async def get_history(current_user: dict = Depends(get_current_user)):
    history = current_user.get("session_history", [])
    return {"sessions": history, "total": len(history)}
