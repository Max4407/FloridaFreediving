import hashlib
from datetime import UTC, datetime, timedelta

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session

from config import Settings, get_settings
from database import get_db
from models.entities import LoginAttempt

SESSION_MAX_AGE = 7 * 24 * 60 * 60
LOGIN_WINDOW = timedelta(minutes=15)
MAX_LOGIN_ATTEMPTS = 5


def validate_origin(request: Request, settings: Settings) -> None:
    if request.method not in {"POST", "PUT", "PATCH", "DELETE"}:
        return
    origin = request.headers.get("origin")
    if origin not in settings.origins:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid request origin")


def session_serializer(settings: Settings) -> URLSafeTimedSerializer:
    return URLSafeTimedSerializer(settings.session_secret, salt="officer-session-v1")


def create_session(settings: Settings) -> str:
    return session_serializer(settings).dumps(
        {"role": "officer", "issued": datetime.now(UTC).isoformat()}
    )


def requireOfficer(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> None:
    validate_origin(request, settings)
    token = request.cookies.get(settings.cookie_name)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Officer login required"
        )
    try:
        payload = session_serializer(settings).loads(token, max_age=SESSION_MAX_AGE)
    except (BadSignature, SignatureExpired) as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Session expired"
        ) from error
    if payload.get("role") != "officer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid session")


def client_hash(request: Request, settings: Settings) -> str:
    address = request.client.host if request.client else "unknown"
    return hashlib.sha256(f"{settings.session_secret}:{address}".encode()).hexdigest()


def check_rate_limit(db: Session, ip_hash: str) -> None:
    cutoff = datetime.now(UTC) - LOGIN_WINDOW
    db.execute(delete(LoginAttempt).where(LoginAttempt.attempted_at < cutoff))
    count = db.scalar(
        select(func.count()).select_from(LoginAttempt).where(LoginAttempt.ip_hash == ip_hash)
    )
    if count >= MAX_LOGIN_ATTEMPTS:
        db.commit()
        raise HTTPException(status_code=429, detail="Too many login attempts; try again later")


def verify_login(
    password: str,
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> str:
    validate_origin(request, settings)
    ip_hash = client_hash(request, settings)
    check_rate_limit(db, ip_hash)
    configured = settings.officer_password_hash.encode()
    valid = bool(configured) and bcrypt.checkpw(password.encode(), configured)
    if not valid:
        db.add(LoginAttempt(ip_hash=ip_hash))
        db.commit()
        raise HTTPException(status_code=401, detail="Incorrect password")
    db.execute(delete(LoginAttempt).where(LoginAttempt.ip_hash == ip_hash))
    db.commit()
    return create_session(settings)
