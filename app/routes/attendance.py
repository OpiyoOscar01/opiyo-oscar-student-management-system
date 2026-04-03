from fastapi import APIRouter, HTTPException, Query, status

from app.database.mysql_connector import execute_query

router = APIRouter(prefix="/api/attendance", tags=["Attendance"])


@router.post("", status_code=status.HTTP_201_CREATED)
def mark_attendance(payload: dict):
    student_id = payload.get("student_id")
    course_id = payload.get("course_id")
    attendance_date = payload.get("attendance_date")
    attendance_status = payload.get("status", "present")
    notes = payload.get("notes")

    if not student_id or not course_id or not attendance_date:
        raise HTTPException(
            status_code=400,
            detail="student_id, course_id and attendance_date are required",
        )

    if attendance_status not in {"present", "absent", "late", "excused"}:
        raise HTTPException(status_code=400, detail="Invalid attendance status")

    enrollment = execute_query(
        """
        SELECT id FROM enrollments
        WHERE student_id = %s AND course_id = %s AND status IN ('enrolled', 'completed')
        """,
        (student_id, course_id),
        fetch_one=True,
    )
    if not enrollment:
        raise HTTPException(status_code=400, detail="Student is not enrolled in the selected course")

    execute_query(
        """
        INSERT INTO attendance (student_id, course_id, attendance_date, status, notes)
        VALUES (%s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
            status = VALUES(status),
            notes = VALUES(notes)
        """,
        (student_id, course_id, attendance_date, attendance_status, notes),
        commit=True,
    )

    row = execute_query(
        """
        SELECT
            a.id,
            a.student_id,
            a.course_id,
            a.attendance_date,
            a.status,
            a.notes,
            a.created_at
        FROM attendance a
        WHERE a.student_id = %s AND a.course_id = %s AND a.attendance_date = %s
        """,
        (student_id, course_id, attendance_date),
        fetch_one=True,
    )
    return {"success": True, "message": "Attendance recorded successfully", "data": row}


@router.get("/student/{student_id}")
def get_student_attendance(
    student_id: int,
    course_id: int | None = Query(default=None),
):
    student = execute_query(
        "SELECT id FROM students WHERE id = %s",
        (student_id,),
        fetch_one=True,
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    query = """
        SELECT
            a.id,
            a.student_id,
            a.course_id,
            a.attendance_date,
            a.status,
            a.notes,
            c.course_code,
            c.course_name
        FROM attendance a
        JOIN courses c ON c.id = a.course_id
        WHERE a.student_id = %s
    """
    params = [student_id]

    if course_id:
        query += " AND a.course_id = %s"
        params.append(course_id)

    query += " ORDER BY a.attendance_date DESC"

    rows = execute_query(query, tuple(params), fetch_all=True) or []
    return {"success": True, "count": len(rows), "data": rows}


@router.get("/course/{course_id}")
def get_course_attendance(
    course_id: int,
    attendance_date: str | None = Query(default=None),
):
    course = execute_query(
        "SELECT id FROM courses WHERE id = %s",
        (course_id,),
        fetch_one=True,
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    query = """
        SELECT
            a.id,
            a.student_id,
            a.course_id,
            a.attendance_date,
            a.status,
            a.notes,
            s.student_id AS student_code,
            CONCAT(s.first_name, ' ', s.last_name) AS student_name
        FROM attendance a
        JOIN students s ON s.id = a.student_id
        WHERE a.course_id = %s
    """
    params = [course_id]

    if attendance_date:
        query += " AND a.attendance_date = %s"
        params.append(attendance_date)

    query += " ORDER BY a.attendance_date DESC, student_name ASC"

    rows = execute_query(query, tuple(params), fetch_all=True) or []
    return {"success": True, "count": len(rows), "data": rows}
