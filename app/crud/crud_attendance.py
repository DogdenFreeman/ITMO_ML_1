from sqlalchemy.orm import Session
from typing import List, Optional

from db.models.attendance import Attendance
from schemas.attendance import AttendanceBase as AttendanceCreate

def get_attendance(db: Session, attendance_id: int) -> Optional[Attendance]:
    return db.query(Attendance).filter(Attendance.id == attendance_id).first()

def get_attendances(db: Session, skip: int = 0, limit: int = 100) -> List[Attendance]:
    return db.query(Attendance).offset(skip).limit(limit).all()

def create_attendance(db: Session, attendance: AttendanceCreate) -> Attendance:
    db_attendance = Attendance(**attendance.dict())
    db.add(db_attendance)
    db.commit()
    db.refresh(db_attendance)
    return db_attendance

def get_attendance_history(db: Session, user_id: int) -> List[Attendance]:
    return db.query(Attendance).filter(Attendance.user_id == user_id).all()