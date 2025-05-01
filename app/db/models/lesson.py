from sqlalchemy import Column, Integer, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from db.base import Base



class Lesson(Base):
    __tablename__ = 'lessons'

    id = Column(Integer, primary_key=True, index=True)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)
    date_time = Column(DateTime, nullable=False)

    subject = relationship("Subject", back_populates="lessons")
    attendances = relationship("Attendance", back_populates="lesson")