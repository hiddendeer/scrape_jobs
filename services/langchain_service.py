"""
LangChain service for AI-powered job analysis and career planning.
Generates competitive reports with learning plans and required skills using streaming.
"""
import os
import logging
import json
from typing import List, Dict, AsyncGenerator, Any
from datetime import datetime

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from langchain.tools import tool
from langchain.agents import create_agent
from services.data_service import get_data_service

logger = logging.getLogger(__name__)

# Prompt template for job analysis
CAREER_ANALYSIS_PROMPT = """你是一位专业的职业规划顾问和技术招聘专家，专注于人工智能、机器学习和软件工程领域。
你的任务是分析多个职位招聘信息，并生成一份全面的职业发展报告。

# 待分析的职位信息:

{job_data}

# 你的任务:

基于上述职位信息，提供一份全面的分析。请将你的回复格式化为以下 JSON 结构:

{{
  "summary": "2-3段市场总结，用中文描述当前职位市场趋势",
  "key_skills": ["技能1", "技能2", ...],
  "soft_skills": ["软技能1", "软技能2", ...],
  "learning_plan": [
    {{
      "phase": "阶段名称（中文）",
      "duration": "时间周期",
      "objectives": ["学习目标1", "学习目标2"],
      "skills": ["技能1", "技能2"],
      "projects": ["项目1", "项目2"],
      "resources": [{{"name": "资源名称", "type": "类型", "description": "描述"}}]
    }}
  ],
  "resources": [
    {{"category": "分类", "items": ["资源1", "资源2"]}}
  ],
  "salary_insights": "详细的薪资分析（用中文描述）",
  "career_path": "职业发展路径描述（用中文）"
}}

# 重要要求:

1. **所有内容必须使用中文输出**，除了技术术语（如 Python、TensorFlow 等保留英文）
2. 只提供 JSON 对象，不要使用 markdown 标记，不要代码块标记，不要额外文本
3. 技能名称可以是英文（专业术语），但描述要用中文
4. 资源名称如果是书籍、课程等，保留原名
5. 确保内容具体、可操作，不要空洞的描述

现在开始你的分析："""


