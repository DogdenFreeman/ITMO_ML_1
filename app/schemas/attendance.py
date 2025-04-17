from pydantic import BaseModel

class AttendanceBase(BaseModel):
    user_id: int
    lesson_id: int
    attended: bool

class Attendance(AttendanceBase):
    id: int

    class Config:
        from_attributes = True