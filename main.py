from fastapi import FastAPI, BackgroundTasks, HTTPException
import logging
from pydantic import BaseModel
from scraper import BossScraper
from database import init_db, insert_jobs

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(title="Boss Zhipin Scraper API")

# Initialize DB on startup
@app.on_event("startup")
def startup_event():
    init_db()

class ScrapeRequest(BaseModel):
    keyword: str
    pages: int = 3

def run_scraper_task(keyword: str, pages: int):
    logger.info(f"Starting background scrape task for '{keyword}' with {pages} pages.")
    total_jobs = 0
    try:
        scraper = BossScraper()
        # Returns a generator now, need to iterate
        for jobs_chunk in scraper.scrape_keyword(keyword, pages):
            if jobs_chunk:
                insert_jobs(jobs_chunk)
                total_jobs += len(jobs_chunk)
                logger.info(f"Saved chunk of {len(jobs_chunk)} jobs. Total so far: {total_jobs}")
            else:
                logger.debug("Empty chunk yielded.")
        
        logger.info(f"Task completed. Total saved: {total_jobs}")
    except Exception as e:
        logger.error(f"Background task failed: {e}")

@app.post("/scrape")
async def trigger_scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Trigger a scrape task.
    """
    background_tasks.add_task(run_scraper_task, request.keyword, request.pages)
    return {"message": f"Scraper started for keyword: {request.keyword}", "status": "processing"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
