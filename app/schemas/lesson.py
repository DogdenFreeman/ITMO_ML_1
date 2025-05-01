from pydantic import BaseModel, ConfigDict
import datetime


class LessonBase(BaseModel):
    subject_id: int
    date_time: datetime.datetime


class Lesson(LessonBase):
    id: int

    model_config = ConfigDict(from_attributes=True)