from fastapi import APIRouter, HTTPException, Query, status

from app.database.mysql_connector import execute_query, get_db_connection

router = APIRouter(prefix="/api/students", tags=["Students"])


def generate_student_code(conn) -> str:
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("SELECT COALESCE(MAX(id), 0) AS max_id FROM students")
        row = cursor.fetchone()
        next_id = (row["max_id"] or 0) + 1
        return f"STU-{next_id:03d}"
    finally:
        cursor.close()


@router.get("")
def list_students(
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
):
    query = """
        SELECT id, student_id, first_name, last_name, email, phone,
               date_of_birth, enrollment_date, status, created_at, updated_at
        FROM students
        WHERE 1=1
    """
    params = []

    if status_filter:
        query += " AND status = %s"
        params.append(status_filter)

    if search:
        term = f"%{search.lower()}%"
        query += """
            AND (
                LOWER(first_name) LIKE %s
                OR LOWER(last_name) LIKE %s
                OR LOWER(email) LIKE %s
                OR LOWER(student_id) LIKE %s
            )
        """
        params.extend([term, term, term, term])

    query += " ORDER BY created_at DESC"

    rows = execute_query(query, tuple(params), fetch_all=True) or []
    return {"success": True, "count": len(rows), "data": rows}


@router.get("/{student_id}")
def get_student(student_id: int):
    row = execute_query(
        """
        SELECT id, student_id, first_name, last_name, email, phone,
               date_of_birth, enrollment_date, status, created_at, updated_at
        FROM students
        WHERE id = %s
        """,
        (student_id,),
        fetch_one=True,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Student not found")
    return {"success": True, "data": row}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_student(payload: dict):
    required = ["first_name", "last_name", "email"]
    for field in required:
        if not payload.get(field):
            raise HTTPException(status_code=400, detail=f"{field} is required")

    email_exists = execute_query(
        "SELECT id FROM students WHERE email = %s",
        (payload["email"],),
        fetch_one=True,
    )
    if email_exists:
        raise HTTPException(status_code=409, detail="Email already exists")

    with get_db_connection() as conn:
        cursor = conn.cursor(dictionary=True)
        try:
            student_code = generate_student_code(conn)

            cursor.execute(
                """
                INSERT INTO students (student_id, first_name, last_name, email, phone, date_of_birth)
                VALUES (%s, %s, %s, %s, %s, %s)
                """,
                (
                    student_code,
                    payload["first_name"],
                    payload["last_name"],
                    payload["email"],
                    payload.get("phone"),
                    payload.get("date_of_birth"),
                ),
            )
            student_pk = cursor.lastrowid
            conn.commit()

            cursor.execute(
                """
                SELECT id, student_id, first_name, last_name, email, phone,
                       date_of_birth, enrollment_date, status, created_at, updated_at
                FROM students WHERE id = %s
                """,
                (student_pk,),
            )
            created = cursor.fetchone()
            return {"success": True, "message": "Student created successfully", "data": created}
        except Exception:
            conn.rollback()
            raise
        finally:
            cursor.close()


@router.put("/{student_id}")
def update_student(student_id: int, payload: dict):
    existing = execute_query(
        "SELECT * FROM students WHERE id = %s",
        (student_id,),
        fetch_one=True,
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Student not found")

    if payload.get("email"):
        email_exists = execute_query(
            "SELECT id FROM students WHERE email = %s AND id != %s",
            (payload["email"], student_id),
            fetch_one=True,
        )
        if email_exists:
            raise HTTPException(status_code=409, detail="Email already exists")

    allowed_fields = [
        "first_name",
        "last_name",
        "email",
        "phone",
        "date_of_birth",
        "status",
    ]
    update_data = {k: v for k, v in payload.items() if k in allowed_fields}

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields provided for update")

    set_clause = ", ".join([f"{key} = %s" for key in update_data.keys()])
    params = list(update_data.values()) + [student_id]

    execute_query(
        f"UPDATE students SET {set_clause} WHERE id = %s",
        tuple(params),
        commit=True,
    )

    updated = execute_query(
        """
        SELECT id, student_id, first_name, last_name, email, phone,
               date_of_birth, enrollment_date, status, created_at, updated_at
        FROM students WHERE id = %s
        """,
        (student_id,),
        fetch_one=True,
    )
    return {"success": True, "message": "Student updated successfully", "data": updated}


@router.delete("/{student_id}")
def soft_delete_student(student_id: int):
    existing = execute_query(
        "SELECT id, status FROM students WHERE id = %s",
        (student_id,),
        fetch_one=True,
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Student not found")

    execute_query(
        "UPDATE students SET status = 'inactive' WHERE id = %s",
        (student_id,),
        commit=True,
    )
    return {"success": True, "message": "Student marked as inactive"}


@router.get("/{student_id}/courses")
def get_student_courses(student_id: int):
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
            e.id AS enrollment_id,
            e.status AS enrollment_status,
            e.grade,
            e.enrollment_date,
            c.id AS course_id,
            c.course_code,
            c.course_name,
            c.credits,
            c.description,
            c.max_capacity,
            c.current_enrollment
        FROM enrollments e
        JOIN courses c ON c.id = e.course_id
        WHERE e.student_id = %s
        ORDER BY e.enrollment_date DESC
        """,
        (student_id,),
        fetch_all=True,
    ) or []

    return {"success": True, "count": len(rows), "data": rows}
