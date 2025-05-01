from typing import List, Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api import deps
from schemas.subject import Subject, SubjectBase

from crud import crud_subject


router = APIRouter()


@router.get("/", response_model=List[Subject])
def read_subjects(
    db: Annotated[Session, Depends(deps.get_db)],
    skip: int = 0,
    limit: int = 100
):
    return crud_subject.get_subjects(db, skip=skip, limit=limit)


@router.post("/", response_model=Subject)
def create_subject(db: Annotated[Session, Depends(deps.get_db)], subject: SubjectBase):
    return crud_subject.create_subject(db, subject)