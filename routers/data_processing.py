"""
Data processing router - handles all data analysis and filtering endpoints
"""
from fastapi import APIRouter, Query, HTTPException
from fastapi.responses import HTMLResponse, StreamingResponse
import logging
import json
import os
import pandas as pd
from database import get_jobs_info, handle_job_info, get_agent_jobs_info, handle_agent_job_info
from services.langchain_service import get_job_analysis_service
from services.data_service import get_data_service

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/data",
    tags=["data-processing"]
)

# Initialize services
data_service = get_data_service()
analysis_service = get_job_analysis_service()


@router.get("/health")
async def health_check(table: str = Query(None, description="Table name to query")):
    """
    Check job data health and filter out unwanted entries.
    Filters out jobs containing EMS, 能源, or 储能 in job_name or job_desc.
    """
    result = get_jobs_info(table=table)
    df = pd.DataFrame(result)

    if df.empty:
        return {"status": "ok", "data": [], "count": 0, "deleted_count": 0}

    # Filter out unwanted jobs
    exclude_regex = 'EMS|能源|储能'
    condition_name = ~df['job_name'].str.contains(exclude_regex, na=False, case=False)
    condition_desc = ~df['job_desc'].str.contains(exclude_regex, na=False, case=False)
    
    df_filtered = df[condition_name & condition_desc]
    in_ids = df_filtered['job_id'].tolist()

    if in_ids:
        handle_job_info(in_ids)

    return {
        "status": "ok",
        "data": df_filtered.to_dict(orient='records'),
        "count": len(df_filtered),
        "deleted_count": len(in_ids)
    }


@router.get("/check-agent")
async def check_agent_info(table: str = Query(None, description="Table name to query")):
    """
    Check and filter agent-related jobs.
    Filters out jobs where job_name doesn't contain agent/ai AND job_desc doesn't contain agent.
    """
    result = get_agent_jobs_info(table=table)
    df = pd.DataFrame(result)

    if df.empty:
        return {"message": "No agent jobs found", "count": 0, "deleted_count": 0}

    # Filter rules: job_name contains agent/ai OR job_desc contains agent
    condition_name = ~df['job_name'].str.contains('agent|ai', na=False, case=False)
    condition_desc = ~df['job_desc'].str.contains('agent', na=False, case=False)

    df_to_delete = df[condition_name & condition_desc]
    in_ids = df_to_delete['job_id'].tolist()

    if in_ids:
        handle_agent_job_info(in_ids)

    return {
        "message": "AI Agent info checked and filtered successfully",
        "total_checked": len(df),
        "deleted_count": len(in_ids),
        "deleted_ids": in_ids
    }


@router.get("/analyze-agent-skills")
async def analyze_agent_skills(
    table: str = Query(None, description="Table name to query"),
    generate_wordcloud_img: bool = Query(True, description="Generate word cloud image")
):
    """
    Analyze and extract top skills from agent-related job postings.
    """
    result = get_agent_jobs_info(table=table)
    if not result:
        return {
            "message": "No data found",
            "total_jobs_analyzed": 0,
            "top_skills": [],
            "wordcloud": None
        }

    # Use DataService to extract skills
    clean_counts = data_service.extract_skills(result)
    top_skills = pd.Series(clean_counts).sort_values(ascending=False).head(20).to_dict()

    # Generate word cloud if requested
    wordcloud_base64 = None
    if generate_wordcloud_img and clean_counts:
        wordcloud_base64 = data_service.generate_wordcloud(clean_counts)

    return {
        "message": "AI Agent skills analyzed successfully",
        "total_jobs_analyzed": len(result),
        "top_skills": [{"skill": s, "count": int(c)} for s, c in top_skills.items()],
        "wordcloud": wordcloud_base64
    }


# ============================================================================
# Streaming Career Analysis Endpoints (LangChain-powered)
# ============================================================================

@router.get("/analyze-career-stream", response_class=HTMLResponse)
async def analyze_career_stream_page(
    table: str = Query(None, description="Table name to query"),
    limit: int = Query(20, description="Maximum number of jobs to analyze", ge=1, le=50)
):
    """Serve the streaming career analysis HTML page."""
    jobs = get_agent_jobs_info(table=table)

    if not jobs:
        return HTMLResponse(
            content="<html><body><h1>No Jobs Found</h1><p>Please scrape some jobs first.</p></body></html>",
            status_code=404
        )

    jobs_to_analyze = jobs[:limit]
    template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "templates", "career_stream.html")

    try:
        with open(template_path, "r", encoding="utf-8") as f:
            template_content = f.read()
            total_str = str(len(jobs_to_analyze))
            html_content = template_content.replace("{{ total_jobs }}", total_str).replace("{{total_jobs}}", total_str)
        return HTMLResponse(content=html_content)
    except Exception as e:
        logger.error(f"Error loading template: {e}")
        return HTMLResponse(content=f"<html><body><h1>Error</h1><p>{str(e)}</p></body></html>", status_code=500)


@router.get("/api/analyze-career-stream")
async def analyze_career_stream_api(
    table: str = Query(None, description="Table name to query"),
    limit: int = Query(20, description="Maximum number of jobs to analyze", ge=1, le=50),
    prompt: str = Query(None, description="Custom analysis prompt for the AI agent")
):
    """SSE endpoint for streaming career analysis."""
    async def event_stream():
        try:
            jobs = get_agent_jobs_info(table=table)
            if not jobs:
                yield f"data: {json.dumps({'type': 'error', 'message': 'No jobs found'}, ensure_ascii=False)}\n\n"
                return

            jobs_to_analyze = jobs[:limit]
            logger.info(f"Streaming analysis of {len(jobs_to_analyze)} jobs with prompt: {prompt}")

            async for chunk in analysis_service.analyze_jobs_streaming(jobs_to_analyze, user_prompt=prompt):
                yield f"data: {chunk}\n\n"

        except Exception as e:
            logger.error(f"Error in streaming API: {e}")
            yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
