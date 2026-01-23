from fastapi import FastAPI
from fastapi.responses import FileResponse
import logging
import os
from database import init_db
from routers import scraper_router, data_processing_router

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Get the base directory
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

# Initialize FastAPI app
app = FastAPI(
    title="Boss Zhipin Scraper API",
    description="API for scraping and processing job listings from Boss Zhipin",
    version="1.0.0"
)

# Initialize DB on startup
@app.on_event("startup")
def startup_event():
    init_db()
    logger.info("Database initialized successfully")

# Include routers
app.include_router(scraper_router)
app.include_router(data_processing_router)

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Boss Zhipin Scraper API",
        "version": "1.0.0",
        "endpoints": {
            "dashboard": "/dashboard",
            "scraper": "/scrape",
            "data_processing": ["/data/health", "/data/check-agent", "/data/analyze-agent-skills"]
        }
    }

# Dashboard endpoint
@app.get("/dashboard")
async def dashboard():
    """Serve the skills dashboard HTML page"""
    dashboard_path = os.path.join(BASE_DIR, "templates", "skills_dashboard.html")
    if os.path.exists(dashboard_path):
        return FileResponse(dashboard_path, media_type="text/html")
    return {"error": "Dashboard not found"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
