"""
Scraper router - handles all web scraping endpoints
"""
from fastapi import APIRouter, BackgroundTasks
import logging
from pydantic import BaseModel
from scraper import BossScraper
from database import insert_jobs
from config import Config

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/scrape",
    tags=["scraper"]
)


class ScrapeRequest(BaseModel):
    keyword: str
    pages: int = 3
    city: str = None  # Single city (optional, for backward compatibility)
    cities: list[str] = None  # Multiple cities (optional)
    table: str = None  # Target table name (optional, uses default from config if not provided)

    def get_cities(self) -> list[str]:
        """Return list of cities to scrape."""
        if self.cities:
            return self.cities
        if self.city:
            return [self.city]
        return ["101210700"]  # Default to Wuxi

    def get_table(self) -> str:
        """Return table name to use."""
        return self.table or Config.INSERT_JOBS_TABLE


def run_scraper_task(keyword: str, pages: int, cities: list[str], table: str):
    """Background task to run the scraper"""
    logger.info(f"Starting background scrape task for '{keyword}' with {pages} pages across {len(cities)} cities: {cities}, table: {table}")
    total_jobs = 0
    total_by_city = {}

    try:
        scraper = BossScraper()
        for city_code in cities:
            logger.info(f"Starting scrape for city: {city_code}")
            city_jobs = 0

            # Returns a generator now, need to iterate
            for jobs_chunk in scraper.scrape_keyword(keyword, pages, city_code):
                if jobs_chunk:
                    insert_jobs(jobs_chunk, table=table)
                    chunk_count = len(jobs_chunk)
                    total_jobs += chunk_count
                    city_jobs += chunk_count
                    logger.info(f"[{city_code}] Saved chunk of {chunk_count} jobs to table '{table}'. City total: {city_jobs}")
                else:
                    logger.debug(f"[{city_code}] Empty chunk yielded.")

            total_by_city[city_code] = city_jobs
            logger.info(f"City {city_code} completed. Jobs saved: {city_jobs}")

        logger.info(f"All tasks completed. Total saved: {total_jobs} to table '{table}'. By city: {total_by_city}")
    except Exception as e:
        logger.error(f"Background task failed: {e}")


@router.post("/")
async def trigger_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Trigger a scrape task.
    Supports single city (city) or multiple cities (cities).
    Supports dynamic table name via 'table' parameter.
    """
    cities = request.get_cities()
    table = request.get_table()
    background_tasks.add_task(run_scraper_task, request.keyword, request.pages, cities, table)
    return {
        "message": f"Scraper started for keyword: {request.keyword}",
        "cities": cities,
        "pages": request.pages,
        "table": table,
        "status": "processing"
    }
