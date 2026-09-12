from __future__ import annotations

import datetime as dt

import bcrypt
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.db.models import User
from app.db.session import get_db

settings = get_settings()
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")

# Calling bcrypt directly rather than through passlib: passlib 1.7.x's
# bcrypt backend detection does not understand bcrypt>=4.1's internals
# (it probes an attribute bcrypt removed) and fails at import/first-use.
# passlib is effectively unmaintained, so rather than pin bcrypt back to
# an old release to dodge the bug, this uses the actively-maintained
# `bcrypt` package's own API — one fewer dependency too.
#
# bcrypt only uses the first 72 bytes of the input; this truncates
# rather than raising, matching bcrypt's own documented behavior.
_BCRYPT_MAX_BYTES = 72


def hash_password(password: str) -> str:
    pw_bytes = password.encode("utf-8")[:_BCRYPT_MAX_BYTES]
    return bcrypt.hashpw(pw_bytes, bcrypt.gensalt()).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8")[:_BCRYPT_MAX_BYTES], hashed.encode("utf-8"))
    except ValueError:
        # Malformed/unknown hash format — never let this crash a login attempt.
        return False


def create_access_token(*, subject: str, role: str) -> str:
    expire = dt.datetime.now(dt.UTC) + dt.timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": subject, "role": role, "exp": expire}
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def _credentials_exception() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise _credentials_exception()
    except JWTError as exc:
        raise _credentials_exception() from exc

    result = await db.execute(select(User).where(User.username == username))
    user = result.scalar_one_or_none()
    if user is None or not user.is_active:
        raise _credentials_exception()
    return user


async def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required")
    return user
