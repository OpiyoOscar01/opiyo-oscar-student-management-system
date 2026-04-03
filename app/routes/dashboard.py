import os
import time

import psutil
from fastapi import APIRouter
from fastapi.responses import JSONResponse

from app.database.mysql_connector import execute_query, get_pool_status, ping_database
from app.middleware.logging import get_request_count

router = APIRouter(tags=["Dashboard"])


@router.get("/api/dashboard/stats")
def get_dashboard_stats():
    total_students = execute_query(
        "SELECT COUNT(*) AS count FROM students",
        fetch_one=True,
    )["count"]

    active_courses = execute_query(
        "SELECT COUNT(*) AS count FROM courses WHERE status = 'active'",
        fetch_one=True,
    )["count"]

    total_enrollments = execute_query(
        "SELECT COUNT(*) AS count FROM enrollments WHERE status = 'enrolled'",
        fetch_one=True,
    )["count"]

    attendance_rate = execute_query(
        """
        SELECT
            ROUND(
                COALESCE(
                    (
                        SUM(CASE WHEN status IN ('present', 'late', 'excused') THEN 1 ELSE 0 END)
                        / NULLIF(COUNT(*), 0)
                    ) * 100,
                    0
                ),
                2
            ) AS rate
        FROM attendance
        """,
        fetch_one=True,
    )["rate"]

    recent_enrollments = execute_query(
        """
        SELECT
            e.id,
            CONCAT(s.first_name, ' ', s.last_name) AS student_name,
            c.course_name,
            c.course_code,
            e.enrollment_date,
            e.status
        FROM enrollments e
        JOIN students s ON s.id = e.student_id
        JOIN courses c ON c.id = e.course_id
        ORDER BY e.enrollment_date DESC
        LIMIT 5
        """,
        fetch_all=True,
    ) or []

    course_chart = execute_query(
        """
        SELECT
            c.id,
            c.course_code,
            c.course_name,
            c.current_enrollment,
            c.max_capacity
        FROM courses c
        WHERE c.status = 'active'
        ORDER BY c.course_code ASC
        """,
        fetch_all=True,
    ) or []

    return {
        "success": True,
        "data": {
            "total_students": total_students,
            "active_courses": active_courses,
            "total_enrollments": total_enrollments,
            "avg_attendance_rate": attendance_rate or 0,
            "recent_enrollments": recent_enrollments,
            "course_chart": course_chart,
        },
    }


@router.get("/metrics")
def get_metrics():
    process = psutil.Process(os.getpid())

    cpu_percent = psutil.cpu_percent(interval=0.3)
    memory_info = process.memory_info()
    virtual_memory = psutil.virtual_memory()

    active_enrollments = execute_query(
        "SELECT COUNT(*) AS count FROM enrollments WHERE status = 'enrolled'",
        fetch_one=True,
    )["count"]

    return {
        "success": True,
        "data": {
            "cpu_usage_percent": cpu_percent,
            "memory_rss_mb": round(memory_info.rss / (1024 * 1024), 2),
            "system_memory_percent": virtual_memory.percent,
            "database_pool": get_pool_status(),
            "total_requests_served": get_request_count(),
            "active_enrollments": active_enrollments,
            "timestamp": int(time.time()),
        },
    }


@router.get("/api/dashboard/recent-enrollments")
def recent_enrollments():
    rows = execute_query(
        """
        SELECT
            e.id,
            CONCAT(s.first_name, ' ', s.last_name) AS student_name,
            c.course_name,
            c.course_code,
            e.enrollment_date,
            e.status
        FROM enrollments e
        JOIN students s ON s.id = e.student_id
        JOIN courses c ON c.id = e.course_id
        ORDER BY e.enrollment_date DESC
        LIMIT 5
        """,
        fetch_all=True,
    ) or []

    return {"success": True, "data": rows}


@router.get("/api/dashboard/db-status")
def db_status():
    return JSONResponse(
        status_code=200 if ping_database() else 503,
        content={
            "success": ping_database(),
            "database": "up" if ping_database() else "down",
            "pool": get_pool_status(),
        },
    )
