import pymysql
import logging
import json
from config import Config

logger = logging.getLogger(__name__)

def get_connection():
    return pymysql.connect(
        host=Config.DB_HOST,
        port=Config.DB_PORT,
        user=Config.DB_USER,
        password=Config.DB_PASSWORD,
        database=Config.DB_NAME,
        charset='utf8mb4',
        cursorclass=pymysql.cursors.DictCursor
    )

def init_db():
    # Since user provided schema is already active, we might skip creation or just log.
    # But for safety, we keep connection check.
    pass

def insert_jobs(jobs):
    if not jobs:
        return
    
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Updated SQL to match new schema
            sql = """
            INSERT INTO ems_jobs (
                job_id, job_name, company_name, city, district,
                salary_raw, salary_min, salary_max, salary_avg, salary_months,
                experience_raw, exp_min, exp_max, 
                education, skills_tags, detail_url
            ) VALUES (
                %(job_id)s, %(job_name)s, %(company_name)s, %(city)s, %(district)s,
                %(salary_raw)s, %(salary_min)s, %(salary_max)s, %(salary_avg)s, %(salary_months)s,
                %(experience_raw)s, %(exp_min)s, %(exp_max)s,
                %(education)s, %(skills_tags)s, %(detail_url)s
            )
            ON DUPLICATE KEY UPDATE
                job_name = VALUES(job_name),
                company_name = VALUES(company_name),
                city = VALUES(city),
                district = VALUES(district),
                salary_raw = VALUES(salary_raw),
                salary_min = VALUES(salary_min),
                salary_max = VALUES(salary_max),
                salary_avg = VALUES(salary_avg),
                salary_months = VALUES(salary_months),
                experience_raw = VALUES(experience_raw),
                exp_min = VALUES(exp_min),
                exp_max = VALUES(exp_max),
                education = VALUES(education),
                skills_tags = VALUES(skills_tags),
                detail_url = VALUES(detail_url)
            """
            
            # Prepare data first
            prepared_jobs = []
            for job in jobs:
                job_copy = job.copy()
                if isinstance(job_copy.get('skills_tags'), list):
                    job_copy['skills_tags'] = json.dumps(job_copy['skills_tags'], ensure_ascii=False)
                prepared_jobs.append(job_copy)

            # Direct insertion without pre-checking name/company duplicates
            # We still use ON DUPLICATE KEY UPDATE to handle job_id conflicts safely
            cursor.executemany(sql, prepared_jobs)
            conn.commit()
            logger.info(f"Inserted/Updated {len(jobs)} jobs.")

    except Exception as e:
        logger.error(f"Error inserting jobs: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_jobs_info():
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = "SELECT * FROM ems_jobs"
            cursor.execute(sql)
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting jobs info: {e}")
    finally:
        conn.close()
