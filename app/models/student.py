from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class StudentStatus(str, Enum):
    active = "active"
    inactive = "inactive"
    graduated = "graduated"
    suspended = "suspended"


class StudentBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    phone: Optional[str] = Field(default=None, max_length=20)
    date_of_birth: Optional[date] = None


class StudentCreate(StudentBase):
    pass


class StudentUpdate(BaseModel):
    first_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    last_name: Optional[str] = Field(default=None, min_length=2, max_length=100)
    email: Optional[EmailStr] = None
    phone: Optional[str] = Field(default=None, max_length=20)
    date_of_birth: Optional[date] = None
    status: Optional[StudentStatus] = None


class StudentResponse(StudentBase):
    id: int
    student_id: str
    status: StudentStatus
    enrollment_date: Optional[date] = None

    model_config = ConfigDict(from_attributes=True)
