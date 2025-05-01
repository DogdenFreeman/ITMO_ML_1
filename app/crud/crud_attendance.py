from sqlalchemy.orm import Session
from sqlalchemy.orm import joinedload
from typing import List, Optional


from db.models.attendance import Attendance
from db.models.lesson import Lesson
from db.models.subject import Subject
from schemas.attendance import AttendanceBase as AttendanceCreate


def get_attendance(db: Session, attendance_id: int) -> Optional[Attendance]:
    return db.query(Attendance).filter(Attendance.id == attendance_id).first()


def get_attendances(db: Session, skip: int = 0, limit: int = 100) -> List[Attendance]:
    return db.query(Attendance).offset(skip).limit(limit).all()


def create_attendance(db: Session, attendance: AttendanceCreate) -> Attendance:
    db_attendance = Attendance(**attendance.model_dump())
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)
    return db_attendance


def get_attendance_history(db: Session, user_id: int, skip: int = 0, limit: int = 100) -> List[Attendance]:
    return (
        db.query(Attendance)
        .filter(Attendance.user_id == user_id)
        .options(
            joinedload(Attendance.lesson).joinedload(Lesson.subject)
        )
        .order_by(Attendance.id)
        .offset(skip)
        .limit(limit)
        .all()
    )