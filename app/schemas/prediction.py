from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
import datetime



class PredictionInputData(BaseModel):
    qr_code_content: Optional[str] = None
    feature1: float
    feature2: str


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

    class Config:
        from_attributes = True
