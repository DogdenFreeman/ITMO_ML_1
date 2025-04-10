from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from app.db.base import Base
import datetime

class PredictionRequest(Base):
    __tablename__ = 'predictions'

    id = Column(Integer, primary_key=True, index=True)
    input_data = Column(JSON)
    prediction_result = Column(JSON)
    status = Column(String, default="completed")
    cost = Column(Float, default=1.0)
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc))
    user_id = Column(Integer, ForeignKey('users.id'))

    owner = relationship("User", back_populates="predictions")
