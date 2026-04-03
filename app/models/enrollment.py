from typing import Optional

from pydantic import BaseModel, Field, field_validator


class EnrollmentCreate(BaseModel):
    student_id: int = Field(..., gt=0)
    course_id: int = Field(..., gt=0)


class GradeUpdate(BaseModel):
    grade: Optional[str] = Field(default=None, max_length=2)

    @field_validator("grade")
    @classmethod
    def validate_grade(cls, value):
        if value is None:
            return value
        value = value.upper().strip()
        allowed = {"A", "B", "C", "D", "F"}
        if value not in allowed:
            raise ValueError("Grade must be one of: A, B, C, D, F")
        return value
