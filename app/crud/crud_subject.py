from sqlalchemy.orm import Session
from typing import List, Optional


from db.models.subject import Subject
from schemas.subject import SubjectBase


def get_subject(db: Session, subject_id: int) -> Optional[Subject]:
    return db.query(Subject).filter(Subject.id == subject_id).first()


def get_subjects(db: Session, skip: int = 0, limit: int = 100) -> List[Subject]:
    return db.query(Subject).offset(skip).limit(limit).all()


def create_subject(db: Session, subject: SubjectBase) -> Subject:
    db_subject = Subject(**subject.model_dump())
    db.add(db_subject)
    db.commit()
    db.refresh(db_subject)
    return db_subject