"""
Routers package for Boss Zhipin Scraper API
"""
from .scraper import router as scraper_router
from .data_processing import router as data_processing_router

__all__ = ["scraper_router", "data_processing_router"]
