from typing import List, Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api import deps
from schemas import subject as subject_schema
from crud import crud_subject

router = APIRouter()


@router.get("/", response_model=List[subject_schema.Subject])
def read_subjects(db: Annotated[Session, Depends(deps.get_db)]):
    return crud_subject.get_subjects(db)


@router.post("/", response_model=subject_schema.Subject)
def create_subject(db: Annotated[Session, Depends(deps.get_db)], subject: subject_schema.SubjectCreate):
    return crud_subject.create_subject(db, subject)
