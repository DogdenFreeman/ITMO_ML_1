from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
import datetime


class PredictionInputData(BaseModel):
    lesson_id: int


class PredictionCreate(BaseModel):
    input_data: PredictionInputData


class PredictionResult(BaseModel):
    prediction: Any
    probability: Optional[float] = None


class PredictionRequest(BaseModel):
    id: int
    user_id: int
    status: str
    input_data: Optional[Dict[str, Any]] = None
    result: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    cost: Optional[float] = None
    timestamp_created: datetime.datetime
    timestamp_completed: Optional[datetime.datetime] = None

    model_config = ConfigDict(from_attributes=True)