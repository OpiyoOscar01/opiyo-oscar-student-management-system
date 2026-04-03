from fastapi import APIRouter, HTTPException, Query, status

from app.database.mysql_connector import execute_query

router = APIRouter(prefix="/api/courses", tags=["Courses"])


@router.get("")
def list_courses(
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(default=None),
):
    query = """
        SELECT id, course_code, course_name, credits, description,
               max_capacity, current_enrollment, status, created_at, updated_at
        FROM courses
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
                LOWER(course_code) LIKE %s
                OR LOWER(course_name) LIKE %s
            )
        """
        params.extend([term, term])

    query += " ORDER BY created_at DESC"

    rows = execute_query(query, tuple(params), fetch_all=True) or []
    return {"success": True, "count": len(rows), "data": rows}


@router.get("/{course_id}")
def get_course(course_id: int):
    row = execute_query(
        """
        SELECT id, course_code, course_name, credits, description,
               max_capacity, current_enrollment, status, created_at, updated_at
        FROM courses WHERE id = %s
        """,
        (course_id,),
        fetch_one=True,
    )
    if not row:
        raise HTTPException(status_code=404, detail="Course not found")
    return {"success": True, "data": row}


@router.post("", status_code=status.HTTP_201_CREATED)
def create_course(payload: dict):
    required = ["course_code", "course_name", "credits"]
    for field in required:
        if payload.get(field) in [None, ""]:
            raise HTTPException(status_code=400, detail=f"{field} is required")

    existing = execute_query(
        "SELECT id FROM courses WHERE course_code = %s",
        (payload["course_code"],),
        fetch_one=True,
    )
    if existing:
        raise HTTPException(status_code=409, detail="Course code already exists")

    execute_query(
        """
        INSERT INTO courses (course_code, course_name, credits, description, max_capacity)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (
            payload["course_code"],
            payload["course_name"],
            payload["credits"],
            payload.get("description"),
            payload.get("max_capacity", 30),
        ),
        commit=True,
    )

    created = execute_query(
        "SELECT * FROM courses WHERE course_code = %s",
        (payload["course_code"],),
        fetch_one=True,
    )
    return {"success": True, "message": "Course created successfully", "data": created}


@router.put("/{course_id}")
def update_course(course_id: int, payload: dict):
    existing = execute_query(
        "SELECT * FROM courses WHERE id = %s",
        (course_id,),
        fetch_one=True,
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Course not found")

    if payload.get("course_code"):
        course_code_exists = execute_query(
            "SELECT id FROM courses WHERE course_code = %s AND id != %s",
            (payload["course_code"], course_id),
            fetch_one=True,
        )
        if course_code_exists:
            raise HTTPException(status_code=409, detail="Course code already exists")

    if payload.get("max_capacity") is not None:
        if int(payload["max_capacity"]) < int(existing["current_enrollment"]):
            raise HTTPException(
                status_code=400,
                detail="max_capacity cannot be lower than current_enrollment",
            )

    allowed_fields = [
        "course_code",
        "course_name",
        "credits",
        "description",
        "max_capacity",
        "status",
    ]
    update_data = {k: v for k, v in payload.items() if k in allowed_fields}

    if not update_data:
        raise HTTPException(status_code=400, detail="No valid fields provided for update")

    set_clause = ", ".join([f"{key} = %s" for key in update_data.keys()])
    params = list(update_data.values()) + [course_id]

    execute_query(
        f"UPDATE courses SET {set_clause} WHERE id = %s",
        tuple(params),
        commit=True,
    )

    updated = execute_query(
        "SELECT * FROM courses WHERE id = %s",
        (course_id,),
        fetch_one=True,
    )
    return {"success": True, "message": "Course updated successfully", "data": updated}


@router.delete("/{course_id}")
def soft_delete_course(course_id: int):
    existing = execute_query(
        "SELECT id FROM courses WHERE id = %s",
        (course_id,),
        fetch_one=True,
    )
    if not existing:
        raise HTTPException(status_code=404, detail="Course not found")

    execute_query(
        "UPDATE courses SET status = 'inactive' WHERE id = %s",
        (course_id,),
        commit=True,
    )
    return {"success": True, "message": "Course marked as inactive"}
