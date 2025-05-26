from pydantic import BaseModel, EmailStr
from typing import Optional
import datetime

class UserCreate(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: EmailStr
    class Config:
        from_attributes = True
class WeatherCreate(BaseModel):
    location: str
    start_date: Optional[datetime.date]
    end_date:   Optional[datetime.date]

class WeatherOut(BaseModel):
    id: int
    location: str
    start_date: Optional[datetime.datetime]
    end_date: Optional[datetime.datetime]
    response: str
    created_at: datetime.datetime

    class Config:
        from_attributes = True  # for Pydantic v2, replaces orm_mode

class WeatherUpdate(BaseModel):
    location: Optional[str]
    start_date: Optional[datetime.date]
    end_date:   Optional[datetime.date]
    
class SunTimes(BaseModel):
    sunrise: str   # ISO 8601
    sunset:  str   # ISO 8601

    class Config:
        orm_mode = True