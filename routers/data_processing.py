"""
Data processing router - handles all data analysis and filtering endpoints
"""
from fastapi import APIRouter, Query, HTTPException
import logging
import re
import json
import base64
from io import BytesIO
from collections import Counter
import pandas as pd
import numpy as np
from wordcloud import WordCloud
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from database import get_jobs_info, handle_job_info, get_agent_jobs_info, handle_agent_job_info

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/data",
    tags=["data-processing"]
)


def generate_wordcloud(skill_counts: dict, width: int = 800, height: int = 400) -> str:
    """
    Generate word cloud image from skill frequency data.

    Args:
        skill_counts: Dictionary of skills and their counts
        width: Image width in pixels
        height: Image height in pixels

    Returns:
        Base64 encoded PNG image
    """
    if not skill_counts:
        return None

    try:
        # Try to use a font that supports Chinese characters
        # Common Chinese fonts: SimHei, Microsoft YaHei, PingFang SC
        font_path = None
        possible_fonts = [
            'C:/Windows/Fonts/msyh.ttc',  # Microsoft YaHei (Windows)
            'C:/Windows/Fonts/simhei.ttf',  # SimHei (Windows)
            '/System/Library/Fonts/PingFang.ttc',  # PingFang (macOS)
            '/usr/share/fonts/truetype/droid/DroidSansFallbackFull.ttf',  # Linux
        ]

        import os
        for font in possible_fonts:
            if os.path.exists(font):
                font_path = font
                logger.info(f"Using font: {font_path}")
                break

        # Create word cloud with font if available
        if font_path:
            wordcloud = WordCloud(
                width=width,
                height=height,
                background_color='white',
                colormap='viridis',
                max_words=100,
                relative_scaling=0.5,
                min_font_size=10,
                font_path=font_path
            ).generate_from_frequencies(skill_counts)
        else:
            # Fallback without font (may not display Chinese correctly)
            wordcloud = WordCloud(
                width=width,
                height=height,
                background_color='white',
                colormap='viridis',
                max_words=100,
                relative_scaling=0.5,
                min_font_size=10,
                prefer_horizontal=0.9
            ).generate_from_frequencies(skill_counts)
            logger.warning("No Chinese font found, Chinese characters may not display correctly")

        # Create figure
        fig, ax = plt.subplots(figsize=(10, 5))
        ax.imshow(wordcloud, interpolation='bilinear')
        ax.axis('off')
        ax.set_title('AI Agent Skills Word Cloud', fontsize=16, pad=20, fontfamily='sans-serif')

        # Save to BytesIO
        buf = BytesIO()
        plt.savefig(buf, format='png', bbox_inches='tight', dpi=100)
        buf.seek(0)
        plt.close(fig)

        # Encode to base64
        img_base64 = base64.b64encode(buf.read()).decode('utf-8')
        return img_base64

    except Exception as e:
        logger.error(f"Error generating word cloud: {e}")
        return None


@router.get("/health")
async def health_check(table: str = Query(None, description="Table name to query")):
    """
    Check job data health and filter out unwanted entries.
    Filters out jobs containing EMS, 能源, or 储能 in job_name or job_desc.
    """
    result = get_jobs_info(table=table)
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


@router.get("/analyze-agent-skills")
async def analyze_agent_skills(
    table: str = Query(None, description="Table name to query"),
    generate_wordcloud_img: bool = Query(True, description="Generate word cloud image")
):
    """
    Analyze and extract top skills from agent-related job postings.
    Extracts skills from skills_tags JSON and job descriptions.
    Returns the top 20 most common skills with optional word cloud image.
    """
    result = get_agent_jobs_info(table=table)
    if not result:
        return {
            "message": "No data found",
            "total_jobs_analyzed": 0,
            "top_skills": [],
            "wordcloud": None
        }

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

    # 3. 统计频率并取前20
    skill_counts = Counter(all_skills)

    # 过滤掉一些极其常见的无意义词汇 (Stop words)
    stop_words = {'and', 'the', 'with', 'to', 'of', 'in', 'for', 'boss', 'kanzhun', 'api', 'agent', 'ai'}
    # ai, agent 作为职位背景通常出现次数最高，可考虑过滤
    clean_counts = {k: v for k, v in skill_counts.items() if k not in stop_words}

    top_skills = Counter(clean_counts).most_common(20)

    # Generate word cloud if requested
    wordcloud_base64 = None
    if generate_wordcloud_img and clean_counts:
        wordcloud_base64 = generate_wordcloud(clean_counts)

    return {
        "message": "AI Agent skills analyzed successfully",
        "total_jobs_analyzed": len(result),
        "top_skills": [{"skill": s, "count": c} for s, c in top_skills],
        "wordcloud": wordcloud_base64  # Base64 encoded PNG image
    }
