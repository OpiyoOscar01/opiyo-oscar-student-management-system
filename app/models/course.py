from enum import Enum
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class CourseStatus(str, Enum):
    active = "active"
    inactive = "inactive"


class CourseBase(BaseModel):
    course_code: str = Field(..., min_length=2, max_length=20)
    course_name: str = Field(..., min_length=2, max_length=255)
    credits: int = Field(..., ge=1, le=6)
    description: Optional[str] = None
    max_capacity: int = Field(default=30, ge=1, le=1000)


class CourseCreate(CourseBase):
    pass


class CourseUpdate(BaseModel):
    course_code: Optional[str] = Field(default=None, min_length=2, max_length=20)
    course_name: Optional[str] = Field(default=None, min_length=2, max_length=255)
    credits: Optional[int] = Field(default=None, ge=1, le=6)
    description: Optional[str] = None
    max_capacity: Optional[int] = Field(default=None, ge=1, le=1000)
    status: Optional[CourseStatus] = None


class CourseResponse(CourseBase):
    id: int
    current_enrollment: int
    status: CourseStatus

    model_config = ConfigDict(from_attributes=True)
