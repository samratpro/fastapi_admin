from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class StudentProfileBase(BaseModel):
    student_id: str
    department: str
    date_of_birth: datetime
    phone_number: Optional[str] = None
    address: Optional[str] = None

class StudentProfileCreate(StudentProfileBase):
    user_id: int

class StudentProfileUpdate(BaseModel):
    department: Optional[str] = None
    date_of_birth: Optional[datetime] = None
    phone_number: Optional[str] = None
    address: Optional[str] = None

class StudentProfile(StudentProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True