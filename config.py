import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Database Configuration
    DB_HOST = os.getenv("DB_HOST")
    DB_PORT = int(os.getenv("DB_PORT", 3306))
    DB_USER = os.getenv("DB_USER")
    DB_PASSWORD = os.getenv("DB_PASSWORD")
    DB_NAME = os.getenv("DB_NAME")

    # Table Configuration
    INSERT_JOBS_TABLE = os.getenv("INSERT_JOBS_TABLE", "agent_jobs")
    QUERY_JOBS_TABLE = os.getenv("QUERY_JOBS_TABLE", "ems_jobs_new")

    # Scraper Configuration
    CHROME_PORT = 9222
