from pydantic import BaseModel, ConfigDict


class AttendanceBase(BaseModel):
    user_id: int
    lesson_id: int
    attended: bool


class Attendance(AttendanceBase):
    id: int

    model_config = ConfigDict(from_attributes=True)