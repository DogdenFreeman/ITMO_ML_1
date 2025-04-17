from typing import List, Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api import deps
from schemas import lesson as lesson_schema
from crud import crud_lesson

router = APIRouter()

@router.get("/", response_model=List[lesson_schema.Lesson])
def read_lessons(db: Annotated[Session, Depends(deps.get_db)]):
    return crud_lesson.get_lessons(db)

@router.post("/", response_model=lesson_schema.Lesson)
def create_lesson(db: Annotated[Session, Depends(deps.get_db)], lesson: lesson_schema.LessonCreate):
    return crud_lesson.create_lesson(db, lesson)