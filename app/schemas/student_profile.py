from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class StudentProfileBase(BaseModel):
    student_id: str
    department: str
    phone_number: Optional[str] = None
    address: Optional[str] = None

class StudentProfileCreate(StudentProfileBase):
    pass

class StudentProfileUpdate(StudentProfileBase):
    student_id: Optional[str] = None
    department: Optional[str] = None

class StudentProfile(StudentProfileBase):
    id: int
    user_id: int
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True
