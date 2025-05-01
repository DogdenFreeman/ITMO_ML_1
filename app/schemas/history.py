from pydantic import BaseModel, ConfigDict
from typing import List
import datetime


class AttendanceRecord(BaseModel):
    subject_name: str
    date_time: datetime.datetime
    attended: bool

    model_config = ConfigDict(from_attributes=True)


class AttendanceHistory(BaseModel):
    history: List[AttendanceRecord]

    model_config = ConfigDict(from_attributes=True)