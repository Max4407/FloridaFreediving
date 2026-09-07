from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from config import Settings, get_settings
from database import get_db
from schemas import LoginInput
from services.auth import SESSION_MAX_AGE, requireOfficer, verify_login

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.post("/login")
def login(
    payload: LoginInput,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    token = verify_login(payload.password, request, db, settings)
    response.set_cookie(
        settings.cookie_name,
        token,
        max_age=SESSION_MAX_AGE,
        secure=settings.cookie_secure,
        httponly=True,
        samesite="lax",
        path="/",
    )
    return {"authenticated": True}


@router.post("/logout", dependencies=[Depends(requireOfficer)])
def logout(response: Response, settings: Settings = Depends(get_settings)):
    response.delete_cookie(
        settings.cookie_name, path="/", secure=settings.cookie_secure, httponly=True
    )
    return {"authenticated": False}


@router.get("/session", dependencies=[Depends(requireOfficer)])
def session_status():
    return {"authenticated": True}
