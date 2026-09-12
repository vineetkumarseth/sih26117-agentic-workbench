from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.session import get_db
from app.models.schemas import Token, UserCreate, UserOut
from app.security.audit import log_event
from app.security.auth import create_access_token, get_current_user, hash_password, require_admin, verify_password
from app.security.rate_limit import limiter
from app.config import get_settings

router = APIRouter(prefix="/api/auth", tags=["auth"])
settings = get_settings()


@router.post("/login", response_model=Token)
@limiter.limit(settings.RATE_LIMIT_LOGIN)
async def login(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.username == form_data.username))
    user = result.scalar_one_or_none()

    # Constant-shape failure path: don't reveal whether the username or the
    # password was wrong, and always run verify_password (even against a
    # dummy hash) so a nonexistent username doesn't respond measurably
    # faster than a wrong password — a small defence against username
    # enumeration via timing.
    dummy_hash = "$2b$12$kyDSHNd6taG0BZJP9E1oNuSqQfGeabrB470Dt9KlfYB.PyOvLIof6"
    ok = verify_password(form_data.password, user.hashed_password if user else dummy_hash)

    if not user or not ok or not user.is_active:
        await log_event(
            db,
            event_type="login",
            username=form_data.username,
            allowed=False,
            detail="invalid credentials",
            client_ip=request.client.host if request.client else None,
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect username or password")

    token = create_access_token(subject=user.username, role=user.role)
    await log_event(
        db,
        event_type="login",
        user_id=user.id,
        username=user.username,
        allowed=True,
        client_ip=request.client.host if request.client else None,
    )
    return Token(access_token=token, role=user.role, username=user.username)


@router.get("/me", response_model=UserOut)
async def me(current_user: User = Depends(get_current_user)):
    return UserOut(
        id=current_user.id, username=current_user.username, role=current_user.role, is_active=current_user.is_active
    )


@router.post("/users", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def create_user(
    payload: UserCreate,
    db: AsyncSession = Depends(get_db),
    _admin: User = Depends(require_admin),
):
    """Admin-only. There's no open self-registration — a confidential
    industrial tool shouldn't let anyone on the network create their own
    account."""
    user = User(username=payload.username, hashed_password=hash_password(payload.password), role=payload.role)
    db.add(user)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists") from exc
    await db.refresh(user)
    return UserOut(id=user.id, username=user.username, role=user.role, is_active=user.is_active)
