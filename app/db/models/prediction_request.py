from sqlalchemy import Column, Integer, String, DateTime, JSON, ForeignKey, Float
from sqlalchemy.orm import relationship
from db.base import Base
import datetime


class PredictionRequest(Base):
    __tablename__ = 'predictions'

    id = Column(Integer, primary_key=True, index=True)
    input_data = Column(JSON, nullable=True)
    result = Column(JSON, nullable=True)
    status = Column(String, default="pending", nullable=False)
    cost = Column(Float, nullable=False)
    timestamp_created = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc), nullable=False)
    timestamp_completed = Column(DateTime, nullable=True)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    error_message = Column(String, nullable=True)

    owner = relationship("User", back_populates="predictions")