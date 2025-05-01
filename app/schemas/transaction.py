from pydantic import BaseModel, ConfigDict
from typing import Optional
import datetime


class TransactionBase(BaseModel):
    amount: float
    transaction_type: str


class Transaction(TransactionBase):
    id: int
    user_id: int
    timestamp: datetime.datetime
    prediction_request_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)