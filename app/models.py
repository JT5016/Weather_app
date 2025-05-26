# app/models.py

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text
from sqlalchemy.orm import relationship
from .database import Base
import datetime

class User(Base):
    __tablename__ = "users"

    id        = Column(Integer, primary_key=True, index=True)
    email     = Column(String(255), unique=True, index=True, nullable=False)
    hashed_pw = Column(String(255), nullable=False)

    # back-ref to this user's weather requests
    weather_requests = relationship("WeatherRequest", back_populates="owner")


class WeatherRequest(Base):
    __tablename__ = "weather_requests"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)  # ← must belong to someone
    location   = Column(String(255), index=True, nullable=False)
    start_date = Column(DateTime, nullable=True)
    end_date   = Column(DateTime, nullable=True)
    response   = Column(Text, nullable=False)  # raw JSON
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # back-ref to the owning user
    owner = relationship("User", back_populates="weather_requests")
