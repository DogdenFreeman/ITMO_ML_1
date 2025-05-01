from typing import List, Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api import deps
from schemas.attendance import Attendance, AttendanceBase
from schemas.history import AttendanceHistory, AttendanceRecord

from crud import crud_attendance
from db.models.user import User


router = APIRouter()


@router.get("/", response_model=List[Attendance])
def read_attendances(
    db: Annotated[Session, Depends(deps.get_db)],
    skip: int = 0,
    limit: int = 100
):
    return crud_attendance.get_attendances(db, skip=skip, limit=limit)


@router.post("/", response_model=Attendance)
def create_attendance(db: Annotated[Session, Depends(deps.get_db)], attendance: AttendanceBase):
    return crud_attendance.create_attendance(db, attendance)


@router.get("/history", response_model=AttendanceHistory)
def read_attendance_history(
    db: Annotated[Session, Depends(deps.get_db)],
    current_user: Annotated[User, Depends(deps.get_current_user)],
    skip: int = 0,
    limit: int = 100
):
    history_records = crud_attendance.get_attendance_history(
        db, user_id=current_user.id, skip=skip, limit=limit
    )

    attendance_history = []
    for attendance in history_records:
        if attendance.lesson and attendance.lesson.subject:
             attendance_history.append(AttendanceRecord(
                subject_name=attendance.lesson.subject.name,
                date_time=attendance.lesson.date_time,
                attended=attendance.attended
            ))

    return AttendanceHistory(history=attendance_history)