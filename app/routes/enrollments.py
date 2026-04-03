from fastapi import APIRouter, HTTPException, Query, status

from app.database.mysql_connector import execute_query, get_db_connection
from app.middleware.logging import log_json

router = APIRouter(prefix="/api/enrollments", tags=["Enrollments"])


@router.get("")
def list_all_enrollments(status_filter: str | None = Query(default=None, alias="status")):
    query = """
        SELECT
            e.id,
            e.student_id,
            e.course_id,
            e.enrollment_date,
            e.grade,
            e.status,
            s.student_id AS student_code,
            CONCAT(s.first_name, ' ', s.last_name) AS student_name,
            s.email AS student_email,
            c.course_code,
            c.course_name
        FROM enrollments e
        JOIN students s ON s.id = e.student_id
        JOIN courses c ON c.id = e.course_id
        WHERE 1=1
    """
    params = []

    if status_filter:
        query += " AND e.status = %s"
        params.append(status_filter)

    query += " ORDER BY e.enrollment_date DESC"

    rows = execute_query(query, tuple(params), fetch_all=True) or []
    return {"success": True, "count": len(rows), "data": rows}


@router.post("", status_code=status.HTTP_201_CREATED)
def enroll_student(payload: dict):
    student_id = payload.get("student_id")
    course_id = payload.get("course_id")

    if not student_id or not course_id:
        raise HTTPException(status_code=400, detail="student_id and course_id are required")

    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            conn.start_transaction()

            cursor.execute(
                "SELECT id, first_name, last_name, status FROM students WHERE id = %s FOR UPDATE",
                (student_id,),
            )
            student = cursor.fetchone()
            if not student:
                raise HTTPException(status_code=404, detail="Student not found")
            if student["status"] != "active":
                raise HTTPException(status_code=400, detail="Only active students can be enrolled")

            cursor.execute(
                """
                SELECT id, course_name, course_code, max_capacity, current_enrollment, status
                FROM courses WHERE id = %s FOR UPDATE
                """,
                (course_id,),
            )
            course = cursor.fetchone()
            if not course:
                raise HTTPException(status_code=404, detail="Course not found")
            if course["status"] != "active":
                raise HTTPException(status_code=400, detail="Only active courses can accept enrollments")

            if int(course["current_enrollment"]) >= int(course["max_capacity"]):
                raise HTTPException(status_code=409, detail="Course is already at full capacity")

            cursor.execute(
                "SELECT id, status FROM enrollments WHERE student_id = %s AND course_id = %s",
                (student_id, course_id),
            )
            existing = cursor.fetchone()

            if existing:
                if existing["status"] == "dropped":
                    cursor.execute(
                        """
                        UPDATE enrollments
                        SET status = 'enrolled', grade = NULL, enrollment_date = CURRENT_TIMESTAMP
                        WHERE id = %s
                        """,
                        (existing["id"],),
                    )
                    enrollment_id = existing["id"]
                else:
                    raise HTTPException(status_code=409, detail="Student is already enrolled in this course")
            else:
                cursor.execute(
                    "INSERT INTO enrollments (student_id, course_id) VALUES (%s, %s)",
                    (student_id, course_id),
                )
                enrollment_id = cursor.lastrowid

            cursor.execute(
                """
                UPDATE courses
                SET current_enrollment = current_enrollment + 1
                WHERE id = %s
                """,
                (course_id,),
            )

            conn.commit()

            new_ratio = (int(course["current_enrollment"]) + 1) / int(course["max_capacity"])
            if new_ratio >= 0.80:
                log_json(
                    "warning",
                    "course_capacity_warning",
                    course_id=course_id,
                    course_code=course["course_code"],
                    utilization_percent=round(new_ratio * 100, 2),
                )

            log_json(
                "info",
                "student_enrolled",
                student_id=student_id,
                course_id=course_id,
                course_code=course["course_code"],
                student_name=f"{student['first_name']} {student['last_name']}",
            )

            cursor.execute(
                """
                SELECT
                    e.id,
                    e.student_id,
                    e.course_id,
                    e.enrollment_date,
                    e.grade,
                    e.status,
                    s.student_id AS student_code,
                    CONCAT(s.first_name, ' ', s.last_name) AS student_name,
                    c.course_code,
                    c.course_name
                FROM enrollments e
                JOIN students s ON s.id = e.student_id
                JOIN courses c ON c.id = e.course_id
                WHERE e.id = %s
                """,
                (enrollment_id,),
            )
            row = cursor.fetchone()
            return {"success": True, "message": "Enrollment created successfully", "data": row}
        except HTTPException:
            conn.rollback()
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


