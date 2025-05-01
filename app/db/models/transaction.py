from sqlalchemy import Column, Integer, Float, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from db.base import Base
import datetime


class Transaction(Base):
    __tablename__ = 'transactions'

    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float, nullable=False)
    transaction_type = Column(String, nullable=False)
    timestamp = Column(DateTime, default=datetime.datetime.now(datetime.timezone.utc), nullable=False)
    user_id = Column(Integer, ForeignKey('users.id'), nullable=False)
    prediction_request_id = Column(Integer, ForeignKey('predictions.id'), nullable=True)

    owner = relationship("User", back_populates="transactions")