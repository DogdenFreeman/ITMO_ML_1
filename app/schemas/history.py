from pydantic import BaseModel
from typing import List
import datetime

class AttendanceRecord(BaseModel):
    subject_name: str
    date_time: datetime.datetime
    attended: bool

class AttendanceHistory(BaseModel):
    history: List[AttendanceRecord]