@router.delete("/{enrollment_id}")
def drop_enrollment(enrollment_id: int):
    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            conn.start_transaction()

            cursor.execute(
                """
                SELECT e.id, e.student_id, e.course_id, e.status, c.course_code
                FROM enrollments e
                JOIN courses c ON c.id = e.course_id
                WHERE e.id = %s FOR UPDATE
                """,
                (enrollment_id,),
            )
            enrollment = cursor.fetchone()
            if not enrollment:
                raise HTTPException(status_code=404, detail="Enrollment not found")

            if enrollment["status"] == "dropped":
                raise HTTPException(status_code=400, detail="Enrollment already dropped")

            cursor.execute(
                "UPDATE enrollments SET status = 'dropped' WHERE id = %s",
                (enrollment_id,),
            )
            cursor.execute(
                """
                UPDATE courses
                SET current_enrollment = GREATEST(current_enrollment - 1, 0)
                WHERE id = %s
                """,
                (enrollment["course_id"],),
            )

            conn.commit()

            log_json(
                "info",
                "enrollment_dropped",
                enrollment_id=enrollment_id,
                student_id=enrollment["student_id"],
                course_id=enrollment["course_id"],
                course_code=enrollment["course_code"],
            )

            return {"success": True, "message": "Enrollment dropped successfully"}
        except HTTPException:
            conn.rollback()
            raise
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


@router.get("/student/{student_id}")
def get_student_enrollments(student_id: int):
    student = execute_query(
        "SELECT id FROM students WHERE id = %s",
        (student_id,),
        fetch_one=True,
    )
    if not student:
        raise HTTPException(status_code=404, detail="Student not found")

    rows = execute_query(
        """
        SELECT
            e.id,
            e.student_id,
            e.course_id,
            e.enrollment_date,
            e.grade,
            e.status,
            c.course_code,
            c.course_name,
            c.credits
        FROM enrollments e
        JOIN courses c ON c.id = e.course_id
        WHERE e.student_id = %s
        ORDER BY e.enrollment_date DESC
        """,
        (student_id,),
        fetch_all=True,
    ) or []

    return {"success": True, "count": len(rows), "data": rows}


@router.get("/course/{course_id}")
def get_course_enrollments(course_id: int):
    course = execute_query(
        "SELECT id FROM courses WHERE id = %s",
        (course_id,),
        fetch_one=True,
    )
    if not course:
        raise HTTPException(status_code=404, detail="Course not found")

    rows = execute_query(
        """
        SELECT
            e.id,
            e.student_id,
            e.course_id,
            e.enrollment_date,
            e.grade,
            e.status,
            s.student_id AS student_code,
            CONCAT(s.first_name, ' ', s.last_name) AS student_name,
            s.email
        FROM enrollments e
        JOIN students s ON s.id = e.student_id
        WHERE e.course_id = %s
        ORDER BY e.enrollment_date DESC
        """,
        (course_id,),
        fetch_all=True,
    ) or []

    return {"success": True, "count": len(rows), "data": rows}


@router.put("/{enrollment_id}/grade")
def update_grade(enrollment_id: int, payload: dict):
    grade = payload.get("grade")
    if not grade:
        raise HTTPException(status_code=400, detail="grade is required")

    grade = grade.upper().strip()
    if grade not in {"A", "B", "C", "D", "F"}:
        raise HTTPException(status_code=400, detail="Grade must be one of: A, B, C, D, F")

    existing = execute_query(
        "SELECT id FROM enrollments WHERE id = %s",
        (enrollment_id,),
        fetch_one=True,
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Enrollment not found")

    execute_query(
        """
        UPDATE enrollments
        SET grade = %s,
            status = CASE WHEN status = 'enrolled' THEN 'completed' ELSE status END
        WHERE id = %s
        """,
        (grade, enrollment_id),
        commit=True,
    )

    updated = execute_query(
        """
        SELECT
            e.id,
            e.student_id,
            e.course_id,
            e.enrollment_date,
            e.grade,
            e.status,
            s.student_id AS student_code,
            CONCAT(s.first_name, ' ', s.last_name) AS student_name,
            c.course_code,
            c.course_name
        FROM enrollments e
        JOIN students s ON s.id = e.student_id
        JOIN courses c ON c.id = e.course_id
        WHERE e.id = %s
        """,
        (enrollment_id,),
        fetch_one=True,
    )
    return {"success": True, "message": "Grade updated successfully", "data": updated}
