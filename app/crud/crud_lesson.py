from sqlalchemy.orm import Session
from typing import List, Optional

from db.models.lesson import Lesson
from schemas.lesson import LessonCreate

def get_lesson(db: Session, lesson_id: int) -> Optional[Lesson]:
    return db.query(Lesson).filter(Lesson.id == lesson_id).first()

def get_lessons(db: Session, skip: int = 0, limit: int = 100) -> List[Lesson]:
    return db.query(Lesson).offset(skip).limit(limit).all()

def create_lesson(db: Session, lesson: LessonCreate) -> Lesson:
    db_lesson = Lesson(**lesson.dict())
    db.add(db_lesson)
    db.commit()
    db.refresh(db_lesson)
    return db_lesson