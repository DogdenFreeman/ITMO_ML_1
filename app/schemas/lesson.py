from pydantic import BaseModel
import datetime

class LessonBase(BaseModel):
    subject_id: int
    date_time: datetime.datetime

class Lesson(LessonBase):
    id: int

    class Config:
        from_attributes = True