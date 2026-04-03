import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    APP_NAME = os.getenv("APP_NAME", "Student Management System")
    APP_VERSION = os.getenv("APP_VERSION", "1.0.0")
    APP_ENV = os.getenv("APP_ENV", "development")
    DEBUG = os.getenv("DEBUG", "false").lower() == "true"

    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8000"))

    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

    # Railway automatically injects MYSQLHOST, MYSQLPORT, MYSQLUSER, MYSQLPASSWORD, MYSQLDATABASE
    MYSQL_HOST = os.getenv("MYSQLHOST", os.getenv("MYSQL_HOST", "localhost"))
    MYSQL_PORT = int(os.getenv("MYSQLPORT", os.getenv("MYSQL_PORT", "3306")))
    MYSQL_USER = os.getenv("MYSQLUSER", os.getenv("MYSQL_USER", "root"))
    MYSQL_PASSWORD = os.getenv("MYSQLPASSWORD", os.getenv("MYSQL_PASSWORD", "password"))
    MYSQL_DATABASE = os.getenv("MYSQLDATABASE", os.getenv("MYSQL_DATABASE", "student_management"))

    MYSQL_POOL_NAME = os.getenv("MYSQL_POOL_NAME", "sms_pool")
    MYSQL_POOL_SIZE = int(os.getenv("MYSQL_POOL_SIZE", "5"))
    MYSQL_POOL_RESET_SESSION = os.getenv("MYSQL_POOL_RESET_SESSION", "true").lower() == "true"
    MYSQL_CONNECT_TIMEOUT = int(os.getenv("MYSQL_CONNECT_TIMEOUT", "10"))
    MYSQL_MAX_RETRIES = int(os.getenv("MYSQL_MAX_RETRIES", "3"))
    MYSQL_RETRY_DELAY_SECONDS = float(os.getenv("MYSQL_RETRY_DELAY_SECONDS", "1.5"))

    CORS_ORIGINS = [
        origin.strip()
        for origin in os.getenv("CORS_ORIGINS", "*").split(",")
        if origin.strip()
    ]

    API_PREFIX = "/api"

    # ============================================================
    # SCALABILITY / ASSIGNMENT DOCUMENTATION
    # ============================================================
    # 1. Railway pricing awareness:
    #    Railway usage pricing is commonly discussed in terms of compute
    #    consumption, such as approximately $0.000145 per vCPU-second,
    #    plus memory and other service costs depending on plan/usage.
    #
    # 2. Horizontal scaling:
    #    For read-heavy workloads, increase replicas in Railway so multiple
    #    app containers can serve traffic concurrently. Good for dashboard
    #    reads, student listing, and reporting endpoints.
    #
    # 3. Vertical scaling:
    #    Increase CPU and memory from the Railway dashboard if the single
    #    instance starts throttling or response times rise under load.
    #
    # 4. Database optimization:
    #    This project uses:
    #      - MySQL indexes
    #      - connection pooling
    #      - transaction control
    #      - selective queries
    #    These reduce latency and improve concurrency.
    #
    # 5. Caching strategy:
    #    Add Redis for frequently requested data such as student lists,
    #    course catalog lookups, and dashboard summary cards.
    #
    # 6. Read replicas:
    #    Use read replicas for reporting queries like attendance analytics,
    #    historical summaries, and professor dashboards, while writes stay
    #    on the primary DB node.
    #
    # 7. Cost optimization:
    #    Set realistic memory/CPU limits, keep one replica for class demos,
    #    and use lower-cost environments for development/testing.
    #
    # 8. Auto-scaling triggers:
    #    A reasonable policy would be to scale when:
    #      - CPU usage > 70%
    #      - request volume > 1000 requests/minute
    #      - latency significantly rises during peak usage
    # ============================================================


settings = Settings()
