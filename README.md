# Student Management System

A complete, production-ready **Student Management System** built with:

- **Backend:** FastAPI (Python 3.11)
- **Database:** MySQL 8.0
- **Frontend:** Responsive HTML/CSS/JavaScript
- **Deployment:** Railway
- **Containerization:** Docker
- **Local Development:** Docker Compose

---

## Student / Developer Details

- **Name:** Opiyo Oscar
- **Student Number:** 2300701330
- **Reg Number:** 23/U/1330
- **Institution:** Makerere University
- **Programme Context:** Software Engineering Student

---

## Features

### Students
- Create student
- List students
- Search students by name/email
- Update student
- Soft delete student
- View student courses

### Courses
- Create course
- List courses
- Search courses by code/name
- Update course
- Soft delete course

### Enrollments
- Enroll a student in a course
- Prevent duplicate enrollments
- Capacity checks
- Drop enrollment with transaction support
- Update student grade

### Attendance
- Mark attendance
- View attendance by student
- View attendance by course

### Dashboard / Monitoring
- Total students
- Active courses
- Total enrollments
- Average attendance rate
- Recent enrollments
- Course enrollment chart
- `/health` endpoint
- `/metrics` endpoint

---

## Project Structure

```bash
student-management-system/
├── app/
│   ├── __init__.py
│   ├── main.py
│   ├── config.py
│   ├── database/
│   │   ├── __init__.py
│   │   └── mysql_connector.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── students.py
│   │   ├── courses.py
│   │   ├── enrollments.py
│   │   ├── attendance.py
│   │   └── dashboard.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── student.py
│   │   ├── course.py
│   │   ├── enrollment.py
│   │   └── attendance.py
│   ├── middleware/
│   │   ├── __init__.py
│   │   └── logging.py
│   └── static/
│       └── index.html
├── requirements.txt
├── Dockerfile
├── railway.json
├── docker-compose.yml
├── init_db.sql
├── .env.example
├── .gitignore
├── .dockerignore
└── README.md
