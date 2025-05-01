from sqlalchemy.orm import Session, joinedload
from typing import List, Optional
import datetime


from db.models.lesson import Lesson
from db.models.subject import Subject
from schemas.lesson import Lesson as LessonCreate


def get_lesson(db: Session, lesson_id: int) -> Optional[Lesson]:
    return db.query(Lesson).filter(Lesson.id == lesson_id).first()


def get_lessons(db: Session, skip: int = 0, limit: int = 100) -> List[Lesson]:
    return db.query(Lesson).offset(skip).limit(limit).all()


def create_lesson(db: Session, lesson: LessonCreate) -> Lesson:
    db_lesson = Lesson(**lesson.model_dump())
    db.add(db_lesson)
    db.commit()
    db.refresh(db_lesson)
    return db_lesson


def get_upcoming_lessons(db: Session, skip: int = 0, limit: int = 100) -> List[Lesson]:
    return (
        db.query(Lesson)
        .options(joinedload(Lesson.subject))
        .filter(Lesson.date_time >= datetime.datetime.now(datetime.timezone.utc))
        .order_by(Lesson.date_time)
        .offset(skip)
        .limit(limit)
        .all()
    )