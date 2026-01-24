"""
Services package for Boss Zhipin Scraper API
"""
from .langchain_service import JobAnalysisService, get_job_analysis_service

__all__ = ["JobAnalysisService", "get_job_analysis_service"]
