from typing import List, Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from api import deps
from schemas import attendance as attendance_schema
from schemas import history as history_schema
from crud import crud_attendance
from db.models.user import User as UserModel

router = APIRouter()

@router.get("/", response_model=List[attendance_schema.Attendance])
def read_attendances(db: Annotated[Session, Depends(deps.get_db)]):
    return crud_attendance.get_attendances(db)

@router.post("/", response_model=attendance_schema.Attendance)
def create_attendance(db: Annotated[Session, Depends(deps.get_db)], attendance: attendance_schema.AttendanceBase):
    return crud_attendance.create_attendance(db, attendance)

@router.get("/history", response_model=history_schema.AttendanceHistory)
def read_attendance_history(db: Annotated[Session, Depends(deps.get_db)], current_user: Annotated[UserModel, Depends(deps.get_current_user)]):
    history = crud_attendance.get_attendance_history(db, current_user.id)
    # история посещений для ответа
    attendance_history = []
    for attendance in history:
        attendance_history.append(history_schema.AttendanceRecord(
            subject_name=attendance.lesson.subject.name,
            date_time=attendance.lesson.date_time,
            attended=attendance.attended
        ))
    return history_schema.AttendanceHistory(history=attendance_history)