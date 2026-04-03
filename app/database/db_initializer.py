from app.config import settings
from app.database.mysql_connector import get_db_connection
from app.middleware.logging import app_logger, log_json



SCHEMA_SQL = [
    """
    CREATE TABLE IF NOT EXISTS students (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_id VARCHAR(20) UNIQUE NOT NULL,
        first_name VARCHAR(100) NOT NULL,
        last_name VARCHAR(100) NOT NULL,
        email VARCHAR(255) UNIQUE NOT NULL,
        phone VARCHAR(20),
        date_of_birth DATE,
        enrollment_date DATE DEFAULT (CURRENT_DATE),
        status ENUM('active', 'inactive', 'graduated', 'suspended') DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_email (email),
        INDEX idx_student_id (student_id),
        INDEX idx_status (status)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS courses (
        id INT AUTO_INCREMENT PRIMARY KEY,
        course_code VARCHAR(20) UNIQUE NOT NULL,
        course_name VARCHAR(255) NOT NULL,
        credits INT NOT NULL CHECK (credits BETWEEN 1 AND 6),
        description TEXT,
        max_capacity INT NOT NULL DEFAULT 30,
        current_enrollment INT NOT NULL DEFAULT 0,
        status ENUM('active', 'inactive') DEFAULT 'active',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
        INDEX idx_course_code (course_code),
        INDEX idx_status (status)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS enrollments (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_id INT NOT NULL,
        course_id INT NOT NULL,
        enrollment_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        grade VARCHAR(2) DEFAULT NULL,
        status ENUM('enrolled', 'dropped', 'completed') DEFAULT 'enrolled',
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
        UNIQUE KEY unique_enrollment (student_id, course_id),
        INDEX idx_student (student_id),
        INDEX idx_course (course_id),
        INDEX idx_status (status)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS attendance (
        id INT AUTO_INCREMENT PRIMARY KEY,
        student_id INT NOT NULL,
        course_id INT NOT NULL,
        attendance_date DATE NOT NULL,
        status ENUM('present', 'absent', 'late', 'excused') DEFAULT 'present',
        notes TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        FOREIGN KEY (course_id) REFERENCES courses(id) ON DELETE CASCADE,
        UNIQUE KEY unique_attendance (student_id, course_id, attendance_date),
        INDEX idx_student (student_id),
        INDEX idx_date (attendance_date)
    )
    """,
]

SEED_SQL = [
    """
    INSERT INTO students (student_id, first_name, last_name, email, phone, date_of_birth, status)
    VALUES
        ('STU-001', 'John', 'Doe', 'john.doe@example.com', '555-0101', '2000-05-15', 'active'),
        ('STU-002', 'Jane', 'Smith', 'jane.smith@example.com', '555-0102', '2001-08-22', 'active'),
        ('STU-003', 'Mike', 'Johnson', 'mike.j@example.com', '555-0103', '1999-11-30', 'active')
    ON DUPLICATE KEY UPDATE
        first_name = VALUES(first_name),
        last_name = VALUES(last_name),
        phone = VALUES(phone),
        date_of_birth = VALUES(date_of_birth),
        status = VALUES(status)
    """,
    """
    INSERT INTO courses (course_code, course_name, credits, description, max_capacity, current_enrollment, status)
    VALUES
        ('CS101', 'Introduction to Programming', 3, 'Learn programming basics with Python', 30, 0, 'active'),
        ('CS102', 'Data Structures', 4, 'Advanced data structures and algorithms', 25, 0, 'active'),
        ('MATH101', 'Calculus I', 4, 'Differential and integral calculus', 35, 0, 'active'),
        ('ENG101', 'English Composition', 3, 'Academic writing and research', 30, 0, 'active')
    ON DUPLICATE KEY UPDATE
        course_name = VALUES(course_name),
        credits = VALUES(credits),
        description = VALUES(description),
        max_capacity = VALUES(max_capacity),
        status = VALUES(status)
    """,
]


def initialize_database():
    """
    Creates all required tables automatically when the application starts.
    Safe to run multiple times because it uses IF NOT EXISTS and UPSERT-style seeding.
    """
    with get_db_connection() as conn:
        cursor = conn.cursor()
        try:
            for statement in SCHEMA_SQL:
                cursor.execute(statement)

            if settings.AUTO_SEED_ON_STARTUP:
                for statement in SEED_SQL:
                    cursor.execute(statement)


            conn.commit()

            log_json(
                "info",
                "database_initialized",
                message="Database tables verified/created successfully on startup"
            )
        except Exception as exc:
            conn.rollback()
            app_logger.exception(
                {
                    "event": "database_initialization_failed",
                    "error": str(exc),
                }
            )
            raise
        finally:
            cursor.close()