class JobAnalysisService:
    """Service for analyzing job postings using LangChain with streaming support"""

    def __init__(self):
        """Initialize the LangChain service with LLM configuration."""
        self._init_config()
        self._init_llm()
        logger.info(f"JobAnalysisService initialized with model: {self.model_name}")

    def _init_config(self):
        """Load configuration from environment variables."""
        self.api_key = os.getenv("LLM_API_KEY")
        self.api_base = os.getenv("LLM_API_BASE", "https://api.openai.com/v1")
        self.model_name = os.getenv("LLM_MODEL_NAME", "gpt-4o-mini")
        self.temperature = float(os.getenv("LLM_TEMPERATURE", "0.7"))

        if not self.api_key:
            logger.error("LLM_API_KEY not found in environment variables")
            raise ValueError("LLM_API_KEY is required but not set")

    def _init_llm(self):
        """Initialize LLM and base components."""
        self.llm = ChatOpenAI(
            model=self.model_name,
            api_key=self.api_key,
            base_url=self.api_base,
            temperature=self.temperature,
            max_tokens=4000,
            streaming=True
        )
        self.str_parser = StrOutputParser()
        self.data_service = get_data_service()

    def _format_job_data(self, jobs: List[Dict]) -> str:
        """Format job data for the LLM prompt."""
        formatted_jobs = []
        for i, job in enumerate(jobs, 1):
            job_text = f"""
## Job {i}:
- Position: {job.get('job_name', 'N/A')}
- Company: {job.get('company_name', 'N/A')}
- Location: {job.get('city', 'N/A')} ({job.get('district', 'N/A')})
- Salary: {job.get('salary_raw', 'N/A')}
- Experience: {job.get('experience_raw', 'N/A')}
- Education: {job.get('education', 'N/A')}
- Skills: {job.get('skills_tags', 'N/A')}
- Description: {job.get('job_desc', 'N/A')[:500]}...
"""
            formatted_jobs.append(job_text)
        return "\n".join(formatted_jobs)

    def _get_analysis_chain(self):
        """Create the LangChain analysis chain."""
        prompt = ChatPromptTemplate.from_template(CAREER_ANALYSIS_PROMPT)
        return (
            {"job_data": RunnablePassthrough()}
            | prompt
            | self.llm
            | self.str_parser
        )

    def _clean_json_response(self, text: str) -> str:
        """Remove markdown code blocks from LLM response."""
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        elif text.startswith("```"):
            text = text[3:]
        
        if text.endswith("```"):
            text = text[:-3]
        return text.strip()

    def _parse_llm_response(self, text: str, jobs_count: int) -> Dict[str, Any]:
        """Parse the raw LLM response into a structured dictionary."""
        try:
            cleaned = self._clean_json_response(text)
            result = json.loads(cleaned)
            
            # Add metadata
            result["metadata"] = {
                "jobs_analyzed": jobs_count,
                "analysis_date": datetime.now().isoformat(),
                "model_used": self.model_name,
            }
            return result
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse LLM response: {e}")
            return {
                "raw_response": text,
                "metadata": {
                    "jobs_analyzed": jobs_count,
                    "analysis_date": datetime.now().isoformat(),
                    "note": "无法解析为结构化 JSON，返回原始响应"
                }
            }

    async def analyze_jobs_streaming(self, jobs: List[Dict], user_prompt: str = None) -> AsyncGenerator[str, None]:
        """Stream job analysis results in real-time using SSE events."""
        if not jobs:
            yield json.dumps({"type": "error", "message": "没有职位信息可供分析"}, ensure_ascii=False)
            return

        try:
            # Define tools
            # Define tools with rich descriptions to help LLM decide when to call them
            @tool
            def get_skill_statistics() -> str:
                """
                对当前检索到的所有职位（全量数据）执行深度的技术栈统计分析。
                当你需要提供真实的市场技术趋势、核心技能频率占比、或需要量化数据来支持你的职业路径建议时，请调用此工具。
                注意：此工具处理的是后台全量数据集，比你上下文中的部分摘要信息更全面。
                """
                counts = self.data_service.extract_skills(jobs)
                sorted_counts = sorted(counts.items(), key=lambda x: x[1], reverse=True)[:20]
                top_skills = [{"skill": s, "count": c} for s, c in sorted_counts]
                return json.dumps(top_skills, ensure_ascii=False)

            tools = [get_skill_statistics]
            
            # Professional, goal-oriented system prompt
            system_prompt = """你是一位顶尖的职业规划专家和资深技术招聘经理。
            
            # 你的核心能力:
            1. **事实检索**: 你能通过下方的职位快照快速建立对垂直领域的初步认知。
            2. **专家级统计分析**: 你配备了 `get_skill_statistics` 工具。它能深度扫描后台成百上千条原始招聘数据。
            **调用策略**:
            - **必须调用**: 当用户需要“精确统计”、“热度排名”、“技能占比”或询问“全量市场趋势”时。
            - **无需调用**: 如果用户的问题仅仅是基于当前可见的职位摘要（Job Snapshot）进行总结、规划或简单建议，或者你认为当前信息已足够给出专业回答，则应直接回答，避免过度使用工具。
            
            # 业务上下文 (职位片段):
            {job_summary}
            
            # 输出规范:
            1. **最终报告模块**: 如果你生成的是一份全面的发展报告，请在回复的最末尾附带一个遵循以下结构的 JSON 代码块（放在 ```json 标签内）。这将用于驱动前端的可视化图表。
            2. **语气**: 保持专业、犀利且富有启发性。
            3. **语言**: 必须使用中文回答。
            
            # 期待的 JSON 结构 (仅在生成最终报告时包含):
            {{
              "summary": "基于全量数据分析的市场综述",
              "key_skills": ["具体技能1", "具体技能2"],
              "soft_skills": ["能力1", "能力2"],
              "learning_plan": [
                {{
                  "phase": "阶段名称",
                  "duration": "预估周期",
                  "objectives": ["核心目标"],
                  "skills": ["学习重点"],
                  "projects": ["实战项目建议"],
                  "resources": [{{"name": "资源名称", "type": "类型", "description": "简述"}}]
                }}
              ],
              "salary_insights": "具有洞察力的薪资趋势分析",
              "career_path": "建议的进阶演进路径"
            }}
            """

            job_summary = self._format_job_data(jobs[:5])
            
            agent_executor = create_agent(
                model=self.llm,
                tools=tools,
                system_prompt=system_prompt.format(job_summary=job_summary)
            )

            input_text = user_prompt if user_prompt else "请根据提供的职位信息，为我生成一份全面的职业发展分析报告。"
            
            yield json.dumps({"type": "status", "message": "正在初始化分析流程...", "progress": 5}, ensure_ascii=False)

            # Execution with manual step handling to yield intermediate results
            full_response = ""
            async for event in agent_executor.astream_events(
                {"messages": [("user", input_text)]},
                version="v1"
            ):
                kind = event["event"]
                
                if kind == "on_chat_model_stream":
                    chunk = event["data"].get("chunk")
                    if chunk and hasattr(chunk, "content"):
                        # Check for thinking/reasoning content (specific models like DeepSeek)
                        reasoning = ""
                        if hasattr(chunk, "additional_kwargs"):
                            reasoning = chunk.additional_kwargs.get("reasoning_content", "")
                        
                        content = chunk.content
                        
                        if reasoning:
                            yield json.dumps({"type": "chunk", "content": reasoning, "is_thought": True}, ensure_ascii=False)
                        
                        if content:
                            full_response += content
                            # If content itself looks like it's inside <think> tags, we could flag it, 
                            # but the frontend handles that too. We can pass a flag if we detect it.
                            is_thought = "<think>" in full_response and "</think>" not in full_response
                            yield json.dumps({"type": "chunk", "content": content, "is_thought": is_thought}, ensure_ascii=False)
                
                elif kind == "on_tool_start":
                    yield json.dumps({
                        "type": "tool_start",
                        "tool": event["name"],
                        "input": event["data"].get("input"),
                        "message": f"正在调用工具: {event['name']}..."
                    }, ensure_ascii=False)
                
                elif kind == "on_tool_end":
                    output = event["data"].get("output")
                    if hasattr(output, "content"):
                        output = output.content
                    
                    yield json.dumps({
                        "type": "tool_end",
                        "tool": event["name"],
                        "output": output,
                        "message": f"工具 {event['name']} 执行完毕"
                    }, ensure_ascii=False)
            
            # Try to parse the final response as JSON for the structured report card
            report_data = None
            try:
                # Remove any thinking tags for parsing
                clean_text = full_response
                if "<think>" in clean_text and "</think>" in clean_text:
                    clean_text = clean_text.split("</think>")[-1]
                
                cleaned_json = self._clean_json_response(clean_text)
                if cleaned_json and (cleaned_json.startswith("{") or cleaned_json.startswith("[")):
                    report_data = self._parse_llm_response(cleaned_json, len(jobs))
            except Exception:
                pass

            yield json.dumps({
                "type": "complete", 
                "message": "分析完成", 
                "progress": 100,
                "data": report_data
            }, ensure_ascii=False)
            logger.info(f"Successfully completed agentic analysis of {len(jobs)} jobs")

        except Exception as e:
            logger.error(f"Error during streaming analysis: {e}", exc_info=True)
            yield json.dumps({"type": "error", "message": str(e), "progress": 0}, ensure_ascii=False)


# Singleton instance
_job_analysis_service = None

def get_job_analysis_service() -> JobAnalysisService:
    """Get or create the singleton JobAnalysisService instance."""
    global _job_analysis_service
    if _job_analysis_service is None:
        _job_analysis_service = JobAnalysisService()
    return _job_analysis_service
