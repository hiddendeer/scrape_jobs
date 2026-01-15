from fastapi import FastAPI, BackgroundTasks, HTTPException
import logging
import re
import json
from collections import Counter
from pydantic import BaseModel
from scraper import BossScraper
from database import init_db, insert_jobs, get_jobs_info, handle_job_info, get_agent_jobs_info, handle_agent_job_info
import pandas as pd

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
    city: str = "101210700"  # Default to Wuxi

def run_scraper_task(keyword: str, pages: int, city: str):
    logger.info(f"Starting background scrape task for '{keyword}' with {pages} pages in city {city}.")
    total_jobs = 0
    try:
        scraper = BossScraper()
        # Returns a generator now, need to iterate
        for jobs_chunk in scraper.scrape_keyword(keyword, pages, city):
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
    background_tasks.add_task(run_scraper_task, request.keyword, request.pages, request.city)
    return {"message": f"Scraper started for keyword: {request.keyword} in city: {request.city}", "status": "processing"}

@app.get("/health")
async def health_check():
    result = get_jobs_info()
    df = pd.DataFrame(result)
    
    if df.empty:
        return {
            "status": "ok", 
            "data": [], 
            "count": 0,
            "deleted_count": 0
        }
    
    # 筛选出 job_name 和 job_desc 都不包含 EMS、能源 或 储能 的数据 (我们要删除的)
    exclude_regex = 'EMS|能源|储能'
    condition_name = ~df['job_name'].str.contains(exclude_regex, na=False, case=False)
    condition_desc = ~df['job_desc'].str.contains(exclude_regex, na=False, case=False)
    df_filtered = df[condition_name & condition_desc]
    in_ids = df_filtered['job_id'].tolist()
    
    # 从数据库中删除这些不需要的任务
    if in_ids:
        handle_job_info(in_ids)
    
    return {
        "status": "ok", 
        "data": df_filtered.to_dict(orient='records'), 
        "count": len(df_filtered),
        "deleted_count": len(in_ids)
    }


@app.get("/check_agent")
async def check_agent_info():
    result = get_agent_jobs_info()
    df = pd.DataFrame(result)
    
    if df.empty:
        return {"message": "No agent jobs found", "count": 0, "deleted_count": 0}
    
    # 筛选出 job_name 不包含 agent 或 ai (不区分大小写) 
    # 或 job_desc 不包含 agent (不区分大小写) 的数据
    condition_name = ~df['job_name'].str.contains('agent|ai', na=False, case=False)
    condition_desc = ~df['job_desc'].str.contains('agent', na=False, case=False)
    
    # 根据用户要求：job_name不包含 agent/ai AND job_desc不包含 agent
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

@app.get("/handle_agent_info")
async def handle_agent_info():
    result = get_agent_jobs_info()
    if not result:
        return {"message": "No data found", "top_skills": []}

    all_skills = []
    
    for job in result:
        # 1. 从 skills_tags 提取 (JSON 格式)
        tags_raw = job.get('skills_tags')
        if tags_raw:
            try:
                tags = json.loads(tags_raw)
                if isinstance(tags, list):
                    all_skills.extend([tag.lower() for tag in tags])
            except:
                pass
        
        # 2. 从 job_desc 提取英文关键词/常见技能 (正则)
        desc = job.get('job_desc', '')
        if desc:
            # 匹配连续的英文字符或C++/C#等常见技术词汇
            eng_words = re.findall(r'[a-zA-Z0-9+#]+', desc)
            # 过滤掉太短的或者纯数字
            filtered_eng = [w.lower() for w in eng_words if len(w) > 1 and not w.isdigit()]
            all_skills.extend(filtered_eng)
            
            # 匹配常见的中文技能关键词 (可选，根据具体情况添加)
            # 比如：大模型, 深度学习, 机器学习 等
            cn_keywords = ["大模型", "深度学习", "机器学习", "自然语言处理", "图像识别", "算法"]
            for kw in cn_keywords:
                if kw in desc:
                    all_skills.append(kw)

    # 3. 统计频率并取前5
    skill_counts = Counter(all_skills)
    
    # 过滤掉一些极其常见的无意义词汇 (Stop words)
    stop_words = {'and', 'the', 'with', 'to', 'of', 'in', 'for', 'boss', 'kanzhun','api','agent','ai'} # ai, agent 作为职位背景通常出现次数最高，可考虑过滤
    clean_counts = {k: v for k, v in skill_counts.items() if k not in stop_words}
    
    top_5 = Counter(clean_counts).most_common(20)
    
    return {
        "message": "AI Agent skills analyzed successfully",
        "total_jobs_analyzed": len(result),
        "top_skills": [{"skill": s, "count": c} for s, c in top_5]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
