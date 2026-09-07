from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from exceptions import ConflictError, NotFoundError
from schemas import SignupCreate
from services.dives import create_signup, get_public_dive, public_view

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/dives/{public_id}")
def read_public_dive(public_id: str, db: Session = Depends(get_db)):
    try:
        return public_view(db, get_public_dive(db, public_id))
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@router.post("/dives/{public_id}/signups", status_code=201)
def submit_signup(public_id: str, payload: SignupCreate, db: Session = Depends(get_db)):
    try:
        return create_signup(db, public_id, payload)
    except NotFoundError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ConflictError as error:
        raise HTTPException(status_code=409, detail=str(error)) from error
