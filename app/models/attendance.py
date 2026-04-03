from datetime import date
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class AttendanceStatus(str, Enum):
    present = "present"
    absent = "absent"
    late = "late"
    excused = "excused"


class AttendanceCreate(BaseModel):
    student_id: int = Field(..., gt=0)
    course_id: int = Field(..., gt=0)
    attendance_date: date
    status: AttendanceStatus = AttendanceStatus.present
    notes: Optional[str] = None
