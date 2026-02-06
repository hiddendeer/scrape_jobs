from typing import List, Optional
import pymysql
import logging
import json
from datetime import datetime
from config import Config

logger = logging.getLogger(__name__)

def get_connection():
    # 验证必需的数据库配置参数
    required_configs = {
        'DB_HOST': Config.DB_HOST,
        'DB_USER': Config.DB_USER,
        'DB_PASSWORD': Config.DB_PASSWORD,
        'DB_NAME': Config.DB_NAME
    }

    missing = [k for k, v in required_configs.items() if v is None]
    if missing:
        raise ValueError(
            f"数据库配置不完整，缺少以下环境变量: {', '.join(missing)}. "
            f"请检查 .env 文件或环境变量设置。"
        )

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
    """初始化数据库表"""
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # 检查表是否已存在
            cursor.execute(f"SHOW TABLES LIKE '{Config.INSERT_JOBS_TABLE}'")
            result = cursor.fetchone()

            if result:
                logger.info(f"Table '{Config.INSERT_JOBS_TABLE}' already exists.")
                return

            # 创建 agent_jobs 表
            create_table_sql = f"""
            CREATE TABLE {Config.INSERT_JOBS_TABLE} (
                id INT AUTO_INCREMENT PRIMARY KEY,
                job_id VARCHAR(100) UNIQUE,
                job_name VARCHAR(255),
                company_name VARCHAR(255),
                city VARCHAR(100),
                district VARCHAR(100),
                salary_raw VARCHAR(100),
                salary_min INT,
                salary_max INT,
                salary_avg INT,
                salary_months INT,
                experience_raw VARCHAR(100),
                exp_min INT,
                exp_max INT,
                education VARCHAR(100),
                skills_tags TEXT,
                job_desc TEXT,
                detail_url VARCHAR(500),
                scraped_time DATETIME,
                is_deleted TINYINT DEFAULT 0,
                INDEX idx_job_id (job_id),
                INDEX idx_city (city),
                INDEX idx_is_deleted (is_deleted)
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
            """
            cursor.execute(create_table_sql)
            conn.commit()
            logger.info(f"Database table '{Config.INSERT_JOBS_TABLE}' created successfully.")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

def insert_jobs(jobs, table: Optional[str] = None):
    if not jobs:
        return

    target_table = table or Config.INSERT_JOBS_TABLE
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Updated SQL to match new schema
            sql = f"""
            INSERT INTO {target_table} (
                job_id, job_name, company_name, city, district,
                salary_raw, salary_min, salary_max, salary_avg, salary_months,
                experience_raw, exp_min, exp_max,
                education, skills_tags, job_desc, detail_url, scraped_time
            ) VALUES (
                %(job_id)s, %(job_name)s, %(company_name)s, %(city)s, %(district)s,
                %(salary_raw)s, %(salary_min)s, %(salary_max)s, %(salary_avg)s, %(salary_months)s,
                %(experience_raw)s, %(exp_min)s, %(exp_max)s,
                %(education)s, %(skills_tags)s, %(job_desc)s, %(detail_url)s, %(scraped_time)s
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
                job_desc = VALUES(job_desc),
                detail_url = VALUES(detail_url),
                scraped_time = VALUES(scraped_time)
            """

            # Prepare data first
            prepared_jobs = []
            for job in jobs:
                job_copy = job.copy()
                if isinstance(job_copy.get('skills_tags'), list):
                    job_copy['skills_tags'] = json.dumps(job_copy['skills_tags'], ensure_ascii=False)
                job_copy['scraped_time'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                prepared_jobs.append(job_copy)

            # Direct insertion without pre-checking name/company duplicates
            # We still use ON DUPLICATE KEY UPDATE to handle job_id conflicts safely
            cursor.executemany(sql, prepared_jobs)
            conn.commit()
            logger.info(f"Inserted/Updated {len(jobs)} jobs into table '{target_table}'.")

    except Exception as e:
        logger.error(f"Error inserting jobs: {e}")
        conn.rollback()
    finally:
        conn.close()

def get_jobs_info(table: Optional[str] = None):
    target_table = table or Config.QUERY_JOBS_TABLE
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = f"SELECT * FROM {target_table}"
            cursor.execute(sql)
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting jobs info: {e}")
    finally:
        conn.close()

def get_agent_jobs_info(table: Optional[str] = None):
    target_table = table or Config.INSERT_JOBS_TABLE
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            sql = f"SELECT * FROM {target_table}"
            cursor.execute(sql)
            return cursor.fetchall()
    except Exception as e:
        logger.error(f"Error getting jobs info: {e}")
    finally:
        conn.close()

def handle_job_info(job_ids: List[str], table: Optional[str] = None):
    if not job_ids:
        return
    target_table = table or Config.QUERY_JOBS_TABLE
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Use format to generate correct number of placeholders
            format_strings = ','.join(['%s'] * len(job_ids))
            sql = f"UPDATE {target_table} SET is_deleted = 1 WHERE job_id IN ({format_strings})"
            cursor.execute(sql, tuple(job_ids))
            conn.commit()
            logger.info(f"Deleted {len(job_ids)} jobs from table '{target_table}'.")
    except Exception as e:
        logger.error(f"Error deleting jobs: {e}")
        conn.rollback()
    finally:
        conn.close()

def handle_agent_job_info(job_ids: List[str], table: Optional[str] = None):
    if not job_ids:
        return
    target_table = table or Config.INSERT_JOBS_TABLE
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Use format to generate correct number of placeholders
            format_strings = ','.join(['%s'] * len(job_ids))
            sql = f"UPDATE {target_table} SET is_deleted = 1 WHERE job_id IN ({format_strings})"
            cursor.execute(sql, tuple(job_ids))
            conn.commit()
            logger.info(f"Marked {len(job_ids)} agent jobs as deleted in table '{target_table}'.")
    except Exception as e:
        logger.error(f"Error updating agent jobs: {e}")
        conn.rollback()
    finally:
        conn.close()

def mark_non_ai_jobs_deleted(table: Optional[str] = None) -> int:
    """
    Mark jobs as deleted where job_name and job_desc don't contain 'ai'.

    Args:
        table: Target table name (optional, uses default from config if not provided)

    Returns:
        Number of rows affected
    """
    target_table = table or Config.INSERT_JOBS_TABLE
    conn = get_connection()
    try:
        with conn.cursor() as cursor:
            # Update jobs where neither job_name nor job_desc contains 'ai' (case-insensitive)
            sql = f"""
            UPDATE {target_table}
            SET is_deleted = 1
            WHERE is_deleted = 0
              AND (job_name IS NULL OR job_name NOT LIKE '%ai%')
              AND (job_desc IS NULL OR job_desc NOT LIKE '%ai%')
            """
            cursor.execute(sql)
            affected_rows = cursor.rowcount
            conn.commit()
            logger.info(f"Marked {affected_rows} non-AI jobs as deleted in table '{target_table}'.")
            return affected_rows
    except Exception as e:
        logger.error(f"Error marking non-AI jobs as deleted: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()
